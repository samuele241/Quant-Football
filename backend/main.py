import os
import urllib.parse
import unicodedata  # For name normalization
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import quant_engine #C++ Module
from scouting_service import ScoutingService

# Setup App
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Football Quant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Permetti a Next.js di chiamare
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------------------------

load_dotenv("../data-processing/.env") # Puntiamo al .env nella cartella vicina

db_pass = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
db_url = f"postgresql://{os.getenv('DB_USER')}:{db_pass}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)
scouting_service = ScoutingService(engine)

@app.get("/")
def read_root():
    return {"status": "System Operational", "engine": "Hybrid Python/C++"}

@app.get("/analytics/teams")
def get_teams(season: str = "2025"):
    query = text("""
        SELECT DISTINCT t.id
        FROM teams t
        JOIN v_full_match_stats pms ON t.id = pms.team_id
        WHERE pms.season = :season
        ORDER BY t.id ASC
    """)
    teams = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"season": season})
        for row in rows:
            display_name = row[0].replace("_", " ")
            teams.append({"id": row[0], "name": display_name})
    return teams

@app.get("/analytics/top-scorers")
def get_top_scorers(season: str = "2025", team_id: str | None = None):
    sql = """
        SELECT player_name,
               array_agg(npxg) as xg_history,
               array_agg(goals) as goal_history,
               SUM(goals) as total_goals
        FROM v_full_match_stats
        WHERE season = :season
    """

    params = {"season": season}
    if team_id and team_id != "all":
        sql += " AND team_id = :team_id"
        params["team_id"] = team_id
        limit_clause = ""
    else:
        limit_clause = "LIMIT 10"

    sql += f"""
        GROUP BY player_name
        HAVING SUM(minutes) > 90
        ORDER BY total_goals DESC
        {limit_clause}
    """

    results = []
    with engine.connect() as conn:
        try:
            rows = conn.execute(text(sql), params)
        except Exception:
            fallback_sql = sql.replace("npxg", "xa")
            rows = conn.execute(text(fallback_sql), params)
        for row in rows:
            xg_vector = [float(x) for x in row[1]]
            goal_vector = [int(g) for g in row[2]]
            efficiency_score = quant_engine.calculate_efficiency(xg_vector, goal_vector)
            results.append({
                "player": row[0],
                "goals": row[3],
                "quant_efficiency_score": round(efficiency_score, 4),
            })

    results.sort(key=lambda x: x["quant_efficiency_score"], reverse=True)
    return results

@app.get("/analytics/player/{player_name}")
def get_player_history(player_name: str, season: str = "2025"):
    """Player history and advanced metrics for the requested season."""
    decoded_name = urllib.parse.unquote(player_name)

    query = text("""
        SELECT match_date,
               goals,
               npxg as xg,
               team_id,
               opponent,
               season,
               minutes,
               shots,
               fair_value
        FROM v_full_match_stats
        WHERE player_name = :name AND trim(season) = :season
        ORDER BY match_date ASC
    """)

    history = []
    goals_vector = []
    fair_values = []
    total_goals = 0
    total_xg = 0.0
    total_minutes = 0
    total_shots = 0
    birth_date = None

    def load_rows(sql_query):
        with engine.connect() as conn:
            return conn.execute(sql_query, {"name": decoded_name, "season": season})

    try:
        rows = load_rows(query)
        for row in rows:
            g = int(row[1] or 0)
            xg = float(row[2] or 0)
            mins = int(row[6] or 0)
            shots = int(row[7] or 0)
            row_season = row[5]
            fv = float(row[8]) if row[8] else 0.0

            total_goals += g
            total_xg += xg
            total_minutes += mins
            total_shots += shots
            if fv > 0:
                fair_values.append(fv)

            history.append({
                "date": str(row[0]),
                "goals": g,
                "xg": xg,
                "team": row[3],
                "opponent": row[4],
                "season": row_season,
            })
            goals_vector.append(float(g))
    except Exception:
        fallback_query = text("""
            SELECT match_date,
                   goals,
                   npxg as xg,
                   team_id,
                   NULL as opponent,
                   season,
                   minutes,
                   shots,
                   fair_value
            FROM v_full_match_stats
            WHERE player_name = :name AND trim(season) = :season
            ORDER BY match_date ASC
        """)
        try:
            rows = load_rows(fallback_query)
        except Exception:
            xa_fallback = text(str(fallback_query).replace("npxg", "xa"))
            rows = load_rows(xa_fallback)

        for row in rows:
            g = int(row[1] or 0)
            xg = float(row[2] or 0)
            mins = int(row[6] or 0)
            shots = int(row[7] or 0)
            row_season = row[5]
            fv = float(row[8]) if row[8] else 0.0

            total_goals += g
            total_xg += xg
            total_minutes += mins
            total_shots += shots
            if fv > 0:
                fair_values.append(fv)

            history.append({
                "date": str(row[0]),
                "goals": g,
                "xg": xg,
                "team": row[3],
                "opponent": None,
                "season": row_season,
            })
            goals_vector.append(float(g))

    if not history:
        raise HTTPException(status_code=404, detail="Player not found for this season")

    conversion_rate = (total_goals / total_shots) * 100 if total_shots > 0 else 0.0
    goals_p90 = (total_goals / total_minutes) * 90 if total_minutes > 0 else 0.0
    xg_diff = total_goals - total_xg
    avg_fair_value = sum(fair_values) / len(fair_values) if fair_values else 0.0

    recent_goals = goals_vector[-5:] if len(goals_vector) >= 5 else goals_vector
    trend_score = quant_engine.calculate_trend(recent_goals)

    if birth_date is None:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT birth_date FROM players WHERE name = :name"),
                {"name": decoded_name},
            ).fetchone()
            if row and row[0]:
                birth_date = str(row[0])

    return {
        "player": decoded_name,
        "birth_date": birth_date,
        "trend_slope": round(trend_score, 4),
        "advanced_metrics": {
            "conversion_rate": round(conversion_rate, 1),
            "goals_per_90": round(goals_p90, 2),
            "total_shots": total_shots,
            "xg_diff": round(xg_diff, 2),
            "fair_value": round(avg_fair_value, 0),
        },
        "history": history,
    }

