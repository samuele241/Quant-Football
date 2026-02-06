import os
import urllib.parse
from sqlalchemy import create_engine
from dotenv import load_dotenv
from models import Base

# --- CONFIGURAZIONE CONNESSIONE (Come prima) ---
load_dotenv()
db_pass = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
db_user = os.getenv("DB_USER")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

def init_db():
    print("🛠  Connessione al DB in corso...")
    engine = create_engine(db_url)
    
    print("🏗  Creazione delle tabelle su Supabase...")
    # Questo comando crea tutte le tabelle definite in models.py se non esistono
    Base.metadata.create_all(engine)
    
    print("✅ Tabelle create con successo! Il DB è pronto a ricevere dati.")

if __name__ == "__main__":
    init_db()