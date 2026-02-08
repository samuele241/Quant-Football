"""
League Simulator - Monte Carlo Forecast
========================================
Simula il resto della stagione Serie A usando Rating ELO e Monte Carlo (10k iterazioni).
Restituisce probabilità di: Vittoria, Top 4, Retrocessione per ogni squadra.
"""

import os
import random
from datetime import datetime, date
from collections import defaultdict
from typing import List, Dict, Tuple
import urllib.parse

import soccerdata as sd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carica .env dalla directory data-processing (come fa main.py)
load_dotenv("../data-processing/.env")

# Database connection - Pulisci variabili d'ambiente
db_user = os.getenv('DB_USER', '').strip()
db_password = os.getenv('DB_PASSWORD', '').strip()
db_host = os.getenv('DB_HOST', '').strip()
db_port = os.getenv('DB_PORT', '').strip() or '5432'
db_name = os.getenv('DB_NAME', '').strip()

db_pass = urllib.parse.quote_plus(db_password)
db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)

# Costanti simulazione
HOME_ADVANTAGE = 100  # Bonus ELO per squadra di casa
DRAW_FACTOR = 0.25     # Fattore che aumenta prob pareggio


def normalize_team_name(name: str) -> str:
    """
    Normalizza i nomi squadre da Understat al formato DB.
    """
    if not name:
        return 'Unknown'
    
    mapping = {
        'Atalanta': 'Atalanta',
        'Bologna': 'Bologna',
        'Cagliari': 'Cagliari',
        'Empoli': 'Empoli',
        'Fiorentina': 'Fiorentina',
        'Genoa': 'Genoa',
        'Hellas Verona': 'Verona',
        'Inter': 'Inter',
        'Juventus': 'Juventus',
        'Lazio': 'Lazio',
        'Lecce': 'Lecce',
        'AC Milan': 'AC_Milan',
        'Milan': 'AC_Milan',
        'Napoli': 'Napoli',
        'Parma': 'Parma_Calcio',
        'Parma Calcio 1913': 'Parma_Calcio',
        'Roma': 'Roma',
        'Torino': 'Torino',
        'Udinese': 'Udinese',
        'Venezia': 'Venezia',
        'Monza': 'Monza',
        'Como': 'Como',
    }
    return mapping.get(name, name.replace(' ', '_'))


def get_remaining_fixtures(season: str = '2025') -> List[Dict]:
    """
    Scarica il calendario Serie A e filtra solo le partite NON ancora giocate.
    
    Returns:
        List di dict con: {'home': str, 'away': str, 'date': date}
    """
    print(f"📅 Recupero fixture rimanenti per stagione {season}...")
    
    try:
        # Download calendario completo da Understat
        scraper = sd.Understat(leagues=['ITA-Serie A'], seasons=season)
        fixtures_df = scraper.read_schedule().reset_index()
        
        print(f"   ✓ Scaricate {len(fixtures_df)} partite totali")
        print(f"   ℹ️ Colonne disponibili: {list(fixtures_df.columns)}")
        
        # Filtra solo partite future (data >= oggi)
        today = date.today()
        remaining = []
        
        for idx, row in fixtures_df.iterrows():
            try:
                match_date = row.get('date')
                if isinstance(match_date, str):
                    match_date = datetime.strptime(match_date.split()[0], '%Y-%m-%d').date()
                elif hasattr(match_date, 'date'):
                    match_date = match_date.date()
                
                # Se la partita non è ancora stata giocata
                if match_date >= today:
                    # Prova diversi nomi colonne
                    home_team = row.get('home') or row.get('home_team') or row.get('HomeTeam')
                    away_team = row.get('away') or row.get('away_team') or row.get('AwayTeam')
                    
                    if home_team and away_team:
                        home_team = normalize_team_name(str(home_team))
                        away_team = normalize_team_name(str(away_team))
                        
                        remaining.append({
                            'home': home_team,
                            'away': away_team,
                            'date': match_date
                        })
            except Exception as e:
                print(f"   ⚠️ Errore riga {idx}: {e}")
                continue
        
        print(f"   ✓ Partite rimanenti: {len(remaining)}")
        if remaining:
            print(f"   📊 Esempio prima partita: {remaining[0]['home']} vs {remaining[0]['away']} il {remaining[0]['date']}")
        
        return remaining
    
    except Exception as e:
        print(f"   ❌ Errore nel recupero fixture: {e}")
        # Fallback: restituisci lista vuota (simulazione solo su classifica attuale)
        return []


