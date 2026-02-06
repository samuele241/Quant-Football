from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

# 1. Tabella LEAGUES (Campionati)
class League(Base):
    __tablename__ = 'leagues'
    
    id = Column(String, primary_key=True)  # es. "ITA-Serie A"
    name = Column(String, nullable=False)
    country = Column(String)

# 2. Tabella TEAMS (Squadre)
class Team(Base):
    __tablename__ = 'teams'
    
    id = Column(String, primary_key=True) # Useremo il nome come ID per semplicità all'inizio (es. "Juventus")
    league_id = Column(String, ForeignKey('leagues.id'))
    
# 3. Tabella MATCHES (Partite)
class Match(Base):
    __tablename__ = 'matches'
    
    id = Column(String, primary_key=True) # Un ID unico generato da noi
    date = Column(DateTime)
    league_id = Column(String, ForeignKey('leagues.id'))
    home_team = Column(String, ForeignKey('teams.id'))
    away_team = Column(String, ForeignKey('teams.id'))
    home_score = Column(Integer)
    away_score = Column(Integer)
    home_xg = Column(Float)
    away_xg = Column(Float)

# 4. Tabella PLAYER STATS (Il cuore del progetto)
# Qui salviamo le prestazioni partita per partita
class PlayerMatchStat(Base):
    __tablename__ = 'player_match_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_name = Column(String, nullable=False)
    team_id = Column(String, ForeignKey('teams.id'))
    match_date = Column(Date) # Utile per le serie temporali
    season = Column(String)
    
    # Dati Statistici (Shooting)
    minutes = Column(Integer)
    goals = Column(Integer)
    assists = Column(Integer)
    shots = Column(Integer)
    shots_on_target = Column(Integer)
    # --- NUOVA COLONNA ---
    opponent = Column(String) 
    # ---------------------
    xg = Column(Float) # Expected Goals
    npxg = Column(Float) # Non-Penalty xG
    
    # Fair Value Estimation (in milioni di €)
    fair_value = Column(Float, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())