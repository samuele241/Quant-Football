#!/usr/bin/env python3
"""
Script di migrazione per aggiungere la colonna 'fair_value' e popolarla.
Eseguire questo PRIMA di rigenerare i dati con ETL.
"""
import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_pass = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
db_url = f"postgresql://{os.getenv('DB_USER')}:{db_pass}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(db_url)

def calculate_fair_value_quick(goals, assists, xg, minutes):
    """Calcolo veloce del Fair Value in Python."""
    base = 1.0
    goals_val = goals * 2.0
    xg_val = xg * 1.0
    assists_val = assists * 1.2
    
    minutes_mult = 1.0
    if minutes < 500:
        minutes_mult = 0.5
    elif minutes < 1000:
        minutes_mult = 0.75
    
    raw = base + goals_val + xg_val + assists_val
    adjusted = raw * minutes_mult
    return min(adjusted, 100.0)

print("=" * 60)
print("MIGRAZIONE: Aggiunta colonna 'fair_value'")
print("=" * 60)

with engine.connect() as conn:
    # Step 1: Verifica se la colonna esiste già
    check_column = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='player_match_stats' AND column_name='fair_value'
    """)
    
    result = conn.execute(check_column).fetchone()
    
    if result:
        print("\n✓ La colonna 'fair_value' esiste già.")
        print("  Procedo a ricalcolare i valori per tutti i record esistenti...\n")
    else:
        print("\n[1] Aggiunta colonna 'fair_value' alla tabella...")
        add_column = text("""
            ALTER TABLE player_match_stats 
            ADD COLUMN fair_value FLOAT DEFAULT 0.0
        """)
        conn.execute(add_column)
        conn.commit()
        print("✓ Colonna aggiunta con successo!\n")
    
    # Step 2: Calcola e aggiorna i valori per tutti i record
    print("[2] Calcolo Fair Value per tutti i giocatori...")
    
    # Recupera tutti i record
    fetch_query = text("""
        SELECT id, goals, assists, xg, minutes 
        FROM player_match_stats
    """)
    
    rows = conn.execute(fetch_query).fetchall()
    print(f"  → Trovati {len(rows)} record da aggiornare")
    
    # Aggiorna in batch
    updates = []
    for row in rows:
        record_id = row[0]
        goals = row[1] or 0
        assists = row[2] or 0
        xg = row[3] or 0.0
        minutes = row[4] or 0
        
        fair_val = calculate_fair_value_quick(goals, assists, xg, minutes)
        updates.append({"id": record_id, "fair_value": fair_val})
    
    if updates:
        update_query = text("""
            UPDATE player_match_stats 
            SET fair_value = :fair_value 
            WHERE id = :id
        """)
        
        # Aggiorna in chunk per performance
        chunk_size = 1000
        for i in range(0, len(updates), chunk_size):
            chunk = updates[i:i+chunk_size]
            conn.execute(update_query, chunk)
            print(f"  → Aggiornati {min(i+chunk_size, len(updates))}/{len(updates)} record...")
        
        conn.commit()
        print(f"\n✓ Tutti i {len(updates)} record sono stati aggiornati!\n")
    
    # Step 3: Verifica
    print("[3] Verifica dei dati...")
    verify_query = text("""
        SELECT player_name, 
               SUM(goals) as total_goals,
               SUM(assists) as total_assists,
               AVG(fair_value) as avg_fair_value
        FROM player_match_stats
        WHERE fair_value > 0
        GROUP BY player_name
        ORDER BY avg_fair_value DESC
        LIMIT 10
    """)
    
    top_players = conn.execute(verify_query).fetchall()
    
    print("\nTop 10 giocatori per Fair Value stimato:")
    print("-" * 60)
    for i, p in enumerate(top_players, 1):
        print(f"  {i}. {p[0]:<30} €{p[3]:.1f}M  ({p[1]} gol, {p[2]} assist)")
    
print("\n" + "=" * 60)
print("✅ MIGRAZIONE COMPLETATA CON SUCCESSO!")
print("=" * 60)
print("\nProssimi passi:")
print("  1. Ricompila il modulo C++ se vuoi usare la funzione C++")
print("     cd backend && python setup.py build_ext --inplace")
print("  2. Il backend userà automaticamente i valori fair_value dal DB")
print("  3. Per nuovi dati, l'ETL calcolerà automaticamente il fair_value")
print()