def get_current_standings(season: str = '2025') -> Dict[str, Dict]:
    """
    Calcola la classifica ATTUALE reale dai dati database.
    
    Returns:
        Dict: {team_id: {'points': int, 'gf': int, 'ga': int, 'gd': int, 'played': int}}
    """
    print(f"📊 Calcolo classifica attuale per stagione {season}...")
    
    session = Session()
    
    # Query semplificata: calcola direttamente vittorie/pareggi/sconfitte
    # invece di usare subquery complessa per opponent_goals
    query = text("""
        WITH team_matches AS (
            -- Per ogni partita, prendi i gol della squadra
            SELECT 
                team_id,
                match_date,
                opponent,
                SUM(goals) as team_goals
            FROM v_full_match_stats
            WHERE season = :season AND minutes > 0
            GROUP BY team_id, match_date, opponent
        ),
        match_results AS (
            -- Unisci ogni partita con quella dell'avversario per avere entrambi i punteggi
            -- Usa LIKE per gestire casi come "Parma Calcio" → "Parma_Calcio_1913"
            SELECT 
                tm.team_id,
                tm.match_date,
                tm.opponent,
                tm.team_goals,
                opp.team_goals as opponent_goals
            FROM team_matches tm
            LEFT JOIN team_matches opp 
                ON (
                    REPLACE(tm.opponent, ' ', '_') = opp.team_id 
                    OR opp.team_id LIKE REPLACE(tm.opponent, ' ', '_') || '%'
                )
                AND (
                    tm.team_id = REPLACE(opp.opponent, ' ', '_')
                    OR tm.team_id LIKE REPLACE(opp.opponent, ' ', '_') || '%'
                )
                AND tm.match_date = opp.match_date
        )
        SELECT 
            team_id,
            COUNT(*) as played,
            SUM(CASE 
                WHEN team_goals > opponent_goals THEN 3
                WHEN team_goals = opponent_goals THEN 1
                ELSE 0
            END) as points,
            SUM(team_goals) as gf,
            COALESCE(SUM(opponent_goals), 0) as ga
        FROM match_results
        WHERE opponent_goals IS NOT NULL
        GROUP BY team_id
        ORDER BY points DESC, (SUM(team_goals) - COALESCE(SUM(opponent_goals), 0)) DESC
    """)
    
    standings = {}
    rows = session.execute(query, {'season': season}).fetchall()
    
    for row in rows:
        raw_team_id = row[0]
        # Normalize: rimuovi suffissi anno (es. "_1913") per match con team_performance
        team_id = raw_team_id.replace('_1913', '').replace('_1899', '').replace('_1907', '')
        
        standings[team_id] = {
            'played': int(row[1]),
            'points': int(row[2]),
            'gf': int(row[3]),
            'ga': int(row[4]),
            'gd': int(row[3]) - int(row[4])
        }
    
    session.close()
    
    print(f"   ✓ Classifica calcolata per {len(standings)} squadre")
    # Mostra top 3
    sorted_teams = sorted(standings.items(), key=lambda x: (x[1]['points'], x[1]['gd']), reverse=True)
    for i, (team, stats) in enumerate(sorted_teams[:3], 1):
        print(f"      {i}. {team}: {stats['points']} pts (GD: {stats['gd']:+d})")
    
    # Fix: Aggiungi squadre con ELO ma senza standings (con valori di default)
    # Questo succede quando la squadra non ha ancora partite con opponent_goals validi
    team_elos_available = get_team_elos(season)
    missing_teams = set(team_elos_available.keys()) - set(standings.keys())
    if missing_teams:
        print(f"   ⚠️ {len(missing_teams)} squadre con ELO ma senza classifica (aggiunte con 0 punti)")
        for team in missing_teams:
            standings[team] = {
                'played': 0,
                'points': 0,
                'gf': 0,
                'ga': 0,
                'gd': 0
            }
            print(f"      → {team} (ELO: {team_elos_available[team]:.0f})")
    
    return standings


