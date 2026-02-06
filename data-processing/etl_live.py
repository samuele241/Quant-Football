import soccerdata as sd
import pandas as pd
import os
import urllib.parse
from sqlalchemy import create_engine, insert, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import PlayerMatchStat, Team, League

load_dotenv()

db_pass = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
db_port = os.getenv('DB_PORT', '5432')  # Default PostgreSQL port
db_url = f"postgresql://{os.getenv('DB_USER')}:{db_pass}@{os.getenv('DB_HOST')}:{db_port}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)

CHUNK_SIZE = 2000


def _extract_opponent_from_game(game_str: str, team_name: str) -> str:
    """Try to robustly extract the opponent from Understat `game` string.

    Typical `game` values look like: "2024-08-17 Bologna - AC Milan 1:0" or
    sometimes different formats. We'll attempt multiple strategies.
    """
    try:
        # First token is date, remainder contains matchup
        parts = game_str.split(' ', 1)
        if len(parts) == 2:
            raw_match = parts[1]
        else:
            raw_match = game_str

        # Try splitting by ' - ' which is common
        if ' - ' in raw_match:
            sides = raw_match.split(' - ')
            if len(sides) >= 2:
                left = sides[0].strip()
                right = sides[1].strip()
                # right may contain score at the end; remove trailing score
                # remove trailing tokens that look like digits or x:x
                right_name = ' '.join([w for w in right.split() if not any(ch.isdigit() for ch in w) and ':' not in w])
                left_name = ' '.join([w for w in left.split() if not any(ch.isdigit() for ch in w) and ':' not in w])

                # Determine opponent
                if team_name.strip() == left_name or team_name.strip() in left_name:
                    return right_name or right
                if team_name.strip() == right_name or team_name.strip() in right_name:
                    return left_name or left
                # fallback: pick the other side
                return right_name or right

        # Fallback: remove team_name from raw_match
        candidate = raw_match.replace(team_name, '').replace('-', '').strip()
        # remove trailing scores like 1:0 or (1-0)
        candidate = ' '.join([w for w in candidate.split() if ':' not in w and not any(ch.isdigit() for ch in w)])
        if candidate:
            return candidate
    except Exception:
        pass
    return 'Unknown'