@app.get("/analytics/prediction/{player_name}")
def get_prediction(player_name: str, season: str = "2025"):
    """Monte Carlo prediction basata sulla stagione specificata (default '2025')."""
    decoded_name = urllib.parse.unquote(player_name)

    player_id = None
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT player_id FROM players WHERE name = :name"),
            {"name": decoded_name},
        ).fetchone()
        if row:
            player_id = row[0]

    if player_id is None:
        raise HTTPException(status_code=404, detail="Player not found")

    query = text("""
        SELECT goals
        FROM v_full_match_stats
        WHERE player_id = :player_id AND season = :season
    """)

    goals_list = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"player_id": player_id, "season": season})
        for r in rows:
            goals_list.append(int(r[0] or 0))

    matches_played = len(goals_list)
    total_matches = 38
    matches_remaining = max(0, total_matches - matches_played)
    current_goals = sum(goals_list)

    if matches_remaining == 0 or matches_played == 0:
        return {
            "player": decoded_name,
            "season": season,
            "matches_played": matches_played,
            "matches_remaining": matches_remaining,
            "current_goals": current_goals,
            "predicted_mean_total_goals": current_goals,
            "percentiles": {"p10": current_goals, "p50": current_goals, "p90": current_goals},
            "simulation": [{"total_goals": current_goals, "probability": 1.0}],
        }

    import random
    trials = 10000
    totals = []
    for _ in range(trials):
        sim = current_goals
        for _m in range(matches_remaining):
            sim += random.choice(goals_list)
        totals.append(sim)

    totals.sort()
    mean_pred = sum(totals) / len(totals)
    p10 = totals[int(0.10 * len(totals))]
    p50 = totals[int(0.50 * len(totals))]
    p90 = totals[int(0.90 * len(totals))]

    from collections import Counter
    counter = Counter(totals)
    simulation = [
        {"total_goals": total, "probability": round(count / len(totals), 4)}
        for total, count in sorted(counter.items())
    ]

    return {
        "player": decoded_name,
        "season": season,
        "matches_played": matches_played,
        "matches_remaining": matches_remaining,
        "current_goals": current_goals,
        "predicted_mean_total_goals": round(mean_pred, 2),
        "percentiles": {"p10": p10, "p50": p50, "p90": p90},
        "simulation": simulation,
    }

@app.get("/analytics/scouting/similar/{player_name}")
def get_similar_players(
    player_name: str,
    season: str = "2025",
    min_minutes: int = 90,
    top_n: int = 5,
):
    """Find similar players using the scouting service (weighted euclidean)."""
    decoded_name = urllib.parse.unquote(player_name)
    try:
        return scouting_service.find_similar(
            decoded_name,
            season=season,
            min_minutes=min_minutes,
            top_n=top_n,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

# ... (altri import) ...

@app.get("/analytics/scouting/suggest")
def suggest_players(q: str):
    """Return up to 10 player name suggestions matching the query (case-insensitive)."""
    if not q or len(q.strip()) < 1:
        return []

    query = text("""
        SELECT DISTINCT player_name
        FROM v_full_match_stats
        WHERE player_name ILIKE :pattern
        ORDER BY player_name ASC
        LIMIT 10
    """)

    pattern = f"%{q.strip()}%"
    suggestions = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"pattern": pattern})
        for r in rows:
            suggestions.append(r[0])

    return suggestions
