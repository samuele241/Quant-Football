import wikipedia
import dateparser
from sqlalchemy import create_engine, text
import time
import re
import os
from dotenv import load_dotenv

load_dotenv()

# Configurazione
wikipedia.set_lang("en") # Inglese è più standard per le date
DB_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)

def extract_birth_date(player_name):
    try:
        # Cerca su Wikipedia (aggiungiamo "footballer" per evitare omonimi)
        search_results = wikipedia.search(f"{player_name} footballer")
        if not search_results:
            return None
        
        # Prende la prima pagina trovata
        page = wikipedia.page(search_results[0], auto_suggest=False)
        
        # Cerchiamo pattern di data nel contenuto (es. "born 22 August 1997")
        # Regex per catturare: (born) (Day Month Year)
        summary = page.summary[:500] # Primi 500 caratteri bastano
        
        # Cerchiamo date comuni
        match = re.search(r'born\s+(\d{1,2}\s+\w+\s+\d{4})', summary)
        if match:
            date_str = match.group(1)
            return dateparser.parse(date_str)
            
        # Fallback: a volte è (born Month Day, Year)
        match = re.search(r'born\s+(\w+\s+\d{1,2},\s+\d{4})', summary)
        if match:
            date_str = match.group(1)
            return dateparser.parse(date_str)

    except Exception as e:
        print(f"   ⚠️ Errore Wiki per {player_name}: {e}")
        return None
    
    return None

def update_ages():
    print("🎂 Avvio Wikipedia Age Hunter...")
    
    with engine.connect() as conn:
        # Prendiamo i giocatori che NON hanno ancora la data di nascita
        players = conn.execute(text("SELECT player_id, name FROM players WHERE birth_date IS NULL")).fetchall()
    
    print(f"🔍 Trovati {len(players)} giocatori senza data di nascita.")
    
    count = 0
    for p_id, name in players:
        print(f"   Searching: {name}...", end=" ", flush=True)
        
        birth_date = extract_birth_date(name)
        
        if birth_date:
            print(f"✅ Trovato: {birth_date.strftime('%Y-%m-%d')}")
            
            # Aggiorna DB
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE players SET birth_date = :bd WHERE player_id = :pid"),
                    {"bd": birth_date, "pid": p_id}
                )
            count += 1
        else:
            print("❌ Non trovato.")
        
        # Pausa etica per non spammare Wikipedia (importante!)
        time.sleep(0.5)

    print(f"\n🎉 Finito! Aggiornati {count} giocatori.")

if __name__ == "__main__":
    update_ages()