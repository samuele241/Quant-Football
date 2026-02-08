import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'data-processing', '.env'))

class AnalyticsEngine:
    def __init__(self):
        db_password = os.getenv('DB_PASSWORD')
        encoded_password = urllib.parse.quote_plus(db_password)
        self.engine = create_engine(f"postgresql://{os.getenv('DB_USER')}:{encoded_password}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
        self.scaler = StandardScaler()
        
    def fetch_data(self):
        query = """
        SELECT 
            player_name,
            SUM(goals) as goals,
            SUM(assists) as assists,
            SUM(npxg) as xg,
            SUM(shots) as shots,
            SUM(minutes) as minutes
        FROM v_full_match_stats
        GROUP BY player_name
        HAVING SUM(minutes) >= 450;
        """
        try:
            return pd.read_sql(text(query), self.engine)
        except Exception:
            fallback_query = query.replace("npxg", "xa")
            return pd.read_sql(text(fallback_query), self.engine)

    def process_metrics(self, df):
        # Calcolo metriche per 90 minuti
        metrics = ['goals', 'assists', 'xg', 'shots']
        for m in metrics:
            df[f'{m}_p90'] = (df[m] / df['minutes']) * 90
        
        # Normalizzazione Z-score
        features_p90 = [f'{m}_p90' for m in metrics]
        df[features_p90] = self.scaler.fit_transform(df[features_p90])
        return df, features_p90

    def calculate_theoretical_value(self, df, features):
        # Pesi delle metriche (possono essere dinamici per ruolo)
        weights = np.array([1.5, 1.2, 1.3, 0.8]) 
        
        # Calcolo punteggio di performance aggregato
        df['performance_score'] = df[features].dot(weights)
        
        # Mappatura su scala monetaria (Heuristic Model)
        # Base 5M, incremento basato sul punteggio deviazione standard
        base_val = 10_000_000
        multiplier = 7_500_000
        df['theoretical_value'] = base_val + (df['performance_score'] * multiplier)
        
        # Floor a 1M per evitare valori negativi o ridicoli
        df['theoretical_value'] = df['theoretical_value'].clip(lower=1_000_000)
        return df

    def find_similar_players(self, target_name, df, features, top_n=5):
        if target_name not in df['player_name'].values:
            return None
        
        target_vec = df[df['player_name'] == target_name][features].values
        
        # Calcolo Distanza Euclidea Pesata
        # Weights: dare più importanza a xG e xA per definire lo stile di gioco
        feature_weights = np.array([1.0, 1.0, 1.5, 0.7])
        
        diff = df[features].values - target_vec
        weighted_diff = diff * feature_weights
        distances = np.linalg.norm(weighted_diff, axis=1)
        
        df['distance'] = distances
        return df[df['player_name'] != target_name].sort_values('distance').head(top_n)

# Execution logic
if __name__ == "__main__":
    engine = AnalyticsEngine()
    data = engine.fetch_data()
    data, feat_cols = engine.process_metrics(data)
    data = engine.calculate_theoretical_value(data, feat_cols)
    
    # Esempio: Similitudine per Vlahovic
    similar = engine.find_similar_players("Dusan Vlahovic", data, feat_cols)
    print(data[['player_name', 'theoretical_value']].sort_values('theoretical_value', ascending=False).head(10))
    print("\nGiocatori simili a Vlahovic:")
    print(similar[['player_name', 'distance']])
    
    # Salvataggio per analisi ML successiva
    data.to_csv("player_analytics_refined.csv", index=False)