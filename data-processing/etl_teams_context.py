"""
ETL Team Performance Context
==============================
Questo script scarica dati storici da football-data.co.uk e calcola:
- ELO Rating per ogni squadra
- Forma (Rolling xG e GA ultimi 5 match)

Integrazione con il progetto:
------------------------------
1. Esegui DOPO init_db.py (per creare le tabelle)
2. Esegui PRIMA di etl_live.py (per avere contesto squadre)

Usage:
    python etl_teams_context.py

Dati:
    - Scarica CSV Serie A (I1) da football-data.co.uk
    - Storico ultime 10 stagioni (2016-2026)
    - Salva in tabella team_performance
"""

import requests
import io
import pandas as pd
import os
import urllib.parse
from datetime import datetime
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import TeamPerformance, Team, League

load_dotenv()

# Database connection
db_pass = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
db_port = os.getenv('DB_PORT', '5432')  # Default PostgreSQL port
db_url = f"postgresql://{os.getenv('DB_USER')}:{db_pass}@{os.getenv('DB_HOST')}:{db_port}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)

# ========================================
# STAGIONI DA CARICARE (solo recenti)
# ========================================
SEASONS_TO_LOAD = ['2425', '2526']  # 2024/25 e 2025/26

# ========================================
# CONFIGURAZIONE ELO
# ========================================
ELO_K_FACTOR = 32  # Sensibilità aggiornamento ELO
ELO_INITIAL = 1500  # Rating iniziale
HOME_ADVANTAGE = 100  # Vantaggio casa in punti ELO


def normalize_team_name(name: str) -> str:
    """
    Normalizza i nomi delle squadre da football-data.co.uk 
    ai nostri team_id nel database.
    
    Esempi:
        "Spal" -> "SPAL"
        "Verona" -> "Verona" 
        "AC Milan" -> "AC_Milan"
    """
    # Mapping esplicito per casi speciali
    team_mapping = {
        'Spal': 'SPAL',
        'AC Milan': 'AC_Milan',
        'Chievo': 'Chievo_Verona',
        'Hellas Verona': 'Verona',
        'Verona': 'Verona',
        'Benevento': 'Benevento',
        'Crotone': 'Crotone',
        'Empoli': 'Empoli',
        'Frosinone': 'Frosinone',
        'Genoa': 'Genoa',
        'Salernitana': 'Salernitana',
        'Sampdoria': 'Sampdoria',
        'Sassuolo': 'Sassuolo',
        'Spezia': 'Spezia',
        'Venezia': 'Venezia',
        'Cagliari': 'Cagliari',
        'Lecce': 'Lecce',
        'Monza': 'Monza',
        'Como': 'Como',
        'Parma': 'Parma_Calcio',
        'Parma Calcio': 'Parma_Calcio',
        # Top teams
        'Atalanta': 'Atalanta',
        'Bologna': 'Bologna',
        'Fiorentina': 'Fiorentina',
        'Inter': 'Inter',
        'Juventus': 'Juventus',
        'Lazio': 'Lazio',
        'Milan': 'AC_Milan',
        'Napoli': 'Napoli',
        'Roma': 'Roma',
        'Torino': 'Torino',
        'Udinese': 'Udinese',
    }
    
    # Rimuovi spazi extra
    clean_name = name.strip()
    
    # Cerca nel mapping
    if clean_name in team_mapping:
        return team_mapping[clean_name]
    
    # Fallback: sostituisci spazi con underscore
    return clean_name.replace(' ', '_')


def load_data_automatic():
    """
    Scarica dati storici Serie A da football-data.co.uk.
    Solo le stagioni configurate in SEASONS_TO_LOAD (es. 2024/25, 2025/26).
    """
    print("🌐 DOWNLOAD DATASET STORICO SERIE A")
    print("=" * 50)
    print(f"   📅 Stagioni da caricare: {SEASONS_TO_LOAD}")

    base_url = "https://www.football-data.co.uk/mmz4281/{}/I1.csv"
    
    # Colonne necessarie: Date, Team, Risultati
    cols_needed = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']

    df_list = []

    for season in SEASONS_TO_LOAD:
        url = base_url.format(season)
        try:
            print(f"   📥 Stagione {season}...", end=" ")
            s = requests.get(url, timeout=10).content
            df_temp = pd.read_csv(io.StringIO(s.decode('utf-8', errors='ignore')))

            # Controllo colonne esistenti
            if all(col in df_temp.columns for col in cols_needed):
                df_temp = df_temp[cols_needed]
                df_temp['season'] = season
                df_list.append(df_temp)
                print(f"✓ {len(df_temp)} partite")
            else:
                print("⚠️ Colonne mancanti")

        except Exception as e:
            print(f"❌ Errore: {e}")

    if not df_list:
        raise ValueError("❌ Impossibile scaricare dati. Controlla connessione.")

    # Unione
    df = pd.concat(df_list, axis=0, ignore_index=True)

    # Pulizia Date (formato dd/mm/yy o dd/mm/yyyy)
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')

    # Rimuovi righe incomplete
    df = df.dropna(subset=['Date', 'FTHG', 'FTR'])
    df = df.sort_values('Date').reset_index(drop=True)

    # Rimuovi duplicati
    df = df.drop_duplicates(subset=['Date', 'HomeTeam', 'AwayTeam'], keep='last')

    print("\n✅ DOWNLOAD COMPLETATO")
    print(f"📊 Totale partite: {len(df)}")
    print(f"📅 Periodo: {df['Date'].min().year} - {df['Date'].max().year}")
    print("=" * 50)

    return df


