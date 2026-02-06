import os
import urllib.parse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carica le variabili
load_dotenv()

# Recupera i pezzi
db_pass = os.getenv("DB_PASSWORD")
db_user = os.getenv("DB_USER")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# Check preliminare
if not db_pass:
    print("❌ Errore: Manca la password nel file .env")
    exit()

# --- MAGIA QUI ---
# Codifichiamo la password per renderla sicura nell'URL (es. '@' diventa '%40')
encoded_pass = urllib.parse.quote_plus(db_pass)

# Costruiamo l'URL noi, non ci fidiamo del copia-incolla
db_url = f"postgresql://{db_user}:{encoded_pass}@{db_host}:{db_port}/{db_name}"

print(f"🔄 Tentativo di connessione a: {db_host}...")

try:
    # Aggiungiamo un timeout di 10 secondi per non aspettare in eterno
    engine = create_engine(db_url, connect_args={'connect_timeout': 10})
    
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.fetchone()
        print(f"✅ CONNESSO! Database pronto.")
        print(f"ℹ️  Versione: {version[0]}")

except Exception as e:
    print("\n❌ ERRORE DI CONNESSIONE:")
    print(e)
    print("\n💡 SUGGERIMENTO:")
    print("Se l'errore parla di 'timeout' o 'resolution', prova a cambiare DB_PORT=6543 nel file .env")