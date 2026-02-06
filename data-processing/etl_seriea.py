import soccerdata as sd
import pandas as pd
import os
import urllib.parse
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import PlayerMatchStat, Team, League

# --- 1. SETUP ---
load_dotenv()
db_pass = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
db_url = f"postgresql://{os.getenv('DB_USER')}:{db_pass}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

# --- 2. DOWNLOAD E PREPARAZIONE ---
print("📥 Scaricamento dati Serie A...")
scraper = sd.Understat(leagues=['ITA-Serie A'], seasons='2024')
stats = scraper.read_player_match_stats().reset_index()
print(f"✅ Dati scaricati: {len(stats)} righe. Preparazione Bulk Insert...")

# Cache dei Team per non fare query inutili
# Scarichiamo tutti i team esistenti in una volta sola
# SQLAlchemy compatibility: session.query(...).all() returns list of 1-tuples
existing_teams = {r[0] for r in session.query(Team.id).all()}
teams_to_add = set()
bulk_stats = []

# --- 3. ELABORAZIONE IN MEMORIA (VELOCISSIMA) ---
for index, row in stats.iterrows():
    try:
        minutes = int(row['minutes'])
        if minutes == 0: continue

        # Parsing dati
        game_str = row['game']
        date_str = game_str.split(' ')[0]
        raw_match = game_str.split(' ', 1)[1]
        team_id_clean = row['team'].replace(" ", "_")
        team_name = row['team']
        opponent_name = raw_match.replace(team_name, "").replace("-", "").strip()
        if not opponent_name:
            opponent_name = "Unknown"

        team_id_clean = team_name.replace(" ", "_")
        
        # Gestione Team (in memoria)
        if team_id_clean not in existing_teams and team_id_clean not in teams_to_add:
            teams_to_add.add(team_id_clean)

        # Prepariamo il dizionario per l'inserimento massivo
        # Nota: usiamo i nomi delle colonne del DB
        bulk_stats.append({
            'player_name': row['player'],
            'team_id': team_id_clean,
            'match_date': pd.to_datetime(date_str).date(),
            'minutes': minutes,
            'goals': int(row['goals']),
            'assists': int(row['assists']),
            'shots': int(row['shots']),
            'shots_on_target': 0, 
            'opponent': opponent_name,
            'xg': float(row['xg']),
            'npxg': float(row['xg']) # Fallback
        })

    except Exception as e:
        continue # Saltiamo errori di parsing silenziosamente per velocità

# --- 4. SCRITTURA SU DB (BULK) ---

# Prima di inserire le team assicuriamoci che la League esista (evita FK violation)
league_id = 'ITA-Serie A'
league = session.query(League).filter_by(id=league_id).first()
if not league:
    print(f"🛠️ League '{league_id}' non trovata — la creo automaticamente.")
    session.execute(
        insert(League),
        [{'id': league_id, 'name': 'Serie A', 'country': 'Italy'}]
    )
    session.commit()

# A. Inseriamo i nuovi team (se ce ne sono)
if teams_to_add:
    print(f"🆕 Inserimento di {len(teams_to_add)} nuove squadre...")
    session.execute(
        insert(Team),
        [{'id': t, 'league_id': league_id} for t in teams_to_add]
    )
    session.commit()

# B. Inseriamo le statistiche (a blocchi di 1000 per sicurezza)
print(f"🚀 Inserimento veloce di {len(bulk_stats)} prestazioni...")

# Usiamo una tecnica chiamata "Chunking"
chunk_size = 2000
for i in range(0, len(bulk_stats), chunk_size):
    chunk = bulk_stats[i:i + chunk_size]
    session.execute(insert(PlayerMatchStat), chunk)
    session.commit()
    print(f"   ...scritti {min(i + chunk_size, len(bulk_stats))} record.")

print("🏁 FINITO! Tempo stimato: < 30 secondi.")