def get_team_elos(season: str = '2025') -> Dict[str, float]:
    """
    Recupera gli ELO rating attuali (più recenti) per tutte le squadre.
    
    Returns:
        Dict: {team_id: elo_rating}
    """
    print(f"⚡ Recupero ELO rating per stagione {season}...")
    
    session = Session()
    
    # Mappa season
    team_season_map = {
        '2024': '2425',
        '2025': '2526'
    }
    team_season = team_season_map.get(season, season)
    
    query = text("""
        SELECT DISTINCT ON (team_id)
            team_id,
            elo
        FROM team_performance
        WHERE season = :season
        ORDER BY team_id, match_date DESC
    """)
    
    elos = {}
    rows = session.execute(query, {'season': team_season}).fetchall()
    
    for row in rows:
        elos[row[0]] = float(row[1])
    
    session.close()
    
    print(f"   ✓ ELO caricati per {len(elos)} squadre")
    # Mostra top 3 ELO
    sorted_elos = sorted(elos.items(), key=lambda x: x[1], reverse=True)
    for i, (team, elo) in enumerate(sorted_elos[:3], 1):
        print(f"      {i}. {team}: {elo:.0f} ELO")
    
    return elos


def simulate_match(home_elo: float, away_elo: float) -> str:
    """
    Simula una partita usando probabilità ELO.
    
    Args:
        home_elo: Rating ELO squadra casa
        away_elo: Rating ELO squadra trasferta
    
    Returns:
        'H' (vittoria casa), 'D' (pareggio), 'A' (vittoria trasferta)
    """
    # Home advantage: +100 ELO virtuale
    adjusted_home_elo = home_elo + HOME_ADVANTAGE
    
    # Formula ELO: P(home wins) = 1 / (1 + 10^((away - home)/400))
    expected_home = 1.0 / (1.0 + 10 ** ((away_elo - adjusted_home_elo) / 400))
    expected_away = 1.0 - expected_home
    
    # Aggiungi probabilità pareggio (sottratta proporzionalmente)
    prob_draw = DRAW_FACTOR * min(expected_home, expected_away)
    prob_home = expected_home * (1 - prob_draw)
    prob_away = expected_away * (1 - prob_draw)
    
    # Normalizza (dovrebbe già essere ~1, ma per sicurezza)
    total = prob_home + prob_draw + prob_away
    prob_home /= total
    prob_draw /= total
    prob_away /= total
    
    # Simula esito
    result = random.choices(
        ['H', 'D', 'A'],
        weights=[prob_home, prob_draw, prob_away],
        k=1
    )[0]
    
    return result


