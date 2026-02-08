import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.preprocessing import MinMaxScaler
import os
from dotenv import load_dotenv
import sys
from pathlib import Path
# Aggiungiamo il percorso del modulo C++ al sys.path
MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
import similarity_engine   # <--- IL TUO MODULO C++!

load_dotenv()

class ScoutingSystem:
    def __init__(self, season='2025', min_minutes=500):
        self.engine = create_engine(f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
        self.season = season
        self.min_minutes = min_minutes
        self.data = None
        self.matrix = None
        self.scaler = MinMaxScaler()
        
        # DEFINIZIONE PESI (Il segreto dello scouting)
        # Più alto il numero, più quella statistica deve essere simile.
        self.weights = np.array([
            0.5,  # goals_p90 (Importante ma variabile)
            0.5,  # assists_p90
            1.5,  # npxg_p90 (FONDAMENTALE: indica la capacità di smarcarsi)
            1.0,  # shots_on_target_p90 (Precisione)
        ])

    def load_and_prep_data(self):
        # 1. Carica Dati
        query = text("""
            SELECT player_name, goals, assists, npxg, shots_on_target, minutes
            FROM v_full_match_stats
            WHERE trim(season) = :s
        """)
        df = pd.read_sql(
            query,
            self.engine,
            params={"s": str(self.season), "min_minutes": int(self.min_minutes)},
        )

        if df.empty:
            seasons_df = pd.read_sql(
                text("SELECT DISTINCT season FROM v_full_match_stats ORDER BY season"),
                self.engine,
            )
            seasons = seasons_df["season"].dropna().astype(str).tolist()
            raise ValueError(
                "Nessun dato trovato per lo scouting! "
                f"Season richiesto: {self.season}. Disponibili: {seasons}"
            )

        metrics = ["goals", "assists", "npxg", "shots_on_target"]
        df = (
            df.groupby("player_name", as_index=False)[metrics + ["minutes"]]
            .sum()
        )
        df = df[df["minutes"] > int(self.min_minutes)].reset_index(drop=True)
        
        if df.empty:
            count_df = pd.read_sql(
                text("""
                    SELECT COUNT(*) AS count
                    FROM v_full_match_stats
                    WHERE trim(season) = :s
                """),
                self.engine,
                params={"s": str(self.season)},
            )
            season_count = int(count_df["count"].iloc[0])
            raise ValueError(
                "Nessun dato trovato per lo scouting! "
                f"Season richiesto: {self.season}. "
                f"Righe totali per season: {season_count}. "
                f"Filtro minuti: > {self.min_minutes}"
            )

        # 2. Calcola P90
        metrics = ['goals', 'assists', 'npxg', 'shots_on_target']
        for m in metrics:
            df[f'{m}_p90'] = (df[m] / df['minutes']) * 90
            
        # 3. Normalizza (0-1) per la distanza Euclidea
        cols_p90 = [f'{m}_p90' for m in metrics]
        self.matrix = self.scaler.fit_transform(df[cols_p90])
        
        # Salviamo il DF per risalire ai nomi dagli indici
        self.data = df.reset_index(drop=True)
        print(f"📊 Scouting Engine Caricato: {len(df)} giocatori pronti.")

    def find_similar(self, player_name, top_n=5):
        if self.data is None:
            self.load_and_prep_data()

        # Trova l'indice del giocatore target
        try:
            target_idx = self.data[self.data['player_name'] == player_name].index[0]
        except IndexError:
            return f"❌ Giocatore '{player_name}' non trovato o ha giocato meno di 500 min."

        target_vector = self.matrix[target_idx]

        # --- CHIAMATA AL MOTORE C++ ---
        # Passiamo liste native a C++ (Pybind11 converte numpy array in std::vector automaticamente)
        results = similarity_engine.find_similar(
            target_vector, 
            self.matrix, 
            self.weights, 
            top_n
        )
        # ------------------------------

        print(f"\n🔍 Analisi Similitudine per: {player_name.upper()}")
        print(f"   (Basata su: npxG, SoT - Weighted Euclidean C++)")
        
        output = []
        for res in results:
            # Salta se stesso (distanza ~0)
            name = self.data.iloc[res.index]['player_name']
            if name == player_name:
                continue
                
            similarity_perc = max(0, 100 - (res.score * 20)) # Conversione approssimativa in %
            print(f"   🔹 {name:<25} (Dist: {res.score:.4f} | Sim: {similarity_perc:.1f}%)")
            output.append({"name": name, "score": res.score})
            
        return output

if __name__ == "__main__":
    scout = ScoutingSystem(season='2025', min_minutes=0)
    
    # Test 1: Simili a Lautaro
    scout.find_similar("Lautaro Martínez", top_n=6)
    
    # Test 2: Simili a Pulisic (Profilo diverso, più creativo)
    scout.find_similar("Christian Pulisic", top_n=6)