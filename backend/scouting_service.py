import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import text

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import similarity_engine


class ScoutingService:
    def __init__(self, engine):
        self.engine = engine
        self.scaler = MinMaxScaler()
        self.weights = np.array([
            0.5,  # goals_p90
            0.5,  # assists_p90
            1.5,  # npxg_p90
            1.0,  # shots_on_target_p90
        ])

    @staticmethod
    def _normalize_name(name: str) -> str:
        nfd = unicodedata.normalize("NFD", name)
        without_accents = "".join(
            char for char in nfd if unicodedata.category(char) != "Mn"
        )
        return without_accents.lower().strip()

    def _load_player_data(self, season: str) -> pd.DataFrame:
        query = text("""
            SELECT
                player_name,
                team_id,
                goals,
                assists,
                npxg,
                shots_on_target,
                minutes,
                fair_value
            FROM v_full_match_stats
            WHERE trim(season) = :season
        """)
        try:
            return pd.read_sql(query, self.engine, params={"season": str(season)})
        except Exception:
            fallback_query = text(str(query).replace("npxg", "xa"))
            df = pd.read_sql(fallback_query, self.engine, params={"season": str(season)})
            df = df.rename(columns={"xa": "npxg"})
            return df

    def _aggregate_players(self, df: pd.DataFrame, min_minutes: int) -> pd.DataFrame:
        metrics = ["goals", "assists", "npxg", "shots_on_target"]
        team_minutes = (
            df.groupby(["player_name", "team_id"], as_index=False)["minutes"]
            .sum()
            .sort_values(["player_name", "minutes"], ascending=[True, False])
        )
        team_primary = team_minutes.drop_duplicates("player_name")

        totals = df.groupby("player_name", as_index=False)[metrics + ["minutes"]].sum()
        fair_values = df.groupby("player_name", as_index=False)["fair_value"].mean()

        merged = totals.merge(team_primary[["player_name", "team_id"]], on="player_name")
        merged = merged.merge(fair_values, on="player_name", how="left")

        merged = merged[merged["minutes"] > int(min_minutes)].reset_index(drop=True)
        return merged

    def find_similar(self, player_name: str, season: str = "2025", min_minutes: int = 90, top_n: int = 5):
        df = self._load_player_data(season)
        if df.empty:
            raise ValueError("Nessun dato trovato per lo scouting.")

        df = self._aggregate_players(df, min_minutes)
        if df.empty:
            raise ValueError("Nessun dato trovato per lo scouting.")

        df = df.reset_index(drop=True)
        df["normalized_name"] = df["player_name"].apply(self._normalize_name)

        target_norm = self._normalize_name(player_name)
        target_rows = df.index[df["normalized_name"] == target_norm].tolist()
        if not target_rows:
            starts_with = df["normalized_name"].str.startswith(target_norm)
            contains = df["normalized_name"].str.contains(target_norm)
            fallback = df.index[starts_with | contains].tolist()
            if not fallback:
                raise ValueError("Giocatore non trovato o minuti insufficienti.")
            target_rows = [fallback[0]]

        target_idx = target_rows[0]
        target_player_name = df.loc[target_idx, "player_name"]

        metrics = ["goals", "assists", "npxg", "shots_on_target"]
        for m in metrics:
            df[f"{m}_p90"] = (df[m] / df["minutes"]) * 90

        cols_p90 = [f"{m}_p90" for m in metrics]
        matrix = self.scaler.fit_transform(df[cols_p90])

        results = similarity_engine.find_similar(
            matrix[target_idx],
            matrix,
            self.weights,
            int(top_n),
        )

        matches = []
        for res in results:
            idx = res.index
            if idx == target_idx:
                continue

            row = df.iloc[idx]
            similarity = max(0.0, 100 - (res.score * 20))
            matches.append({
                "player": row["player_name"],
                "team": row["team_id"],
                "similarity": round(similarity, 1),
                "data": {
                    "goals_p90": round(row["goals_p90"], 3),
                    "assists_p90": round(row["assists_p90"], 3),
                    "npxg_p90": round(row["npxg_p90"], 3),
                    "shots_on_target_p90": round(row["shots_on_target_p90"], 3),
                    "xg_p90": round(row["npxg_p90"], 3),
                    "fair_value": float(row["fair_value"] or 0),
                },
            })
            if len(matches) >= int(top_n):
                break

        return {
            "target": target_player_name,
            "position": "UNKNOWN",
            "matches": matches,
            "algorithm": "weighted_euclidean_cpp",
        }