def run_simulation(season: str = '2025', n_simulations: int = 10000) -> Dict:
    """
    Esegue simulazione Monte Carlo del resto della stagione.
    
    Args:
        season: Stagione da simulare (es. '2025')
        n_simulations: Numero di iterazioni (default: 10000)
    
    Returns:
        Dict con probabilità per ogni squadra:
        {
            'Inter': {
                'win_league': 0.73,
                'top4': 0.98,
                'relegation': 0.0,
                'avg_points': 89.3,
                'avg_position': 1.2
            },
            ...
        }
    """
    print(f"\n🎲 AVVIO SIMULAZIONE MONTE CARLO")
    print(f"=" * 60)
    print(f"   Stagione: {season}")
    print(f"   Iterazioni: {n_simulations:,}")
    print(f"=" * 60)
    
    # 1. Carica dati
    current_standings = get_current_standings(season)
    team_elos = get_team_elos(season)
    remaining_fixtures = get_remaining_fixtures(season)
    
    if not remaining_fixtures:
        print("⚠️ Nessuna partita rimanente - restituisco classifica attuale come forecast")
        # TODO: gestire caso fine stagione
    
    # 2. Prepara strutture per tracking risultati
    teams = list(current_standings.keys())
    results = {
        team: {
            'win_count': 0,
            'top4_count': 0,
            'relegation_count': 0,
            'total_points': 0,
            'total_position': 0
        }
        for team in teams
    }
    
    # 3. Esegui simulazioni
    print(f"\n⚙️ Simulazione in corso...")
    skipped_fixtures = set()
    
    for sim in range(n_simulations):
        if (sim + 1) % 2000 == 0:
            print(f"   → Completate {sim + 1:,}/{n_simulations:,} simulazioni...")
        
        # Copia classifica attuale
        sim_standings = {
            team: {
                'points': stats['points'],
                'gf': stats['gf'],
                'ga': stats['ga'],
                'gd': stats['gd']
            }
            for team, stats in current_standings.items()
        }
        
        # Simula tutte le partite rimanenti
        for fixture in remaining_fixtures:
            home = fixture['home']
            away = fixture['away']
            
            # Skip se squadra non ha ELO (es. promossa non tracciata)
            if home not in team_elos or away not in team_elos:
                if sim == 0:  # Log solo prima iterazione
                    skipped_fixtures.add(f"{home} vs {away} (missing ELO)")
                continue
            
            # Skip se squadra non nella classifica (mismatch nomi)
            if home not in sim_standings or away not in sim_standings:
                if sim == 0:  # Log solo prima iterazione
                    skipped_fixtures.add(f"{home} vs {away} (not in standings)")
                continue
            
            result = simulate_match(team_elos[home], team_elos[away])
            
            # Aggiorna punti (gol stimati con media gaussiana)
            if result == 'H':
                sim_standings[home]['points'] += 3
                sim_standings[home]['gf'] += 2
                sim_standings[away]['ga'] += 2
                sim_standings[away]['gf'] += 1
                sim_standings[home]['ga'] += 1
            elif result == 'A':
                sim_standings[away]['points'] += 3
                sim_standings[away]['gf'] += 2
                sim_standings[home]['ga'] += 2
                sim_standings[home]['gf'] += 1
                sim_standings[away]['ga'] += 1
            else:  # Draw
                sim_standings[home]['points'] += 1
                sim_standings[away]['points'] += 1
                sim_standings[home]['gf'] += 1
                sim_standings[away]['gf'] += 1
                sim_standings[home]['ga'] += 1
                sim_standings[away]['ga'] += 1
            
            # Aggiorna GD
            sim_standings[home]['gd'] = sim_standings[home]['gf'] - sim_standings[home]['ga']
            sim_standings[away]['gd'] = sim_standings[away]['gf'] - sim_standings[away]['ga']
        
        # Ordina classifica finale
        final_table = sorted(
            sim_standings.items(),
            key=lambda x: (x[1]['points'], x[1]['gd'], x[1]['gf']),
            reverse=True
        )
        
        # Registra risultati
        for position, (team, stats) in enumerate(final_table, 1):
            if position == 1:
                results[team]['win_count'] += 1
            if position <= 4:
                results[team]['top4_count'] += 1
            if position >= 18:  # Ultime 3 = retrocessione
                results[team]['relegation_count'] += 1
            
            results[team]['total_points'] += stats['points']
            results[team]['total_position'] += position
    
    # 4. Calcola probabilità finali
    print(f"\n✅ SIMULAZIONE COMPLETATA")
    print(f"=" * 60)
    
    if skipped_fixtures:
        print(f"\n⚠️ {len(skipped_fixtures)} partite saltate (squadre non tracciate):")
        for skip in list(skipped_fixtures)[:5]:
            print(f"   - {skip}")
    
    forecast = {}
    for team in teams:
        forecast[team] = {
            'win_league_pct': round((results[team]['win_count'] / n_simulations) * 100, 2),
            'top4_pct': round((results[team]['top4_count'] / n_simulations) * 100, 2),
            'relegation_pct': round((results[team]['relegation_count'] / n_simulations) * 100, 2),
            'avg_points': round(results[team]['total_points'] / n_simulations, 1),
            'avg_position': round(results[team]['total_position'] / n_simulations, 1),
            'current_points': current_standings[team]['points'],
            'current_elo': round(team_elos.get(team, 1500), 0)
        }
    
    # Mostra top 5 candidati vittoria
    sorted_forecast = sorted(forecast.items(), key=lambda x: x[1]['win_league_pct'], reverse=True)
    print("\n🏆 TOP 5 CANDIDATI VITTORIA:")
    for i, (team, data) in enumerate(sorted_forecast[:5], 1):
        print(f"   {i}. {team}: {data['win_league_pct']:.1f}% - Avg {data['avg_points']:.1f} pts")
    
    return forecast


# Test locale
if __name__ == '__main__':
    # Test 1: Recupera fixture rimanenti
    fixtures = get_remaining_fixtures('2025')
    print(f"\n📋 FIXTURE RIMANENTI: {len(fixtures)}")
    
    # Test 2: Classifica attuale
    standings = get_current_standings('2025')
    
    # Test 3: ELO attuali
    elos = get_team_elos('2025')
    
    # Test 4: Simulazione veloce (100 iter per test)
    # forecast = run_simulation('2025', n_simulations=100)
