from db_connect import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Statistiche generali
    stats = conn.execute(text("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT team_id) as total_teams,
            MIN(elo) as min_elo,
            MAX(elo) as max_elo,
            AVG(elo) as avg_elo
        FROM team_performance
    """)).fetchone()
    
    print("\n📊 TEAM PERFORMANCE DATABASE")
    print("=" * 50)
    print(f"Total Records: {stats[0]:,}")
    print(f"Total Teams: {stats[1]}")
    print(f"ELO Range: {stats[2]:.0f} - {stats[3]:.0f}")
    print(f"ELO Average: {stats[4]:.0f}")
    print("=" * 50)
    
    # Top 5 per ELO attuale
    top_teams = conn.execute(text("""
        SELECT DISTINCT ON (team_id) 
            team_id, 
            elo, 
            rolling_xg_form, 
            rolling_ga_form
        FROM team_performance
        WHERE season = '2526'
        ORDER BY team_id, match_date DESC
    """)).fetchall()
    
    sorted_teams = sorted(top_teams, key=lambda x: x[1], reverse=True)[:10]
    
    print("\n🏆 TOP 10 TEAMS BY ELO (Season 2025/26)")
    print("=" * 50)
    for i, row in enumerate(sorted_teams, 1):
        gf = row[2] or 0
        ga = row[3] or 0
        print(f"{i:2}. {row[0]:<20} ELO: {row[1]:>6.0f}  Form: {gf:.1f}G / {ga:.1f}GA")
    print("=" * 50)
