from league_simulator import run_simulation

print('🎲 SIMULAZIONE FINALE: 10,000 iterazioni Monte Carlo\n')
result = run_simulation('2025', n_simulations=10000)

# Top 10 per vittoria
sorted_win = sorted(result.items(), key=lambda x: x[1]['win_league_pct'], reverse=True)
print('\n🏆 PROBABILITÀ VITTORIA CAMPIONATO (Top 10):')
for i, (team, data) in enumerate(sorted_win[:10], 1):
    print(f'{i:2d}. {team:20s}: {data["win_league_pct"]:5.1f}% (avg {data["avg_points"]:5.1f} pts, ELO {int(data["current_elo"])})')

# Top 4
print('\n📊 PROBABILITÀ TOP 4 (qualificazione Champions):')
sorted_top4 = sorted(result.items(), key=lambda x: x[1]['top4_pct'], reverse=True)
for i, (team, data) in enumerate(sorted_top4[:6], 1):
    print(f'{i}. {team:20s}: {data["top4_pct"]:5.1f}%')

# Retrocessione
print('\n⚠️ RISCHIO RETROCESSIONE (Bottom 5):')
sorted_releg = sorted(result.items(), key=lambda x: x[1]['relegation_pct'], reverse=True)
for i, (team, data) in enumerate(sorted_releg[:5], 1):
    print(f'{i}. {team:20s}: {data["relegation_pct"]:5.1f}%')

print('\n✅ League Simulator completato con successo!')