def etl_season(season_id: str):
    """Run ETL for a given season id (e.g. '2024'). Downloads player-match stats and writes to DB.

    Inserts `season` into `player_match_stats` and creates League/Teams if missing.
    """
    session = Session()

    # 🧹 PULIZIA: Cancella i dati esistenti per questa stagione per evitare duplicati
    print(f"🧹 Pulizia dati esistenti per stagione {season_id}...")
    deleted_count = session.execute(
        text("DELETE FROM player_match_stats WHERE season = :season"),
        {"season": season_id}
    ).rowcount
    session.commit()
    print(f"   ✓ Rimossi {deleted_count} record esistenti.")

    print(f"📥 Scaricamento dati Serie A stagione {season_id}...")
    scraper = sd.Understat(leagues=['ITA-Serie A'], seasons=season_id)
    stats = scraper.read_player_match_stats().reset_index()
    print(f"✅ Dati scaricati: {len(stats)} righe. Preparazione Bulk Insert...")

    existing_teams = {r[0] for r in session.query(Team.id).all()}
    teams_to_add = set()
    bulk_stats = []

    def calculate_fair_value_quick(goals, assists, xg, minutes):
        """Calcolo veloce del Fair Value in Python - Formula realistica per Serie A."""
        # Base per essere in Serie A
        base_value = 5_000_000
        
        # Moltiplicatori per performance
        goal_value = goals * 2_500_000      # 2.5M per gol
        xg_value = xg * 1_000_000           # 1M per xG (pericolosità)
        assist_value = assists * 1_500_000   # 1.5M per assist
        
        # Totale grezzo
        raw_value = base_value + goal_value + xg_value + assist_value
        
        # Penalty per pochi minuti (ma meno aggressivo)
        if minutes < 300:
            raw_value *= 0.6  # -40% se ha giocato pochissimo
        elif minutes < 900:
            raw_value *= 0.8  # -20% se ha giocato poco
        
        # Cap realistico per Serie A (raramente > 80M)
        return min(raw_value, 80_000_000.0)
    
    for index, row in stats.iterrows():
        try:
            minutes = int(row.get('minutes', 0) or 0)
            if minutes == 0:
                continue

            game_str = row.get('game', '')
            date_str = game_str.split(' ')[0] if isinstance(game_str, str) and ' ' in game_str else row.get('date') or None
            team_name = row.get('team') or ''

            # Extract opponent robustly
            opponent_name = _extract_opponent_from_game(game_str or '', team_name)

            team_id_clean = team_name.replace(' ', '_')

            if team_id_clean not in existing_teams and team_id_clean not in teams_to_add:
                teams_to_add.add(team_id_clean)
            
            # Aggiungi statistiche (fair_value calcolato dopo su totali stagionali)
            goals = int(row.get('goals') or 0)
            assists = int(row.get('assists') or 0)
            xg = float(row.get('xg') or 0.0)

            bulk_stats.append({
                'player_name': row.get('player'),
                'team_id': team_id_clean,
                'match_date': pd.to_datetime(date_str).date() if date_str else None,
                'minutes': minutes,
                'goals': goals,
                'assists': assists,
                'shots': int(row.get('shots') or 0),
                'shots_on_target': int(row.get('shots_on_target') or 0) if 'shots_on_target' in row else 0,
                'opponent': opponent_name,
                'xg': xg,
                'npxg': float(row.get('npxg') or row.get('xg') or 0.0),
                'season': season_id,
                'fair_value': 0.0,  # Placeholder, calcolato dopo
            })

        except Exception as e:
            # Log and continue
            print(f"Warning: skipping row {index} due to parse error: {e}")
            continue

    # Ensure league exists
    league_id = 'ITA-Serie A'
    league = session.query(League).filter_by(id=league_id).first()
    if not league:
        print(f"🛠️ League '{league_id}' non trovata — la creo automaticamente.")
        session.execute(insert(League), [{'id': league_id, 'name': 'Serie A', 'country': 'Italy'}])
        session.commit()

    # Insert teams
    if teams_to_add:
        print(f"🆕 Inserimento di {len(teams_to_add)} nuove squadre...")
        session.execute(insert(Team), [{'id': t, 'league_id': league_id} for t in teams_to_add])
        session.commit()

    # Bulk insert player match stats in chunks
    print(f"🚀 Inserimento veloce di {len(bulk_stats)} prestazioni...")
    for i in range(0, len(bulk_stats), CHUNK_SIZE):
        chunk = bulk_stats[i:i + CHUNK_SIZE]
        session.execute(insert(PlayerMatchStat), chunk)
        session.commit()
        print(f"   ...scritti {min(i + CHUNK_SIZE, len(bulk_stats))} record.")
    
    # CALCOLO FAIR VALUE SUI TOTALI STAGIONALI (non per partita!)
    print(f"💰 Calcolo Fair Value sui totali stagionali per {season_id}...")
    player_totals = session.execute(text("""
        SELECT player_name, 
               SUM(goals) as total_goals,
               SUM(assists) as total_assists,
               SUM(xg) as total_xg,
               SUM(minutes) as total_minutes
        FROM player_match_stats
        WHERE season = :season
        GROUP BY player_name
    """), {"season": season_id}).fetchall()
    
    for player_row in player_totals:
        player_name, tot_goals, tot_assists, tot_xg, tot_mins = player_row
        fair_val = calculate_fair_value_quick(tot_goals or 0, tot_assists or 0, tot_xg or 0.0, tot_mins or 0)
        
        # Aggiorna TUTTE le partite di questo giocatore nella stagione
        session.execute(text("""
            UPDATE player_match_stats
            SET fair_value = :fv
            WHERE player_name = :pname AND season = :season
        """), {"fv": fair_val, "pname": player_name, "season": season_id})
    
    session.commit()
    print(f"   ✓ Fair Value calcolato per {len(player_totals)} giocatori!")

    print(f"🏁 ETL per stagione {season_id} completato. Totale inseriti: {len(bulk_stats)}")


if __name__ == '__main__':
    PAST_SEASON = '2024'
    CURRENT_SEASON = '2025'

    etl_season(PAST_SEASON)
    etl_season(CURRENT_SEASON)
