import requests
import io
import pandas as pd
import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

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

# Config
SEASONS_TO_LOAD = ['2425', '2526']
ELO_K_FACTOR = 32
ELO_INITIAL = 1500
HOME_ADVANTAGE = 100

def normalize_team_name(name: str) -> str:
    # Mappatura per allineare i nomi di Football-Data con Understat/Supabase
    mapping = {
        'AC Milan': 'AC_Milan', 'Inter': 'Inter', 'Juventus': 'Juventus',
        'Napoli': 'Napoli', 'Roma': 'Roma', 'Lazio': 'Lazio',
        'Fiorentina': 'Fiorentina', 'Atalanta': 'Atalanta', 'Torino': 'Torino',
        'Verona': 'Verona', 'Hellas Verona': 'Verona', 'Lecce': 'Lecce',
        'Udinese': 'Udinese', 'Bologna': 'Bologna', 'Empoli': 'Empoli',
        'Monza': 'Monza', 'Genoa': 'Genoa', 'Cagliari': 'Cagliari',
        'Parma': 'Parma_Calcio', 'Como': 'Como', 'Venezia': 'Venezia',
        'Salernitana': 'Salernitana', 'Sassuolo': 'Sassuolo', 'Frosinone': 'Frosinone'
    }
    return mapping.get(name.strip(), name.strip().replace(' ', '_'))

def update_team_context():
    print("\n📊 AVVIO AGGIORNAMENTO CONTESTO SQUADRE (ELO & FORMA)")
    
    # 1. Download Dati
    df_list = []
    base_url = "https://www.football-data.co.uk/mmz4281/{}/I1.csv"
    
    for season in SEASONS_TO_LOAD:
        print(f"   📥 Scaricamento stagione {season}...", end=" ")
        try:
            s = requests.get(base_url.format(season)).content
            df_temp = pd.read_csv(io.StringIO(s.decode('latin-1')))
            df_temp['season_code'] = season
            df_list.append(df_temp)
            print("OK")
        except Exception as e:
            print(f"ERRORE: {e}")

    if not df_list: return

    full_df = pd.concat(df_list).dropna(subset=['Date', 'HomeTeam', 'AwayTeam', 'FTR'])
    full_df['Date'] = pd.to_datetime(full_df['Date'], dayfirst=True)
    full_df = full_df.sort_values('Date')

    # 2. Calcolo ELO
    team_elo = {}
    history_xg = {} # Per la rolling form (simulata coi gol se non abbiamo xG qui)
    records = []

    print(f"   🧮 Ricalcolo metriche su {len(full_df)} partite...")

    for _, row in full_df.iterrows():
        home = normalize_team_name(row['HomeTeam'])
        away = normalize_team_name(row['AwayTeam'])
        
        if home not in team_elo: team_elo[home] = ELO_INITIAL
        if away not in team_elo: team_elo[away] = ELO_INITIAL

        # Calcolo ELO
        diff = (team_elo[home] + HOME_ADVANTAGE) - team_elo[away]
        exp_home = 1 / (1 + 10 ** (-diff / 400))
        
        result = 1.0 if row['FTR'] == 'H' else (0.5 if row['FTR'] == 'D' else 0.0)
        
        new_elo_home = team_elo[home] + ELO_K_FACTOR * (result - exp_home)
        new_elo_away = team_elo[away] + ELO_K_FACTOR * ((1 - result) - (1 - exp_home))
        
        team_elo[home] = new_elo_home
        team_elo[away] = new_elo_away

        # Calcolo Forma (Usa Gol Fatti come proxy di xG se non c'è xG nel CSV)
        # Nota: Football-Data.co.uk ha gol, non xG. Per xG reali usiamo update_team_stats.py interno.
        # Questo script è utile come backup o per dati storici pre-Understat.
        
        records.append({
            "team_id": home, "match_date": row['Date'], "season": row['season_code'],
            "elo": round(new_elo_home, 2), "rolling_xg_form": 0.0 # Placeholder
        })
        records.append({
            "team_id": away, "match_date": row['Date'], "season": row['season_code'],
            "elo": round(new_elo_away, 2), "rolling_xg_form": 0.0
        })

    # 3. Salvataggio
    print(f"   💾 Aggiornamento tabella team_performance ({len(records)} record)...")
    with engine.begin() as conn:
        # Usa INSERT ON CONFLICT o TRUNCATE per semplicità se ricalcoli tutto
        conn.execute(text("TRUNCATE TABLE team_performance RESTART IDENTITY"))
        
        # Bulk Insert
        conn.execute(
            text("""
                INSERT INTO team_performance (team_id, match_date, season, elo, rolling_xg_form)
                VALUES (:team_id, :match_date, :season, :elo, :rolling_xg_form)
            """),
            records
        )
    print("✅ Contesto Squadre Aggiornato.")

if __name__ == "__main__":
    update_team_context()