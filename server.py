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

@mcp.tool()
def porownaj_dostawcow(nazwa_produktu: str, ilosc: int) -> dict:
    """Porównuje oferty dostawców dla produktu i podanej ilości.
    Zwraca ceny, całkowity koszt, minimum logistyczne i czas dostawy.
    Nazwa produktu może być pełna lub stanowić fragment nazwy."""

    if not nazwa_produktu.strip():
        return {"blad": "Podaj nazwę produktu."}

    if isinstance(ilosc, bool) or not isinstance(ilosc, int) or ilosc <= 0:
        return {"blad": "Ilość musi być dodatnią liczbą całkowitą."}

    with polacz() as conn:
        # Najpierw szukamy dokładnej nazwy, potem fragmentu nazwy lub SKU.
        produkt = conn.execute(
            """
            SELECT sku, nazwa
            FROM produkty
            WHERE lower(trim(nazwa)) = lower(trim(?))
            """,
            (nazwa_produktu,),
        ).fetchall()

        if not produkt:
            produkt = conn.execute(
                """
                SELECT sku, nazwa
                FROM produkty
                WHERE lower(nazwa) LIKE lower(?)
                   OR lower(sku) = lower(trim(?))
                ORDER BY nazwa
                """,
                (f"%{nazwa_produktu.strip()}%", nazwa_produktu),
            ).fetchall()

        if not produkt:
            return {
                "blad": f"Nie znaleziono produktu: {nazwa_produktu}",
                "wskazowka": "Sprawdź nazwę lub podaj SKU produktu.",
            }

        # Nie wybieramy arbitralnie, jeśli nazwa pasuje do wielu produktów.
        if len(produkt) > 1:
            return {
                "komunikat": "Znaleziono kilka produktów. Doprecyzuj nazwę.",
                "dopasowania": [
                    {"sku": p["sku"], "nazwa": p["nazwa"]}
                    for p in produkt
                ],
            }

        p = produkt[0]

        oferty = conn.execute(
            """
            SELECT
                dostawca_id,
                nazwa,
                cena_hurtowa,
                czas_dostawy_dni,
                minimum_logistyczne
            FROM dostawcy
            WHERE sku = ?
            ORDER BY cena_hurtowa ASC
            """,
            (p["sku"],),
        ).fetchall()

    if not oferty:
        return {
            "produkt": p["nazwa"],
            "sku": p["sku"],
            "ilosc_zamawiana": ilosc,
            "komunikat": "Żaden dostawca nie oferuje tego produktu.",
            "oferty": [],
        }

    porownanie = []

    for o in oferty:
        cena = o["cena_hurtowa"]
        minimum = o["minimum_logistyczne"]
        spelnia_minimum = ilosc >= minimum

        porownanie.append({
            "dostawca_id": o["dostawca_id"],
            "dostawca": o["nazwa"],
            "cena_jednostkowa": round(cena, 2),
            "ilosc": ilosc,
            "wartosc_zamowienia": round(cena * ilosc, 2),
            "minimum_logistyczne": minimum,
            "minimum_spelnione": spelnia_minimum,
            "brakujace_sztuki": max(0, minimum - ilosc),
            "czas_dostawy_dni": o["czas_dostawy_dni"],
        })

    return {
        "produkt": p["nazwa"],
        "sku": p["sku"],
        "ilosc_zamawiana": ilosc,
        "waluta": "PLN",
        "liczba_ofert": len(porownanie),
        "oferty": porownanie,
        "uwaga": (
            "Minimum logistyczne dotyczy danego produktu. "
            "Baza nie określa minimalnej wartości całego zamówienia."
        ),
    }

if __name__ == "__main__":
    mcp.run()
