import sqlite3
from pathlib import Path

from mcp.server.mcpserver import MCPServer

# Inicjalizacja serwera MCP dla systemu Spiżarnik AI (Spiżarnia Bez Dna Sp. z o.o.)
mcp = MCPServer("Spizarnik AI Server")

# Baza leży w folderze data/ obok tego pliku. Ścieżka liczona od położenia pliku,
# a nie od folderu uruchomienia, bo Claude Desktop startuje serwer z innego miejsca.
DB_PATH = Path(__file__).parent / "data" / "spizarnia.db"


def polacz() -> sqlite3.Connection:
    """Otwiera połączenie z bazą. Wiersze są dostępne po nazwach kolumn."""
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Brak bazy danych: {DB_PATH}. Uruchom najpierw 'python init_db.py'."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@mcp.tool()
def hello_spizarnik() -> str:
    """Funkcja testowa weryfikująca połączenie z serwerem MCP."""
    return "Serwer Spiżarnik AI działa poprawnie!"


@mcp.tool()
def sprawdz_stany_magazynowe(store_id: str, krytyczny_poziom: bool = False) -> dict:
    """Pokazuje stany magazynowe sklepu o podanym identyfikatorze (np. 'S1').
    Gdy krytyczny_poziom=True, zwraca tylko produkty poniżej zapasu bezpieczeństwa."""
    with polacz() as conn:
        sklep = conn.execute(
            "SELECT nazwa FROM sklepy WHERE sklep_id = ?", (store_id,)
        ).fetchone()
        if sklep is None:
            dostepne = [w["sklep_id"] for w in conn.execute("SELECT sklep_id FROM sklepy")]
            return {"blad": f"Nie ma sklepu '{store_id}'. Dostępne sklepy: {dostepne}"}

        sql = """
            SELECT s.sku, p.nazwa, s.ilosc, s.zapas_bezpieczenstwa
            FROM stany_magazynowe s
            JOIN produkty p ON p.sku = s.sku
            WHERE s.sklep_id = ?
        """
        if krytyczny_poziom:
            sql += " AND s.ilosc < s.zapas_bezpieczenstwa"
        wiersze = conn.execute(sql + " ORDER BY s.sku", (store_id,)).fetchall()

    return {
        "sklep": sklep["nazwa"],
        "liczba_produktow": len(wiersze),
        "produkty": [dict(w) for w in wiersze],
    }


if __name__ == "__main__":
    mcp.run()