"""
Analisi Contestuali - Context Analytics Endpoints

Questi endpoint integrano i dati team_performance (ELO, Forma) 
con le statistiche giocatori per fornire metriche avanzate.
"""

# Aggiungi dopo gli import esistenti in main.py:

@app.get("/analytics/player/{player_name}/context")
def get_player_context_analysis(player_name: str, season: str = "2025"):
    """
    Analisi contestuale avanzata per un giocatore:
    - Difficoltà calendario (media ELO avversari)
    - Performance vs Top/Bottom teams
    - Fair Value Adjustment basato su opposizione
    - Goal Quality Score (gol contro squadre forti valgono di più)
    """
    decoded_name = urllib.parse.unquote(player_name)
    
    # Map season format: v_full_match_stats usa "2025", team_performance usa "2526"
    team_season_map = {"2024": "2425", "2025": "2526"}
    team_season = team_season_map.get(season, season)
    
    query = text("""
        WITH player_matches AS (
            SELECT 
                pms.match_date,
                pms.opponent,
                pms.goals,
                pms.xg,
                pms.team_id,
                tp.elo as opponent_elo,
                tp.rolling_xg_form as opponent_attack_form,
                tp.rolling_ga_form as opponent_defense_form
            FROM v_full_match_stats pms
            LEFT JOIN team_performance tp 
                ON pms.opponent = tp.team_id 
                AND pms.match_date = tp.match_date
                AND tp.season = :team_season
            WHERE pms.player_name = :name 
                AND pms.season = :season
                AND pms.minutes > 0
        )
        SELECT 
            match_date,
            opponent,
            goals,
            xg,
            opponent_elo,
            opponent_attack_form,
            opponent_defense_form
        FROM player_matches
        ORDER BY match_date ASC
    """)
    
    matches = []
    total_goals = 0
    total_xg = 0.0
    elo_weighted_goals = 0.0
    total_opponent_elo = 0.0
    
    top_team_goals = 0  # Gol vs squadre ELO > 1600
    bottom_team_goals = 0  # Gol vs squadre ELO < 1450
    
    with engine.connect() as conn:
        rows = conn.execute(query, {"name": decoded_name, "season": season, "team_season": team_season})
        
        for row in rows:
            opponent_elo = float(row[4]) if row[4] else 1500.0
            goals = int(row[2])
            xg = float(row[3])
            
            # Goal Quality: gol contro squadre forti valgono di più
            # Formula: goals * (opponent_elo / 1500)
            quality_multiplier = opponent_elo / 1500.0
            
            matches.append({
                "date": str(row[0]),
                "opponent": row[1],
                "goals": goals,
                "xg": xg,
                "opponent_elo": round(opponent_elo, 0),
                "opponent_attack": round(float(row[5] or 0), 2),
                "opponent_defense": round(float(row[6] or 0), 2),
                "quality_score": round(quality_multiplier * goals, 2)
            })
            
            total_goals += goals
            total_xg += xg
            elo_weighted_goals += quality_multiplier * goals
            total_opponent_elo += opponent_elo
            
            # Classifica performance vs top/bottom
            if opponent_elo >= 1600:
                top_team_goals += goals
            elif opponent_elo <= 1450:
                bottom_team_goals += goals
    
    if not matches:
        raise HTTPException(status_code=404, detail="Player not found or no matches")
    
    num_matches = len(matches)
    avg_opponent_elo = total_opponent_elo / num_matches if num_matches > 0 else 1500.0
    
    # Calendar Difficulty Score (0-100)
    # 1500 = 50 (media), 1800 = 100 (difficilissimo), 1200 = 0 (facile)
    difficulty_score = min(100, max(0, ((avg_opponent_elo - 1200) / 600) * 100))
    
    # Goal Quality Index (weighted vs standard)
    goal_quality_index = (elo_weighted_goals / total_goals) if total_goals > 0 else 1.0
    
    # Fair Value Adjustment
    # Giocatori che affrontano calendari difficili meritano bonus
    difficulty_bonus_pct = (difficulty_score - 50) / 100  # da -50% a +50%
    
    return {
        "player": decoded_name,
        "season": season,
        "summary": {
            "matches_analyzed": num_matches,
            "total_goals": total_goals,
            "avg_opponent_elo": round(avg_opponent_elo, 0),
            "difficulty_score": round(difficulty_score, 1),  # 0-100
            "goal_quality_index": round(goal_quality_index, 2),  # >1 = gol contro forti
            "fair_value_difficulty_adj": round(difficulty_bonus_pct * 100, 1)  # % adjustment
        },
        "splits": {
            "vs_top_teams": {
                "goals": top_team_goals,
                "description": "Goals vs teams with ELO >= 1600"
            },
            "vs_bottom_teams": {
                "goals": bottom_team_goals,
                "description": "Goals vs teams with ELO <= 1450"
            },
            "top_bottom_ratio": round(top_team_goals / bottom_team_goals, 2) if bottom_team_goals > 0 else 0
        },
        "match_history": matches
    }


