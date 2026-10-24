import sqlite3
import os

DB_PATH = os.path.join("data", "spizarnia.db")

def init_database():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print(f"Baza danych zinicjalizowana pomyślnie w: {DB_PATH}")
    conn.close()

if __name__ == "__main__":
    init_database()