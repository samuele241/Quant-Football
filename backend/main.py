import os
import urllib.parse
import unicodedata  # For name normalization
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import quant_engine #C++ Module

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

@app.get("/")
def read_root():
    return {"status": "System Operational", "engine": "Hybrid Python/C++"}

# DEBUG ENDPOINT: Vedi tutti i giocatori disponibili
@app.get("/analytics/scouting/available-players")
def get_available_players(season: str = "2025", limit: int = 50):
    """Mostra i giocatori disponibili per la ricerca similarity."""
    query = text("""
        SELECT player_name, 
               team_id,
               SUM(goals) as total_goals,
               SUM(minutes) as total_mins
        FROM player_match_stats
        WHERE season = :season
        GROUP BY player_name, team_id
        HAVING SUM(minutes) > 90
        ORDER BY SUM(goals) DESC
        LIMIT :limit
    """)
    
    players = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"season": season, "limit": limit})
        for row in rows:
            players.append({
                "name": row[0],
                "team": row[1],
                "goals": row[2],
                "minutes": row[3]
            })
    
    return {
        "season": season,
        "total_players": len(players),
        "players": players
    }

# 1. NUOVO ENDPOINT: Lista Squadre
@app.get("/analytics/teams")
def get_teams(season: str = "2025"):
    # Prende tutte le squadre che hanno giocato in quella stagione
    query = text("""
        SELECT DISTINCT t.id 
        FROM teams t
        JOIN player_match_stats pms ON t.id = pms.team_id
        WHERE pms.season = :season
        ORDER BY t.id ASC
    """)
    teams = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"season": season})
        for row in rows:
            # Puliamo l'ID (es. "AC_Milan" -> "AC Milan") per visualizzazione
            display_name = row[0].replace("_", " ")
            teams.append({"id": row[0], "name": display_name})
    return teams

# 2. UPDATE: Top Scorers con Filtro Team
@app.get("/analytics/top-scorers")
def get_top_scorers(season: str = "2025", team_id: str = None): # Aggiunto team_id
    
    # Base Query
    sql = """
        SELECT player_name, 
               array_agg(xg) as xg_history, 
               array_agg(goals) as goal_history,
               SUM(goals) as total_goals
        FROM player_match_stats
        WHERE season = :season
    """
    
    params = {"season": season}
    
    # SE C'È UN FILTRO SQUADRA: Aggiungiamo WHERE e togliamo il LIMIT
    if team_id and team_id != "all":
        sql += " AND team_id = :team_id"
        params["team_id"] = team_id
        limit_clause = "" # Mostra tutti i giocatori della squadra
    else:
        # Se non c'è filtro, mostriamo solo la Top 10 globale
        limit_clause = "LIMIT 10"

    sql += f"""
        GROUP BY player_name
        HAVING SUM(minutes) > 90  -- Minimo filtro per non vedere chi ha giocato 1 minuto
        ORDER BY total_goals DESC
        {limit_clause}
    """
    
    results = []
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params)
        for row in rows:
            xg_vector = [float(x) for x in row[1]] 
            goal_vector = [int(g) for g in row[2]]
            efficiency_score = quant_engine.calculate_efficiency(xg_vector, goal_vector)
            
            results.append({
                "player": row[0],
                "goals": row[3],
                "quant_efficiency_score": round(efficiency_score, 4)
            })
    
    results.sort(key=lambda x: x["quant_efficiency_score"], reverse=True)
    return results