@app.get("/analytics/team/{team_id}/elo-history")
def get_team_elo_history(team_id: str, season: str = "2025"):
    """
    Storico ELO di una squadra per visualizzazione grafico.
    """
    query = text("""
        SELECT 
            match_date,
            elo,
            rolling_xg_form,
            rolling_ga_form
        FROM team_performance
        WHERE team_id = :team_id AND season = :season
        ORDER BY match_date ASC
    """)
    
    history = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"team_id": team_id, "season": season})
        for row in rows:
            history.append({
                "date": str(row[0]),
                "elo": round(float(row[1]), 0),
                "attack_form": round(float(row[2] or 0), 2),
                "defense_form": round(float(row[3] or 0), 2)
            })
    
    if not history:
        raise HTTPException(status_code=404, detail="Team not found")
    
    return {
        "team": team_id,
        "season": season,
        "current_elo": history[-1]["elo"] if history else 1500,
        "history": history
    }


@app.get("/analytics/league/strength-rankings")
def get_league_strength_rankings(season: str = "2025"):
    """
    Classifica squadre per ELO corrente + forma.
    """
    query = text("""
        SELECT DISTINCT ON (team_id)
            team_id,
            elo,
            rolling_xg_form,
            rolling_ga_form,
            match_date
        FROM team_performance
        WHERE season = :season
        ORDER BY team_id, match_date DESC
    """)
    
    teams = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"season": season})
        for row in rows:
            gf = float(row[2] or 0)
            ga = float(row[3] or 0)
            goal_diff = gf - ga
            
            teams.append({
                "team": row[0],
                "elo": round(float(row[1]), 0),
                "attack_form": round(gf, 2),
                "defense_form": round(ga, 2),
                "form_diff": round(goal_diff, 2),
                "last_update": str(row[4])
            })
    
    # Ordina per ELO
    teams.sort(key=lambda x: x["elo"], reverse=True)
    
    return {
        "season": season,
        "rankings": teams
    }


# ============================================
# LEAGUE FORECAST - Monte Carlo Simulation
# ============================================
from datetime import datetime
from functools import lru_cache
import league_simulator

# Cache per 5 minuti (evita ricalcolo se utente ricarica pagina)
_forecast_cache = {"data": None, "timestamp": None}
CACHE_DURATION_SECONDS = 300  # 5 minuti

@app.get("/analytics/league-forecast")
def get_league_forecast(season: str = "2025", simulations: int = 10000, use_cache: bool = True):
    """
    Simula il resto della stagione Serie A usando Monte Carlo (10k iterazioni).
    
    Returns:
        - Per ogni squadra: probabilità vittoria, top4, retrocessione
        - Punti medi attesi, posizione media
        - Classifica attuale e ELO corrente
    
    Query params:
        - season: Stagione da simulare (default: 2025)
        - simulations: Numero iterazioni (default: 10000, max: 50000)
        - use_cache: Se True, usa cache di 5 minuti (default: True)
    """
    global _forecast_cache
    
    # Limita simulazioni max
    simulations = min(simulations, 50000)
    
    # Check cache
    if use_cache and _forecast_cache["data"] is not None:
        elapsed = (datetime.now() - _forecast_cache["timestamp"]).total_seconds()
        if elapsed < CACHE_DURATION_SECONDS:
            print(f"📦 Usando forecast dalla cache ({int(elapsed)}s fa)")
            return {
                "cached": True,
                "cache_age_seconds": int(elapsed),
                **_forecast_cache["data"]
            }
    
    try:
        # Esegui simulazione
        forecast = league_simulator.run_simulation(season=season, n_simulations=simulations)
        
        # Ordina per probabilità vittoria
        sorted_forecast = sorted(
            forecast.items(),
            key=lambda x: (x[1]['win_league_pct'], x[1]['avg_points']),
            reverse=True
        )
        
        result = {
            "season": season,
            "simulations": simulations,
            "forecast": dict(sorted_forecast),
            "generated_at": datetime.now().isoformat()
        }
        
        # Aggiorna cache
        _forecast_cache["data"] = result
        _forecast_cache["timestamp"] = datetime.now()
        
        return {
            "cached": False,
            **result
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nella simulazione: {str(e)}"
        )