def calculate_elo_probability(elo_home, elo_away):
    """
    Calcola probabilità vittoria basata su differenza ELO.
    Formula standard: 1 / (1 + 10^(diff/400))
    """
    diff = (elo_home + HOME_ADVANTAGE) - elo_away
    return 1 / (1 + 10 ** (-diff / 400))


def update_elo(elo_home, elo_away, actual_result):
    """
    Aggiorna rating ELO dopo una partita.
    
    Args:
        elo_home: ELO casa
        elo_away: ELO trasferta
        actual_result: 1 (home win), 0.5 (draw), 0 (away win)
    
    Returns:
        (new_elo_home, new_elo_away)
    """
    expected_home = calculate_elo_probability(elo_home, elo_away)
    expected_away = 1 - expected_home
    
    # Aggiornamento
    new_elo_home = elo_home + ELO_K_FACTOR * (actual_result - expected_home)
    new_elo_away = elo_away + ELO_K_FACTOR * ((1 - actual_result) - expected_away)
    
    return new_elo_home, new_elo_away


def calculate_rolling_form(team_history, window=5):
    """
    Calcola forma (media ultimi N match).
    
    Args:
        team_history: Lista di dict con 'goals_for', 'goals_against'
        window: Finestra di calcolo (default 5)
    
    Returns:
        (rolling_gf, rolling_ga) medie
    """
    if len(team_history) < window:
        return None, None
    
    recent = team_history[-window:]
    avg_gf = sum(m['goals_for'] for m in recent) / window
    avg_ga = sum(m['goals_against'] for m in recent) / window
    
    return round(avg_gf, 2), round(avg_ga, 2)


def process_matches_and_calculate_metrics(df):
    """
    Processa tutte le partite e calcola:
    - ELO per ogni squadra (evolvendo nel tempo)
    - Rolling Form (ultimi 5 match)
    
    Returns:
        List[dict] con team_performance records
    """
    print("\n🧮 CALCOLO METRICHE SQUADRE")
    print("=" * 50)
    
    # Inizializza ELO e storico
    team_elo = {}  # {team_name: current_elo}
    team_history = {}  # {team_name: [list of matches]}
    
    performance_records = []
    
    for idx, row in df.iterrows():
        home = normalize_team_name(row['HomeTeam'])
        away = normalize_team_name(row['AwayTeam'])
        date = row['Date']
        season = row['season']
        
        home_goals = int(row['FTHG'])
        away_goals = int(row['FTAG'])
        
        # Inizializza ELO se nuova squadra
        if home not in team_elo:
            team_elo[home] = ELO_INITIAL
            team_history[home] = []
        if away not in team_elo:
            team_elo[away] = ELO_INITIAL
            team_history[away] = []
        
        # Risultato (1=home win, 0.5=draw, 0=away win)
        if home_goals > away_goals:
            result = 1.0
        elif home_goals < away_goals:
            result = 0.0
        else:
            result = 0.5
        
        # ELO prima della partita (per salvare stato PRE-match)
        elo_home_before = team_elo[home]
        elo_away_before = team_elo[away]
        
        # Aggiorna ELO
        new_elo_home, new_elo_away = update_elo(elo_home_before, elo_away_before, result)
        team_elo[home] = new_elo_home
        team_elo[away] = new_elo_away
        
        # Aggiungi a storico
        team_history[home].append({
            'date': date,
            'goals_for': home_goals,
            'goals_against': away_goals
        })
        team_history[away].append({
            'date': date,
            'goals_for': away_goals,
            'goals_against': home_goals
        })
        
        # Calcola Rolling Form (ultimi 5)
        rolling_gf_home, rolling_ga_home = calculate_rolling_form(team_history[home])
        rolling_gf_away, rolling_ga_away = calculate_rolling_form(team_history[away])
        
        # Salva record HOME (ELO POST-match)
        performance_records.append({
            'team_id': home,
            'match_date': date.date(),
            'season': season,
            'elo': round(new_elo_home, 2),
            'rolling_xg_form': rolling_gf_home,
            'rolling_ga_form': rolling_ga_home
        })
        
        # Salva record AWAY (ELO POST-match)
        performance_records.append({
            'team_id': away,
            'match_date': date.date(),
            'season': season,
            'elo': round(new_elo_away, 2),
            'rolling_xg_form': rolling_gf_away,
            'rolling_ga_form': rolling_ga_away
        })
        
        # Progress ogni 100 partite
        if (idx + 1) % 100 == 0:
            print(f"   ⚙️ Processate {idx + 1}/{len(df)} partite...")
    
    print(f"\n✅ CALCOLO COMPLETATO")
    print(f"📈 {len(performance_records)} record generati")
    print(f"🏆 {len(team_elo)} squadre tracciate")
    print("=" * 50)
    
    return performance_records


