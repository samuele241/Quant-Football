import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, RobustScaler
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'data-processing', '.env'))

class CalibratedValuation:
    def __init__(self, season='2025'):
        db_password = os.getenv('DB_PASSWORD')
        encoded_password = urllib.parse.quote_plus(db_password)
        self.engine = create_engine(f"postgresql://{os.getenv('DB_USER')}:{encoded_password}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
        self.season = season

    def get_clean_data(self):
        # Leggiamo dalla VISTA e manteniamo le righe match-level per metriche avanzate
        query = text("""
            SELECT
                v.player_id,
                player_name,
                team_id,
                match_date,
                opponent,
                goals,
                assists,
                npxg,
                npxg as xg,
                shots,
                shots_on_target,
                minutes,
                p.birth_date
            FROM v_full_match_stats v
            JOIN players p ON v.player_id = p.player_id
            WHERE season = :s
        """)
        try:
            df = pd.read_sql(query, self.engine, params={"s": self.season})
        except Exception:
            fallback_query = text("""
                SELECT
                    v.player_id,
                    player_name,
                    team_id,
                    match_date,
                    NULL as opponent,
                    goals,
                    assists,
                    npxg,
                    npxg as xg,
                    shots,
                    shots_on_target,
                    minutes,
                    p.birth_date
                FROM v_full_match_stats v
                JOIN players p ON v.player_id = p.player_id
                WHERE season = :s
            """)
            try:
                df = pd.read_sql(fallback_query, self.engine, params={"s": self.season})
            except Exception:
                xa_fallback = text(str(fallback_query).replace("npxg", "xa"))
                df = pd.read_sql(xa_fallback, self.engine, params={"s": self.season})
                df = df.rename(columns={"xa": "npxg"})
                df["xg"] = df["npxg"]
        if "opponent_elo" not in df.columns:
            df["opponent_elo"] = np.nan
        return df

    def sigmoid_reliability(self, minutes, midpoint=900, k=0.005):
        """Funzione Sigmoide: 0.5 a 900 min (~10 partite), 0.9 a 1800+ min"""
        return 1 / (1 + np.exp(-k * (minutes - midpoint)))
    
    def infer_role(self, goals_p90, assists_p90, shots_p90):
        """Inferisce ruolo dal comportamento statistico"""
        if goals_p90 > 0.4 or shots_p90 > 3.0:
            return 'attacker'
        elif assists_p90 > 0.25:
            return 'midfielder'
        else:
            return 'defender'
    
    def calculate_age_factor(self, birth_date):
        if pd.isnull(birth_date):
            return 1.0

        today = pd.Timestamp.now()
        age = (today - pd.to_datetime(birth_date)).days / 365.25

        if age < 22:
            return 1.35
        elif age < 25:
            return 1.20
        elif age < 29:
            return 1.00
        elif age < 32:
            return 0.70
        else:
            return 0.40
    
    def calculate_consistency(self, group_data):
        """Calcola consistenza come inverso della varianza delle prestazioni"""
        if len(group_data) < 3:
            return 0.5  # Neutral per pochi dati
        
        # Performance Score per ogni match
        match_scores = (group_data['npxg'] * 2 + group_data['goals'] * 1.5 + 
                       group_data['assists'] * 1.2) / (group_data['minutes'] / 90)
        
        cv = match_scores.std() / (match_scores.mean() + 0.01)  # Coefficient of variation
        # Più basso è meglio: 1 - normalize
        return max(0.3, 1 - min(cv / 2, 0.7))  # Range 0.3-1.0
    
    def calculate_trend(self, group_data):
        """Trend: confronta ultimi 5 match vs precedenti"""
        if len(group_data) < 6:
            return 1.0  # Neutral
        
        sorted_data = group_data.sort_values('match_date')
        recent = sorted_data.tail(5)
        older = sorted_data.iloc[:-5]
        
        recent_perf = (recent['npxg'].sum() + recent['goals'].sum() * 0.8) / max(recent['minutes'].sum() / 90, 1)
        older_perf = (older['npxg'].sum() + older['goals'].sum() * 0.8) / max(older['minutes'].sum() / 90, 1)
        
        if older_perf < 0.01:
            return 1.0
        
        trend = recent_perf / older_perf
        return np.clip(trend, 0.7, 1.3)  # Max +/-30%
    
    def goal_quality_score(self, group_data):
        """Gol contro squadre forti valgono di più"""
        if group_data['goals'].sum() == 0:
            return 1.0
        
        # Peso gol per ELO avversario
        group_data['opponent_elo'] = group_data['opponent_elo'].fillna(1500)
        weighted_goals = (group_data['goals'] * (group_data['opponent_elo'] / 1500)).sum()
        total_goals = group_data['goals'].sum()
        
        return weighted_goals / total_goals if total_goals > 0 else 1.0

    def calculate_model(self, match_data):
        """Algoritmo Top-Tier: Integra consistenza, trend, goal quality, ruolo"""
        
        # === FASE 1: Aggregazione Player-Level con Metriche Avanzate ===
        player_stats = []
        
        for player_name, group in match_data.groupby('player_name'):
            total_minutes = group['minutes'].sum()
            
            if total_minutes < 90:  # Minimo 1 partita completa
                continue
            
            stats = {
                'player_name': player_name,
                'team_id': group['team_id'].mode()[0] if len(group) > 0 else None,
                'birth_date': group['birth_date'].dropna().iloc[0] if not group['birth_date'].dropna().empty else None,
                'minutes': total_minutes,
                'goals': group['goals'].sum(),
                'assists': group['assists'].sum(),
                'npxg': group['npxg'].sum(),
                'xg': group['xg'].sum(),
                'shots': group['shots'].sum(),
                'sot': group['shots_on_target'].sum(),
                'matches_played': len(group),
                
                # Metriche Avanzate
                'consistency': self.calculate_consistency(group),
                'trend': self.calculate_trend(group),
                'goal_quality': self.goal_quality_score(group),
                'avg_opponent_elo': group['opponent_elo'].fillna(1500).mean()
            }
            
            player_stats.append(stats)
        
        df = pd.DataFrame(player_stats)
        
        # === FASE 2: Metriche Per 90 Minuti ===
        metrics = ['goals', 'assists', 'npxg', 'xg', 'shots', 'sot']
        for m in metrics:
            df[f'{m}_p90'] = (df[m] / df['minutes']) * 90
        
        # === FASE 3: Inferenza Ruolo ===
        df['role'] = df.apply(lambda x: self.infer_role(x['goals_p90'], x['assists_p90'], x['shots_p90']), axis=1)
        
        # === FASE 4: Pesi Dinamici per Ruolo ===
        def get_weights(role):
            if role == 'attacker':
                return {'npxg_p90': 0.45, 'goals_p90': 0.25, 'assists_p90': 0.15, 'sot_p90': 0.15}
            elif role == 'midfielder':
                return {'npxg_p90': 0.30, 'goals_p90': 0.15, 'assists_p90': 0.40, 'sot_p90': 0.15}
            else:  # defender/altro
                return {'npxg_p90': 0.25, 'goals_p90': 0.20, 'assists_p90': 0.30, 'sot_p90': 0.25}
        
        # === FASE 5: Normalizzazione Robusta (Resiste a outlier) ===
        scaler = RobustScaler()  # Usa mediana e IQR invece di media e std
        cols_p90 = ['npxg_p90', 'goals_p90', 'assists_p90', 'sot_p90']
        
        # Winsorization (cap al 99° percentile)
        for col in cols_p90:
            cap = df[col].quantile(0.99)
            df[col] = df[col].clip(upper=cap)
        
        df[cols_p90] = scaler.fit_transform(df[cols_p90])
        
        # Min-Max per portare a 0-1
        min_max = MinMaxScaler()
        df[cols_p90] = min_max.fit_transform(df[cols_p90])
        
        # === FASE 6: Performance Score Pesato per Ruolo ===
        df['performance_score'] = df.apply(lambda row: (
            row['npxg_p90'] * get_weights(row['role'])['npxg_p90'] +
            row['goals_p90'] * get_weights(row['role'])['goals_p90'] +
            row['assists_p90'] * get_weights(row['role'])['assists_p90'] +
            row['sot_p90'] * get_weights(row['role'])['sot_p90']
        ) * 100, axis=1)
        
        # === FASE 7: Fattori Moltiplicativi ===
        df['reliability'] = df['minutes'].apply(self.sigmoid_reliability)
        df['age_multiplier'] = df['birth_date'].apply(self.calculate_age_factor)
        
        # Bonus/Malus Calendario (ELO medio avversari)
        df['schedule_difficulty'] = (df['avg_opponent_elo'] - 1500) / 1500  # Normalized
        df['schedule_bonus'] = 1 + (df['schedule_difficulty'] * 0.15).clip(-0.1, 0.15)
        
        # === FASE 8: FORMULA FINALE MULTI-FATTORIALE ===
        # Formula: Base + (Score^exp * Reliability * Trend * Consistency * GoalQuality * Schedule * Age * Multiplier)
        
        base_value = 800_000  # Minimo Serie A
        market_multiplier = 120_000
        exponent = 1.65  # Curva esponenziale per premiare top player
        
        df['fair_value'] = base_value + (
            (df['performance_score'] ** exponent) *
            df['reliability'] *
            df['trend'] *
            df['consistency'] *
            df['goal_quality'] *
            df['schedule_bonus'] *
            df['age_multiplier'] *
            market_multiplier
        )
        
        # === FASE 9: Calibrazione Finale ===
        # Arrotondamento a multipli di 500k per realismo
        df['fair_value'] = (df['fair_value'] / 500_000).round() * 500_000
        df['fair_value'] = df['fair_value'].clip(lower=500_000, upper=200_000_000)
        
        return df.sort_values(by='fair_value', ascending=False)

    def save_to_db(self, df):
        print(f"💾 Salvataggio valori su schema V2...")
        with self.engine.begin() as conn:
            # Qui dobbiamo fare un update un po' più complesso perché dobbiamo risalire all'ID
            # Ma dato che il fair_value è stagionale, possiamo aggiornare tutte le righe di quel giocatore in quella stagione
            # oppure (meglio) salvare il fair_value nell'anagrafica o in una tabella di cache.
            # Per ora, aggiorniamo le stats delle partite recenti.
            
            for _, row in df.iterrows():
                conn.execute(
                    text("""
                        UPDATE player_stats_v2 s
                        SET fair_value = :v
                        FROM players p, matches m
                        WHERE s.player_id = p.player_id 
                          AND s.match_id = m.match_id
                          AND p.name = :n 
                          AND m.season = :s
                    """),
                    {"v": row['fair_value'], "n": row['player_name'], "s": self.season}
                )

if __name__ == "__main__":
    model = CalibratedValuation(season='2025') 
    
    print("🚀 Avvio algoritmo valutazione TOP-TIER...\n")
    
    data = model.get_clean_data()
    if not data.empty:
        print(f"📊 Dati caricati: {len(data)} partite analizzate\n")
        
        results = model.calculate_model(data)
        
        print("\n" + "="*70)
        print("🏆 TOP 15 GIOCATORI SERIE A (Valutazione Algoritmica Avanzata)")
        print("="*70)
        
        preview = results[['player_name', 'role', 'minutes', 'matches_played', 
                          'consistency', 'trend', 'goal_quality', 'fair_value']].head(15).copy()
        preview['value_mln'] = (preview['fair_value'] / 1_000_000).round(1)
        preview['consistency'] = (preview['consistency'] * 100).round(0)
        preview['trend'] = (preview['trend'] * 100).round(0)
        preview['goal_quality'] = (preview['goal_quality'] * 100).round(0)
        
        print(preview[['player_name', 'role', 'minutes', 'consistency', 'trend', 'value_mln']].to_string(index=False))
        
        print("\n" + "="*70)
        print("📈 STATISTICHE MODELLO")
        print("="*70)
        print(f"Valore Medio: €{results['fair_value'].mean()/1e6:.1f}M")
        print(f"Valore Mediano: €{results['fair_value'].median()/1e6:.1f}M")
        print(f"Range: €{results['fair_value'].min()/1e6:.1f}M - €{results['fair_value'].max()/1e6:.1f}M")
        print(f"\nGiocatori valutati: {len(results)}")
        print(f"Attaccanti: {(results['role'] == 'attacker').sum()}")
        print(f"Centrocampisti: {(results['role'] == 'midfielder').sum()}")
        print(f"Difensori/Altri: {(results['role'] == 'defender').sum()}")
        
        # Salvataggio
        print("\n💾 Salvataggio valori nel database...")
        model.save_to_db(results)
        print("✅ Completato!")
    else:
        print("❌ Nessun dato trovato per la stagione selezionata")