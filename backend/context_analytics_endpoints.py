"""
Analisi Contestuali - Context Analytics Endpoints

Questi endpoint integrano i dati team_performance (ELO, Forma) 
con le statistiche giocatori per fornire metriche avanzate.
"""

import urllib.parse
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from db_connect import engine
router = APIRouter()


# Aggiungi dopo gli import esistenti in main.py:

@router.get("/analytics/player/{player_name}/context")
def get_player_context_analysis(player_name: str, season: str = "2025"):
    """
    Analisi contestuale avanzata per un giocatore:
    - Difficoltà calendario (media ELO avversari)
    - Performance vs Top/Bottom teams
    - Fair Value Adjustment basato su opposizione
    - Goal Quality Score (gol contro squadre forti valgono di più)
    """
    decoded_name = urllib.parse.unquote(player_name)
    
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
            FROM player_match_stats pms
            LEFT JOIN team_performance tp 
                ON pms.opponent = tp.team_id 
                AND pms.match_date = tp.match_date
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
        rows = conn.execute(query, {"name": decoded_name, "season": season})
        
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


@router.get("/analytics/team/{team_id}/elo-history")
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


@router.get("/analytics/league/strength-rankings")
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