@app.get("/analytics/player/{player_name}")
def get_player_history(player_name: str, season: str | None = None):
    decoded_name = urllib.parse.unquote(player_name)
    
    # Aggiungi 'minutes', 'shots', 'season' e 'fair_value' alla query
    if season:
        query = text("""
            SELECT match_date, goals, xg, team_id, opponent, minutes, shots, season, fair_value
            FROM player_match_stats
            WHERE player_name = :name AND season = :season
            ORDER BY match_date ASC
        """)
    else:
        query = text("""
            SELECT match_date, goals, xg, team_id, opponent, minutes, shots, season, fair_value
            FROM player_match_stats
            WHERE player_name = :name
            ORDER BY match_date ASC
        """)
    
    history = []
    goals_vector = []
    
    # Variabili per i totali
    total_goals = 0
    total_shots = 0
    total_minutes = 0
    total_xg = 0.0
    fair_values = []  # Per calcolare la media

    with engine.connect() as conn:
        if season:
            rows = conn.execute(query, {"name": decoded_name, "season": season})
        else:
            rows = conn.execute(query, {"name": decoded_name})
        for row in rows:
            # Accumulo i totali
            g = int(row[1])
            xg = float(row[2])
            mins = int(row[5])
            s = int(row[6])
            row_season = row[7]
            fv = float(row[8]) if row[8] else 0.0

            total_goals += g
            total_xg += xg
            total_minutes += mins
            total_shots += s
            if fv > 0:
                fair_values.append(fv)

            history.append({
                "date": row[0],
                "goals": g,
                "xg": xg,
                "team": row[3],
                "opponent": row[4],
                "season": row_season
            })
            goals_vector.append(float(g))

    # --- CALCOLO METRICHE AVANZATE ---
    
    # 1. Shot Conversion Rate (Gol / Tiri)
    conversion_rate = 0.0
    if total_shots > 0:
        conversion_rate = (total_goals / total_shots) * 100

    # 2. Goals per 90 minuti
    goals_p90 = 0.0
    if total_minutes > 0:
        goals_p90 = (total_goals / total_minutes) * 90

    # 3. xG Overperformance (Totale)
    xg_diff = total_goals - total_xg
    
    # 4. Fair Value medio
    avg_fair_value = sum(fair_values) / len(fair_values) if fair_values else 0.0

    # --- C++ TREND (Già presente) ---
    recent_goals = goals_vector[-5:] if len(goals_vector) >= 5 else goals_vector
    trend_score = quant_engine.calculate_trend(recent_goals)

    return {
        "player": decoded_name,
        "trend_slope": round(trend_score, 4),
        "advanced_metrics": {
            "conversion_rate": round(conversion_rate, 1),
            "goals_per_90": round(goals_p90, 2),
            "total_shots": total_shots,
            "xg_diff": round(xg_diff, 2),
            "fair_value": round(avg_fair_value, 0)  # NUOVO: Valore di mercato stimato
        },
        "history": history
    }


@app.get("/analytics/prediction/{player_name}")
def get_prediction(player_name: str, season: str = '2025'):
    """Monte Carlo prediction basata sulla stagione specificata (default '2025').

    Restituisce: matches_played, matches_remaining, current_goals, predicted_mean, percentiles
    """
    SEASON = season
    decoded_name = urllib.parse.unquote(player_name)

    # Recuperiamo tutte le prestazioni nella stagione richiesta
    query = text("""
        SELECT goals
        FROM player_match_stats
        WHERE player_name = :name AND season = :season
        ORDER BY match_date ASC
    """)

    goals_list = []
    with engine.connect() as conn:
        rows = conn.execute(query, {"name": decoded_name, "season": SEASON})
        for r in rows:
            goals_list.append(int(r[0] or 0))

    matches_played = len(goals_list)
    TOTAL_MATCHES = 38
    matches_remaining = max(0, TOTAL_MATCHES - matches_played)
    current_goals = sum(goals_list)

    # If no historical goals exist for the season, return a simple empty prediction
    if matches_remaining == 0 or matches_played == 0:
        return {
            "player": decoded_name,
            "season": SEASON,
            "matches_played": matches_played,
            "matches_remaining": matches_remaining,
            "current_goals": current_goals,
            "predicted_mean_total_goals": current_goals,
            "percentiles": {"p10": current_goals, "p50": current_goals, "p90": current_goals},
            "simulation": [{"total_goals": current_goals, "probability": 1.0}]
        }

    # Monte Carlo: sample per-match goals from existing distribution (bootstrap)
    import random
    TRIALS = 10000
    totals = []
    for _ in range(TRIALS):
        sim = current_goals
        for _m in range(matches_remaining):
            # sample with replacement from historical per-match goals
            sim += random.choice(goals_list)
        totals.append(sim)

    totals.sort()
    mean_pred = sum(totals) / len(totals)
    p10 = totals[int(0.10 * len(totals))]
    p50 = totals[int(0.50 * len(totals))]
    p90 = totals[int(0.90 * len(totals))]

    # Build an empirical distribution (total_goals -> probability)
    from collections import Counter
    counter = Counter(totals)
    simulation = [
        {"total_goals": total, "probability": round(count / len(totals), 4)}
        for total, count in sorted(counter.items())
    ]

    return {
        "player": decoded_name,
        "season": SEASON,
        "matches_played": matches_played,
        "matches_remaining": matches_remaining,
        "current_goals": current_goals,
        "predicted_mean_total_goals": round(mean_pred, 2),
        "percentiles": {"p10": p10, "p50": p50, "p90": p90},
        "simulation": simulation
    }

