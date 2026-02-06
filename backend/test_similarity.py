#!/usr/bin/env python3
"""Script di test per l'endpoint similarity."""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("TEST SIMILARITY SEARCH - Football Quant Engine")
print("=" * 60)

# 1. Test: Giocatori disponibili
print("\n[1] Recupero giocatori disponibili...")
try:
    resp = requests.get(f"{BASE_URL}/analytics/scouting/available-players?limit=10")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✓ Trovati {data['total_players']} giocatori")
        print("\nPrimi 5 giocatori:")
        for i, p in enumerate(data['players'][:5], 1):
            print(f"  {i}. {p['name']} ({p['team']}) - {p['goals']} gol")
        
        # Usa il primo giocatore per il test
        if data['players']:
            test_player = data['players'][0]['name']
            print(f"\n[2] Test similarity search per: {test_player}")
            
            resp2 = requests.get(f"{BASE_URL}/analytics/scouting/similar/{test_player}")
            if resp2.status_code == 200:
                result = resp2.json()
                print(f"\n✓ Algoritmo usato: {result.get('algorithm', 'N/A')}")
                print(f"✓ Match trovati: {len(result.get('matches', []))}")
                
                if result.get('matches'):
                    print("\nTop 5 giocatori simili:")
                    for i, m in enumerate(result['matches'][:5], 1):
                        print(f"  {i}. {m['player']} ({m['team']}) - Similarity: {m['similarity']}%")
                        print(f"      Goals/90: {m['data']['goals_p90']}, xG/90: {m['data']['xg_p90']}")
                else:
                    print("\n⚠ Nessun match trovato!")
            else:
                print(f"\n✗ Errore API: {resp2.status_code}")
                print(resp2.text)
    else:
        print(f"✗ Errore: {resp.status_code}")
except requests.exceptions.ConnectionError:
    print("✗ ERRORE: Server non raggiungibile. Assicurati che uvicorn sia in esecuzione.")
except Exception as e:
    print(f"✗ Errore: {e}")

print("\n" + "=" * 60)
