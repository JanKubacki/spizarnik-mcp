"""Tworzy bazę data/spizarnia.db od zera:
najpierw tabele (data/schemat.sql), potem dane (data/dane_poczatkowe.sql).

Uruchom ponownie, żeby przywrócić bazę do stanu początkowego,
np. przed testami i przed demo.
"""
import sqlite3
from pathlib import Path

KATALOG = Path(__file__).parent / "data"
DB_PATH = KATALOG / "spizarnia.db"
SCHEMAT = KATALOG / "schemat.sql"
DANE = KATALOG / "dane_poczatkowe.sql"
TABELE = ["sklepy", "produkty", "stany_magazynowe", "dostawcy",
          "zamowienia", "pozycje_zamowienia"]


def init_database():
    try:
        DB_PATH.unlink(missing_ok=True)  # zaczynamy od czystej bazy
    except PermissionError:
        raise SystemExit("Baza jest otwarta w innym programie "
                         "(DB Browser albo Claude Desktop). Zamknij go i spróbuj ponownie.")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMAT.read_text(encoding="utf-8"))
        conn.executescript(DANE.read_text(encoding="utf-8"))
        conn.commit()

        print(f"Baza danych utworzona: {DB_PATH}")
        print("Liczba wierszy w tabelach:")
        for tabela in TABELE:
            liczba = conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
            print(f"  {tabela}: {liczba}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