# ... (altri import) ...

@app.get("/analytics/scouting/similar/{player_name}")
def get_similar_players(player_name: str, season: str = "2025"):
    """Find similar players using hybrid similarity algorithm with name normalization."""
    
    def normalize_name(name: str) -> str:
        """Normalizza il nome: lowercase + rimuove accenti."""
        # Rimuove accenti (NFD = Normalization Form Decomposed)
        nfd = unicodedata.normalize('NFD', name)
        without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
        return without_accents.lower().strip()
    
    def infer_position(goals_p90: float, shots_p90: float, assists_p90: float, minutes: int) -> str:
        """Inferisce il ruolo del giocatore dalle statistiche."""
        # Filtro: ignora chi ha giocato troppo poco (< 270 minuti = ~3 partite)
        if minutes < 270:
            return "BENCH_PLAYER"
        
        # ATTACCANTE: alto volume di tiri e goal
        if shots_p90 >= 2.5 and goals_p90 >= 0.35:
            return "STRIKER"
        
        # ALA/ATTACCANTE MOBILE: tiri moderati, goal + assist
        if shots_p90 >= 1.5 and (goals_p90 >= 0.20 or assists_p90 >= 0.25):
            return "WINGER"
        
        # CENTROCAMPISTA OFFENSIVO: più assist che goal, alcuni tiri
        if assists_p90 >= 0.15 and shots_p90 >= 0.8:
            return "MIDFIELDER_OFF"
        
        # CENTROCAMPISTA/DIFENSORE: pochi tiri, pochi goal
        if shots_p90 < 1.0 and goals_p90 < 0.15:
            return "DEFENDER_MID"
        
        # FALLBACK: medio-campo generico
        return "MIDFIELDER"
    
    decoded_name = urllib.parse.unquote(player_name)
    normalized_search = normalize_name(decoded_name)
    
    # 1. Query ampliata: aggiungiamo assists e shots_on_target + fair_value
    query = text("""
        SELECT player_name, 
               team_id,
               SUM(goals) as total_goals, 
               SUM(xg) as total_xg, 
               SUM(minutes) as total_mins,
               SUM(shots) as total_shots,
               SUM(assists) as total_assists,
               array_agg(xg), array_agg(goals),
               AVG(fair_value) as avg_fair_value
        FROM player_match_stats
        WHERE season = :season
        GROUP BY player_name, team_id
        HAVING SUM(minutes) > 90
    """)
    
    players_data = []
    target_idx = -1
    
    with engine.connect() as conn:
        rows = conn.execute(query, {"season": season}).fetchall()
        
        # 2. Creiamo i vettori delle feature (Feature Engineering)
        feature_matrix = [] # Matrice per il C++
        metadata_list = []  # Lista parallela con i nomi
        
        for idx, row in enumerate(rows):
            name = row[0]
            team = row[1]
            mins = row[4]
            
            # Calcolo metriche P90 (Per 90 minuti)
            goals_p90 = (row[2] / mins) * 90
            xg_p90 = (row[3] / mins) * 90
            shots_p90 = (row[5] / mins) * 90
            assists_p90 = (row[6] / mins) * 90
            
            # Calcolo efficienza (usando la funzione C++ esistente)
            xg_vec = [float(x) for x in row[7]]
            g_vec = [int(g) for g in row[8]]
            eff = quant_engine.calculate_efficiency(xg_vec, g_vec)
            
            # Fair Value (media delle valutazioni per partita)
            fair_val = float(row[9]) if row[9] else 0.0
            
            # INFERENZA RUOLO AUTOMATICA
            position = infer_position(goals_p90, shots_p90, assists_p90, mins)
            
            # IL NOSTRO "DNA" DEL GIOCATORE (ora con assists)
            vector = [goals_p90, xg_p90, shots_p90, assists_p90, eff]
            
            feature_matrix.append(vector)
            metadata_list.append({
                "player": name,
                "team": team,
                "position": position,  # NUOVO!
                "fair_value": round(fair_val, 1),  # NUOVO!
                "stats": {
                    "goals_p90": round(goals_p90, 2),
                    "xg_p90": round(xg_p90, 2),
                    "assists_p90": round(assists_p90, 2),
                    "efficiency": round(eff, 2),
                    "fair_value": round(fair_val, 0)  # Aggiungi fair_value alle stats per il frontend
                }
            })
            
            # Match case-insensitive con accenti normalizzati (priorità match esatti)
            normalized_db_name = normalize_name(name)
            # Priorità 1: Match esatto del nome completo
            if normalized_db_name == normalized_search:
                target_idx = idx
                break
            # Priorità 2: Il nome cercato inizia con la query (es. "Lautaro Martínez" starts with "lautaro")
            if target_idx == -1 and normalized_db_name.startswith(normalized_search):
                target_idx = idx
            # Priorità 3: La query è contenuta nel nome (fallback)
            if target_idx == -1 and normalized_search in normalized_db_name:
                target_idx = idx

    if target_idx == -1:
        return {"error": f"Player '{decoded_name}' not found or played less than 90 mins"}

    target_position = metadata_list[target_idx]["position"]
    
    # FILTRO: Considera SOLO giocatori dello stesso ruolo
    same_position_indices = [i for i, meta in enumerate(metadata_list) if meta["position"] == target_position]
    
    # Se ci sono meno di 6 giocatori nello stesso ruolo, amplia la ricerca
    if len(same_position_indices) < 6:
        # Fallback: include ruoli "vicini"
        compatible_positions = {
            "STRIKER": ["STRIKER", "WINGER"],
            "WINGER": ["WINGER", "STRIKER", "MIDFIELDER_OFF"],
            "MIDFIELDER_OFF": ["MIDFIELDER_OFF", "WINGER", "MIDFIELDER"],
            "MIDFIELDER": ["MIDFIELDER", "MIDFIELDER_OFF", "DEFENDER_MID"],
            "DEFENDER_MID": ["DEFENDER_MID", "MIDFIELDER"]
        }
        allowed = compatible_positions.get(target_position, [target_position])
        same_position_indices = [i for i, meta in enumerate(metadata_list) if meta["position"] in allowed]
    
    # 3. NORMALIZZAZIONE MIN-MAX (solo sui giocatori dello stesso ruolo)
    # Crea subset della feature matrix con solo i giocatori compatibili
    filtered_matrix = [feature_matrix[i] for i in same_position_indices]
    filtered_metadata = [metadata_list[i] for i in same_position_indices]
    
    # Trova l'indice del target nel nuovo array filtrato
    target_idx_filtered = same_position_indices.index(target_idx)
    
    # Trova min e max per ogni metrica (solo nel subset filtrato)
    cols = len(filtered_matrix[0]) if filtered_matrix else 0
    mins = [float('inf')] * cols
    maxs = [float('-inf')] * cols

    # Trova range di ogni feature
    for rowv in filtered_matrix:
        for c in range(cols):
            if rowv[c] < mins[c]:
                mins[c] = rowv[c]
            if rowv[c] > maxs[c]:
                maxs[c] = rowv[c]

    # Applica Min-Max Normalization (scala 0-1)
    norm_matrix = []
    for rowv in filtered_matrix:
        norm_row = []
        for c in range(cols):
            # (value - min) / (max - min)
            range_val = maxs[c] - mins[c]
            if range_val > 0:
                normalized = (rowv[c] - mins[c]) / range_val
            else:
                normalized = 0.0  # Se tutti i valori sono uguali
            norm_row.append(normalized)
        norm_matrix.append(norm_row)

    target_vector = norm_matrix[target_idx_filtered]
    target_raw = filtered_matrix[target_idx_filtered]  # Vettore originale per fallback
    target_player_name = filtered_metadata[target_idx_filtered]["player"]  # Nome reale del giocatore trovato
    
    # Chiediamo più risultati al C++ (top 20 per avere margine)
    similarity_results = quant_engine.find_similar_players(target_vector, norm_matrix, min(20, len(norm_matrix)))
    
    # 4. Formattazione Risultati
    matches = []
    for idx, score in similarity_results:
        if idx == target_idx_filtered:  # Saltiamo se stesso
            continue
            
        player_meta = filtered_metadata[idx]
        matches.append({
            "player": player_meta["player"],
            "team": player_meta["team"],
            "similarity": round(score * 100, 1),
            "data": player_meta["stats"]
        })
    
    # 5. FALLBACK INTELLIGENTE: Se abbiamo meno di 5 match, usiamo distanza euclidea
    if len(matches) < 5:
        import math
        
        # Calcola distanza euclidea per tutti i giocatori (nello stesso ruolo!)
        distances = []
        for idx, rowv in enumerate(filtered_matrix):
            if idx == target_idx_filtered:
                continue
            
            # Distanza euclidea normalizzata
            dist = 0.0
            for c in range(cols):
                diff = (rowv[c] - target_raw[c])
                dist += diff * diff
            dist = math.sqrt(dist)
            
            distances.append((idx, dist))
        
        # Ordina per distanza (più piccola = più simile)
        distances.sort(key=lambda x: x[1])
        
        # Prendi i top 10 e converti in similarity score (inverso della distanza)
        fallback_matches = []
        for idx, dist in distances[:10]:
            player_meta = filtered_metadata[idx]
            # Converti distanza in similarity (0-100)
            # Usa una funzione sigmoid-like per avere score più umani
            max_dist = 100  # Distanza massima "ragionevole"
            similarity_score = max(0, (1 - min(dist / max_dist, 1)) * 100)
            
            fallback_matches.append({
                "player": player_meta["player"],
                "team": player_meta["team"],
                "similarity": round(similarity_score, 1),
                "data": player_meta["stats"]
            })
        
        # Merge: usa i match esistenti + fallback per arrivare a 5
        existing_names = {m["player"] for m in matches}
        for fb in fallback_matches:
            if fb["player"] not in existing_names and len(matches) < 5:
                matches.append(fb)
    
    # Limita a 5 risultati finali e ordina per similarity
    matches = sorted(matches, key=lambda x: x["similarity"], reverse=True)[:5]
    
    return {
        "target": target_player_name,  # Nome reale del giocatore dal database
        "position": target_position,  # NUOVO: mostra il ruolo inferito
        "matches": matches,
        "algorithm": "hybrid_cosine_euclidean" if len(similarity_results) < 5 else "cosine_similarity"
    }


@app.get("/analytics/scouting/suggest")
def suggest_players(q: str):
    """Return up to 10 player name suggestions matching the query (case-insensitive)."""
    if not q or len(q.strip()) < 1:
        return []

    query = text("""
        SELECT DISTINCT player_name
        FROM player_match_stats
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
    
    # Map season format: player_match_stats usa "2025", team_performance usa "2526"
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
            FROM player_match_stats pms
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