def save_to_database(records):
    """
    Salva i record nella tabella team_performance.
    """
    print("\n💾 SALVATAGGIO NEL DATABASE")
    print("=" * 50)
    
    session = Session()
    
    try:
        # Verifica/crea league
        league_id = 'ITA-Serie A'
        league = session.query(League).filter_by(id=league_id).first()
        if not league:
            print("   🏟️ Creazione league Serie A...")
            session.execute(insert(League), [{'id': league_id, 'name': 'Serie A', 'country': 'Italy'}])
            session.commit()
        
        # Estrai squadre uniche
        unique_teams = set(r['team_id'] for r in records)
        existing_teams = {t.id for t in session.query(Team).all()}
        new_teams = unique_teams - existing_teams
        
        if new_teams:
            print(f"   🆕 Inserimento {len(new_teams)} nuove squadre...")
            team_records = [{'id': t, 'league_id': league_id} for t in new_teams]
            session.execute(insert(Team), team_records)
            session.commit()
        
        # Pulizia: cancella SOLO le stagioni che stiamo per ricaricare
        print(f"   🗑️ Pulizia dati esistenti per stagioni {SEASONS_TO_LOAD}...")
        for season in SEASONS_TO_LOAD:
            deleted = session.query(TeamPerformance).filter_by(season=season).delete()
            print(f"      → Stagione {season}: {deleted} record rimossi")
        session.commit()
        
        # Inserimento bulk
        print(f"   📊 Inserimento {len(records)} record...")
        CHUNK_SIZE = 2000
        for i in range(0, len(records), CHUNK_SIZE):
            chunk = records[i:i + CHUNK_SIZE]
            session.execute(insert(TeamPerformance), chunk)
            session.commit()
            print(f"      → {min(i + CHUNK_SIZE, len(records))}/{len(records)} inseriti")
        
        print("\n✅ SALVATAGGIO COMPLETATO")
        print("=" * 50)
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ ERRORE: {e}")
        raise
    finally:
        session.close()


def main():
    """
    Pipeline ETL completa:
    1. Download dati
    2. Calcolo metriche
    3. Salvataggio DB
    """
    print("\n" + "=" * 50)
    print("🚀 ETL TEAM PERFORMANCE CONTEXT")
    print("=" * 50 + "\n")
    
    try:
        # Step 1: Download
        df = load_data_automatic()
        
        # Step 2: Calcolo
        records = process_matches_and_calculate_metrics(df)
        
        # Step 3: Salvataggio
        save_to_database(records)
        
        print("\n" + "=" * 50)
        print("🎉 ETL COMPLETATO CON SUCCESSO!")
        print("=" * 50 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRORE FATALE: {e}")
        raise


if __name__ == '__main__':
    main()


# ========================================
# USAGE NOTES
# ========================================
"""
ORDINE DI ESECUZIONE:
----------------------
1. python init_db.py          # Crea tabelle (inclusa team_performance)
2. python etl_teams_context.py # Popola contesto squadre (ELO + Forma) [QUESTO SCRIPT]
3. python etl_live.py          # Popola statistiche giocatori

PERCHÉ QUESTO ORDINE?
----------------------
- init_db crea le tabelle
- etl_teams_context crea il contesto storico squadre (necessario per analisi future)
- etl_live usa il database già popolato con squadre

DATI GENERATI:
--------------
- ELO Rating evolutivo per ogni squadra (1200-1800 tipicamente)
- Rolling Form (media gol fatti/subiti ultimi 5 match)
- Storico completo 2016-2026

UTILIZZO FUTURO:
----------------
Questi dati possono essere joinati con player_match_stats per:
- Contestualizzare performance giocatori (giocava contro squadra forte/debole?)
- Previsioni (squadra in forma vs squadra in crisi)
- Fair Value adjustment (giocatore in squadra top vale di più)
"""
