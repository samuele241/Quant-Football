import soccerdata as sd
import pandas as pd
import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import sys

# Aggiungiamo il path per importare moduli dal backend se necessario
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from fetch_ages import update_ages # Importiamo la funzione specifica se l'hai creata, o usiamo subprocess
except ImportError:
    pass # Gestiremo con subprocess se l'import fallisce

load_dotenv()

# Setup Database
db_user = os.getenv('DB_USER', '').strip()
db_password = os.getenv('DB_PASSWORD', '').strip()
db_host = os.getenv('DB_HOST', '').strip()
db_port = os.getenv('DB_PORT', '').strip() or '5432'
db_name = os.getenv('DB_NAME', '').strip()

db_pass = urllib.parse.quote_plus(db_password)
db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(db_url)

def get_or_create_player(conn, player_name, team_id, new_players_list):
    """Restituisce l'ID del giocatore. Se non esiste, lo crea."""
    # 1. Cerca ID
    res = conn.execute(text("SELECT player_id FROM players WHERE name = :name"), {"name": player_name}).fetchone()
    if res:
        return res[0]
    
    # 2. Crea se non esiste
    print(f"   👤 Nuovo giocatore trovato: {player_name}")
    res = conn.execute(
        text("INSERT INTO players (name, current_team_id) VALUES (:name, :tid) RETURNING player_id"),
        {"name": player_name, "tid": team_id}
    ).fetchone()
    
    new_players_list.add(player_name) # Aggiungiamo alla lista per fetch_ages
    return res[0]

def get_or_create_match(conn, date, season, home_team, away_team):
    """Restituisce l'ID della partita. Se non esiste, la crea."""
    # Chiave univoca: Data + Squadre
    res = conn.execute(
        text("""
            SELECT match_id FROM matches 
            WHERE date = :date AND home_team_id = :h AND away_team_id = :a
        """),
        {"date": date, "h": home_team, "a": away_team}
    ).fetchone()
    
    if res:
        return res[0]
    
    # Crea nuova partita
    res = conn.execute(
        text("""
            INSERT INTO matches (season, date, home_team_id, away_team_id)
            VALUES (:s, :d, :h, :a)
            RETURNING match_id
        """),
        {"s": season, "d": date, "h": home_team, "a": away_team}
    ).fetchone()
    return res[0]

def etl_season_v2(season_id: str):
    print(f"\n🚀 Avvio ETL V2 per stagione {season_id}...")
    
    # 1. Scarica Dati Understat
    scraper = sd.Understat(leagues=['ITA-Serie A'], seasons=season_id)
    stats = scraper.read_player_match_stats().reset_index()
    print(f"✅ Dati scaricati: {len(stats)} righe.")

    new_players_found = set()
    stats_buffer = []

    with engine.begin() as conn:
        # Pulizia preventiva dei dati V2 per questa stagione (per evitare duplicati in fase di dev)
        # Nota: In produzione potresti voler fare "Upsert" invece di Delete/Insert
        # Per ora manteniamo la logica semplice: puliamo le stats, non matches/players
        print("   🧹 Pulizia statistiche vecchie per la stagione corrente...")
        conn.execute(
            text("DELETE FROM player_stats_v2 WHERE match_id IN (SELECT match_id FROM matches WHERE season = :s)"),
            {"s": season_id}
        )

        for index, row in stats.iterrows():
            try:
                minutes = int(row.get('minutes', 0) or 0)
                if minutes == 0: continue

                # Parsing Dati
                player_name = row['player']
                team_name = row['team'].replace(' ', '_') # Normalizzazione base
                game_str = row['game'] # Es: "2024-08-19 Juventus - Como 3:0"
                date_val = pd.to_datetime(row['date'])

                # Parsing Partita (Home vs Away) da "Juventus - Como"
                # Understat format: "Date Home - Away Score"
                parts = game_str.split(' ', 1)[1] # Rimuovi data iniziale
                matchup = parts.rsplit(' ', 1)[0] # Rimuovi punteggio finale
                if ' - ' in matchup:
                    home_team_raw, away_team_raw = matchup.split(' - ')
                    home_team = home_team_raw.strip().replace(' ', '_')
                    away_team = away_team_raw.strip().replace(' ', '_')
                else:
                    # Fallback se il parsing fallisce
                    home_team = team_name
                    away_team = "Unknown"

                # 1. Gestione Player
                p_id = get_or_create_player(conn, player_name, team_name, new_players_found)

                # 2. Gestione Match
                m_id = get_or_create_match(conn, date_val, season_id, home_team, away_team)

                # 3. Preparazione Statistiche
                stats_buffer.append({
                    "player_id": p_id,
                    "match_id": m_id,
                    "team_id": team_name,
                    "minutes": minutes,
                    "goals": int(row.get('goals') or 0),
                    "assists": int(row.get('assists') or 0),
                    "shots": int(row.get('shots') or 0),
                    "shots_on_target": int(row.get('shots_on_target') or 0),
                    "npxg": float(row.get('npxg') or 0.0),
                    "xa": float(row.get('xa') or 0.0),
                    "fair_value": 0.0 # Sarà calcolato dal Valuation Engine
                })

            except Exception as e:
                print(f"   ⚠️ Errore riga {index}: {e}")
                continue
        
        # Bulk Insert Stats
        if stats_buffer:
            print(f"   💾 Inserimento di {len(stats_buffer)} record in player_stats_v2...")
            conn.execute(
                text("""
                    INSERT INTO player_stats_v2 
                    (player_id, match_id, team_id, minutes, goals, assists, shots, shots_on_target, npxg, xa, fair_value)
                    VALUES (:player_id, :match_id, :team_id, :minutes, :goals, :assists, :shots, :shots_on_target, :npxg, :xa, :fair_value)
                """),
                stats_buffer
            )

    # 4. Trigger Età (Se ci sono nuovi giocatori)
    if new_players_found:
        print(f"\n🎂 Trovati {len(new_players_found)} nuovi giocatori. Avvio ricerca età...")
        import subprocess
        # Eseguiamo lo script fetch_ages.py come sottoprocesso
        subprocess.run(["python", "backend/fetch_ages.py"])
    else:
        print("\n✅ Nessun nuovo giocatore da analizzare.")

if __name__ == '__main__':
    # Esegui per la stagione corrente e passata
    etl_season_v2('2024')
    etl_season_v2('2025')