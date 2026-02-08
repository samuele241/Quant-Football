import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
import os
from dotenv import load_dotenv
from tqdm import tqdm # Installalo con: pip install tqdm

load_dotenv()

# Setup Database
DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

def migrate():
    print("🚀 Inizio Migrazione Database in 'Shadow Mode'...")
    
    with engine.connect() as conn:
        # 1. Carichiamo TUTTI i dati vecchi in memoria (pandas è efficiente per questo volume)
        print("📥 Caricamento dati grezzi...")
        raw_df = pd.read_sql("SELECT * FROM v_full_match_stats", conn)
        print(f"   Trovate {len(raw_df)} righe di statistiche.")

        # --- FASE 1: POPOLARE PLAYERS ---
        print("👤 Migrazione Giocatori...")
        unique_players = raw_df['player_name'].unique()
        
        player_map = {} # Dizionario { 'Lautaro': player_id }
        
        for name in tqdm(unique_players, desc="Players"):
            # Inseriamo o ignoriamo se esiste già
            try:
                # Insert e ritorna ID
                result = conn.execute(
                    text("INSERT INTO players (name) VALUES (:name) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING player_id"),
                    {"name": name}
                )
                player_id = result.fetchone()[0]
                player_map[name] = player_id
            except Exception as e:
                print(f"Errore su {name}: {e}")

        conn.commit()
        print(f"✅ Mappati {len(player_map)} giocatori unici.")

        # --- FASE 2: POPOLARE MATCHES E STATS ---
        print("⚽️ Migrazione Partite e Stats (Questo richiederà tempo)...")
        
        match_map = {} # Chiave (date, team_a, team_b) -> match_id
        stats_count = 0

        # Iteriamo su ogni riga del vecchio DB
        for index, row in tqdm(raw_df.iterrows(), total=raw_df.shape[0], desc="Rows"):
            try:
                # 1. Identificazione Partita
                # Dobbiamo creare una chiave unica per la partita. 
                # Assumiamo: Date + (Team, Opponent) ordinati alfabeticamente per evitare duplicati A-B vs B-A
                teams = sorted([row['team_id'], row['opponent']])
                match_key = (row['match_date'], teams[0], teams[1])
                
                if match_key not in match_map:
                    # Creiamo la partita
                    # Nota: Non sappiamo chi è casa/fuori dai dati vecchi in modo affidabile senza 'h_a' column
                    # Assumiamo convenzionalmente teams[0] home, teams[1] away per l'ID, ma salviamo i dati
                    res = conn.execute(
                        text("""
                            INSERT INTO matches (season, date, home_team_id, away_team_id)
                            VALUES (:season, :date, :h, :a)
                            ON CONFLICT (date, home_team_id, away_team_id) DO UPDATE SET season=EXCLUDED.season
                            RETURNING match_id
                        """),
                        {
                            "season": row['season'],
                            "date": row['match_date'],
                            "h": teams[0],
                            "a": teams[1]
                        }
                    )
                    match_id = res.fetchone()[0]
                    match_map[match_key] = match_id
                else:
                    match_id = match_map[match_key]

                # 2. Inserimento Statistiche Collegate
                conn.execute(
                    text("""
                        INSERT INTO player_stats_v2 
                        (player_id, match_id, team_id, minutes, goals, assists, shots, shots_on_target, npxg, xa, fair_value)
                        VALUES (:pid, :mid, :tid, :mins, :gls, :ast, :sh, :sot, :npxg, :xa, :fv)
                    """),
                    {
                        "pid": player_map[row['player_name']],
                        "mid": match_id,
                        "tid": row['team_id'],
                        "mins": row['minutes'],
                        "gls": row['goals'],
                        "gls": row['goals'],
                        "ast": row['assists'],
                        "sh": row['shots'],
                        "sot": row['shots_on_target'],
                        "npxg": row['npxg'] if row['npxg'] else 0, # Handle None
                        "xa": 0.0, # Se non avevi la colonna xa nel vecchio, metti 0 o correggi
                        "fv": row['fair_value']
                    }
                )
                stats_count += 1
                
            except Exception as e:
                print(f"Errore riga {index}: {e}")

        conn.commit()
        print(f"✅ Migrazione completata. Inserite {len(match_map)} partite e {stats_count} statistiche.")

if __name__ == "__main__":
    migrate()