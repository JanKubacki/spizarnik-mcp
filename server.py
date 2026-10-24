import json
import sqlite3
from pathlib import Path
from typing import Union, List, Dict, Any

from mcp.server.mcpserver import MCPServer

# Inicjalizacja serwera MCP dla systemu Spiżarnik AI (Spiżarnia Bez Dna Sp. z o.o.)
mcp = MCPServer("Spizarnik AI Server")

# Ścieżka do bazy SQLite wyliczana względem położenia tego pliku
DB_PATH = Path(__file__).parent / "data" / "spizarnia.db"


def polacz() -> sqlite3.Connection:
    """Otwiera bezpieczne połączenie z bazą SQLite z włączoną obsługą kluczy obcych."""
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Brak bazy danych pod adresem: {DB_PATH}. Uruchom najpierw skrypt 'python init_db.py'."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@mcp.tool()
def hello_spizarnik() -> str:
    """Funkcja testowa weryfikująca połączenie z serwerem MCP."""
    return "Serwer Spiżarnik AI działa poprawnie!"


@mcp.tool()
def sprawdz_stany_magazynowe(store_id: str, krytyczny_poziom: bool = False) -> dict:
    """Pokazuje stany magazynowe sklepu o podanym identyfikatorze lub nazwie (np. 'S1', 'S2', 'Mokotów').
    Gdy krytyczny_poziom=True, zwraca tylko produkty, których ilość jest poniżej zapasu bezpieczeństwa.

    Args:
        store_id: ID sklepu (np. 'S1', 'S2') lub fragment nazwy sklepu.
        krytyczny_poziom: Jeśli True, filtruje produkty wymagające pilnego uzupełnienia.
    """
    with polacz() as conn:
        sklep = conn.execute(
            """
            SELECT sklep_id, nazwa FROM sklepy 
            WHERE LOWER(sklep_id) = LOWER(?) OR LOWER(nazwa) LIKE LOWER(?)
            """,
            (store_id.strip(), f"%{store_id.strip()}%")
        ).fetchone()

        if sklep is None:
            dostepne = [f"{w['nazwa']} ({w['sklep_id']})" for w in conn.execute("SELECT sklep_id, nazwa FROM sklepy")]
            return {"blad": f"Nie znaleziono sklepu '{store_id}'. Dostępne sklepy: {dostepne}"}

        real_sklep_id = sklep["sklep_id"]

        sql = """
            SELECT s.sku, p.nazwa, p.kategoria, s.ilosc, s.zapas_bezpieczenstwa
            FROM stany_magazynowe s
            JOIN produkty p ON p.sku = s.sku
            WHERE s.sklep_id = ?
        """
        if krytyczny_poziom:
            sql += " AND s.ilosc < s.zapas_bezpieczenstwa"

        wiersze = conn.execute(sql + " ORDER BY s.sku", (real_sklep_id,)).fetchall()

    return {
        "sklep": sklep["nazwa"],
        "sklep_id": real_sklep_id,
        "liczba_produktow": len(wiersze),
        "produkty": [dict(w) for w in wiersze],
    }


@mcp.tool()
def porownaj_dostawcow(nazwa_produktu: str, ilosc: int = 1) -> dict:
    """Porównuje oferty dostawców dla wskazanego produktu i podanej ilości.
    Zwraca ceny, całkowity koszt, minimum logistyczne, ewentualne braki oraz czas dostawy.
    Nazwa produktu może być pełna, stanowić fragment nazwy lub być kodem SKU.

    Args:
        nazwa_produktu: Nazwa produktu (np. 'Mleko 2%', 'Mleko') lub SKU (np. 'NAB-001').
        ilosc: Zamawiana ilość w sztukach (domyślnie 1).
    """
    if not str(nazwa_produktu).strip():
        return {"blad": "Podaj nazwę lub SKU produktu."}

    if isinstance(ilosc, bool) or not isinstance(ilosc, int) or ilosc <= 0:
        return {"blad": "Ilość musi być dodatnią liczbą całkowitą."}

    with polacz() as conn:
        # Najpierw szukamy dokładnej nazwy, potem fragmentu nazwy lub SKU
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

        if len(produkt) > 1:
            return {
                "komunikat": "Znaleziono kilka pasujących produktów. Doprecyzuj nazwę.",
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


@mcp.tool()
def generuj_zamowienie(
    sklep_id: str,
    dostawca: str,
    pozycje: Union[List[Dict[str, Any]], str]
) -> dict:
    """Generuje projekt zamówienia dla sklepu od dostawcy.
    Automatycznie dopasowuje nazwy/ID sklepów, dostawców i produktów.
    Weryfikuje limit budżetu sklepu oraz minima logistyczne dostawcy.
    Tworzy zamówienie w stanie 'projekt' oczekujące na zatwierdzenie przez człowieka (Human-in-the-loop / EU AI Act).

    Args:
        sklep_id: Identyfikator lub nazwa sklepu (np. 'S1', 'Mokotów').
        dostawca: ID lub nazwa dostawcy (np. 'D1', 'MlekoHurt', 'WarzywaExpress').
        pozycje: Lista pozycji [{"sku": "NAB-001", "ilosc": 24}] lub [{"produkt": "Mleko 2%", "ilosc": 24}].
    """
    dostawca_param = str(dostawca).strip()
    sklep_param = str(sklep_id).strip()

    if isinstance(pozycje, str):
        try:
            pozycje = json.loads(pozycje)
        except json.JSONDecodeError:
            return {"blad": "Parametr 'pozycje' zawiera niepoprawny format JSON."}

    if not isinstance(pozycje, list) or len(pozycje) == 0:
        return {"blad": "Lista pozycji w zamówieniu nie może być pusta."}

    try:
        with polacz() as conn:
            cursor = conn.cursor()

            # 1. Identyfikacja sklepu i weryfikacja limitu budżetu
            sklep = cursor.execute(
                """
                SELECT sklep_id, nazwa, limit_budzetu FROM sklepy 
                WHERE LOWER(sklep_id) = LOWER(?) OR LOWER(nazwa) LIKE LOWER(?)
                """,
                (sklep_param, f"%{sklep_param}%")
            ).fetchone()

            if sklep is None:
                dostepne = [f"{w['nazwa']} ({w['sklep_id']})" for w in cursor.execute("SELECT sklep_id, nazwa FROM sklepy")]
                return {"blad": f"Nie znaleziono sklepu '{sklep_param}'. Dostępne sklepy: {dostepne}"}

            real_sklep_id = sklep["sklep_id"]
            limit_budzetu = float(sklep["limit_budzetu"])

            # 2. Identyfikacja dostawcy
            dostawca_rec = cursor.execute(
                """
                SELECT DISTINCT dostawca_id, nazwa FROM dostawcy 
                WHERE LOWER(dostawca_id) = LOWER(?) OR LOWER(nazwa) LIKE LOWER(?)
                """,
                (dostawca_param, f"%{dostawca_param}%")
            ).fetchone()

            if dostawca_rec is None:
                dostepni = [f"{w['nazwa']} (ID: {w['dostawca_id']})" for w in cursor.execute("SELECT DISTINCT dostawca_id, nazwa FROM dostawcy")]
                return {"blad": f"Nie znaleziono dostawcy '{dostawca_param}'. Dostępni dostawcy: {dostepni}"}

            real_dostawca_id = dostawca_rec["dostawca_id"]
            dostawca_nazwa = dostawca_rec["nazwa"]

            # 3. Weryfikacja pozycji i minimów logistycznych
            weryfikowane_pozycje = []
            laczna_wartosc = 0.0

            for poz in pozycje:
                szukana_nazwa_lub_sku = poz.get("sku") or poz.get("produkt") or poz.get("nazwa") or poz.get("produkt_id")
                ilosc = poz.get("ilosc", 0)

                if not szukana_nazwa_lub_sku or not isinstance(ilosc, int) or ilosc <= 0:
                    return {"blad": f"Niepoprawne dane pozycji: {poz}. Wymagane nazwa/SKU produktu oraz ilosc > 0."}

                term = str(szukana_nazwa_lub_sku).strip()

                oferta = cursor.execute(
                    """
                    SELECT d.sku, d.cena_hurtowa, d.minimum_logistyczne, p.nazwa AS produkt_nazwa
                    FROM dostawcy d
                    JOIN produkty p ON d.sku = p.sku
                    WHERE d.dostawca_id = ? AND (LOWER(d.sku) = LOWER(?) OR LOWER(p.nazwa) LIKE LOWER(?))
                    """,
                    (real_dostawca_id, term, f"%{term}%")
                ).fetchone()

                if oferta is None:
                    oferty_dostawcy = [
                        f"{w['produkt_nazwa']} (SKU: {w['sku']}, Min: {w['minimum_logistyczne']} szt.)"
                        for w in cursor.execute(
                            "SELECT p.nazwa AS produkt_nazwa, d.sku, d.minimum_logistyczne FROM dostawcy d JOIN produkty p ON d.sku = p.sku WHERE d.dostawca_id = ?",
                            (real_dostawca_id,)
                        ).fetchall()
                    ]
                    return {
                        "blad": f"Dostawca '{dostawca_nazwa}' nie ma w ofercie produktu '{term}'. Oferta dostawcy: {oferty_dostawcy}"
                    }

                sku_real = oferta["sku"]
                nazwa_prod = oferta["produkt_nazwa"]
                cena_hurtowa = float(oferta["cena_hurtowa"])
                min_logistyczne = int(oferta["minimum_logistyczne"])

                if ilosc < min_logistyczne:
                    return {
                        "status": "ODRZUCONO",
                        "powod": "Naruszenie minimum logistycznego",
                        "komunikat": f"Dla '{nazwa_prod}' zamówiono {ilosc} szt., ale minimum logistyczne wynosi {min_logistyczne} szt.",
                        "zalecenie": f"Zwiększ ilość w zamówieniu do co najmniej {min_logistyczne} szt."
                    }

                wartosc_pozycji = cena_hurtowa * ilosc
                laczna_wartosc += wartosc_pozycji

                weryfikowane_pozycje.append({
                    "sku": sku_real,
                    "nazwa": nazwa_prod,
                    "ilosc": ilosc,
                    "cena_jednostkowa": cena_hurtowa,
                    "wartosc": round(wartosc_pozycji, 2)
                })

            # 4. Sprawdzenie limitu budżetu
            if laczna_wartosc > limit_budzetu:
                return {
                    "status": "ODRZUCONO",
                    "powod": "Przekroczenie limitu budżetu sklepu",
                    "sklep": sklep["nazwa"],
                    "sklep_id": real_sklep_id,
                    "wymagana_kwota": round(laczna_wartosc, 2),
                    "dostepny_limit_budzetu": round(limit_budzetu, 2),
                    "brakuje": round(laczna_wartosc - limit_budzetu, 2)
                }

            # 5. Rejestracja w bazie ze statusem 'projekt'
            cursor.execute(
                """
                INSERT INTO zamowienia (sklep_id, dostawca_id, status, wartosc)
                VALUES (?, ?, 'projekt', ?)
                """,
                (real_sklep_id, real_dostawca_id, laczna_wartosc)
            )
            zamowienie_id = cursor.lastrowid

            for item in weryfikowane_pozycje:
                cursor.execute(
                    """
                    INSERT INTO pozycje_zamowienia (zamowienie_id, sku, ilosc, cena_jednostkowa)
                    VALUES (?, ?, ?, ?)
                    """,
                    (zamowienie_id, item["sku"], item["ilosc"], item["cena_jednostkowa"])
                )

            nowy_limit = limit_budzetu - laczna_wartosc
            cursor.execute(
                "UPDATE sklepy SET limit_budzetu = ? WHERE sklep_id = ?",
                (nowy_limit, real_sklep_id)
            )

            conn.commit()

            return {
                "status": "SUKCES",
                "komunikat": f"Wygenerowano PROJEKT zamówienia nr #{zamowienie_id}. Wymaga zatwierdzenia przez człowieka.",
                "zamowienie_id": zamowienie_id,
                "sklep": sklep["nazwa"],
                "sklep_id": real_sklep_id,
                "dostawca": dostawca_nazwa,
                "dostawca_id": real_dostawca_id,
                "status_zamowienia": "projekt",
                "laczna_wartosc": round(laczna_wartosc, 2),
                "pozostaly_limit_budzetu": round(nowy_limit, 2),
                "pozycje": weryfikowane_pozycje,
                "instrukcja_dla_operatora": f"Aby zaakceptować zamówienie i przekazać do realizacji, użyj narzędzia zatwierdz_zamowienie(zamowienie_id={zamowienie_id})."
            }

    except sqlite3.Error as e:
        return {"blad": f"Błąd bazy danych SQLite: {str(e)}"}


@mcp.tool()
def zatwierdz_zamowienie(zamowienie_id: int) -> dict:
    """Narzędzie Nadzoru Ludzkiego (Human-in-the-loop / EU AI Act).
    Zatwierdza projekt zamówienia przygotowany przez AI i zmienia jego status z 'projekt' na 'zatwierdzone'.

    Args:
        zamowienie_id: Numer ID zamówienia w stanie 'projekt'.
    """
    try:
        with polacz() as conn:
            cursor = conn.cursor()

            zamowienie = cursor.execute(
                """
                SELECT z.zamowienie_id, z.status, z.wartosc, s.nazwa AS sklep_nazwa, d.nazwa AS dostawca_nazwa
                FROM zamowienia z
                JOIN sklepy s ON z.sklep_id = s.sklep_id
                JOIN dostawcy d ON z.dostawca_id = d.dostawca_id
                WHERE z.zamowienie_id = ?
                """,
                (zamowienie_id,)
            ).fetchone()

            if zamowienie is None:
                return {"blad": f"Zamówienie o ID #{zamowienie_id} nie istnieje w bazie."}

            if zamowienie["status"] == "zatwierdzone":
                return {"komunikat": f"Zamówienie #{zamowienie_id} jest już zatwierdzone."}

            if zamowienie["status"] != "projekt":
                return {
                    "blad": f"Nie można zatwierdzić zamówienia #{zamowienie_id}. Aktualny status to '{zamowienie['status']}' (wymagany: 'projekt')."
                }

            cursor.execute(
                "UPDATE zamowienia SET status = 'zatwierdzone' WHERE zamowienie_id = ?",
                (zamowienie_id,)
            )

            conn.commit()

            return {
                "status": "SUKCES",
                "komunikat": f"ZATWIERDZONO ZAMÓWIENIE #{zamowienie_id} przez operatora (Human-in-the-loop).",
                "zamowienie_id": zamowienie_id,
                "sklep": zamowienie["sklep_nazwa"],
                "dostawca": zamowienie["dostawca_nazwa"],
                "wartosc": float(zamowienie["wartosc"]),
                "nowy_status": "zatwierdzone",
                "dalsze_kroki": "Zamówienie zostało przekazane do dostawcy. Po otrzymaniu towaru użyj rejestruj_dostawe."
            }

    except sqlite3.Error as e:
        return {"blad": f"Błąd bazy danych SQLite: {str(e)}"}


@mcp.tool()
def anuluj_zamowienie(zamowienie_id: int) -> dict:
    """Narzędzie Nadzoru Ludzkiego (Human-in-the-loop / EU AI Act).
    Odrzuca projekt zamówienia wygenerowany przez AI, zmienia status na 'anulowane' oraz zwraca zarezerwowany budżet do sklepu.

    Args:
        zamowienie_id: Numer ID zamówienia do anulowania.
    """
    try:
        with polacz() as conn:
            cursor = conn.cursor()

            zamowienie = cursor.execute(
                "SELECT zamowienie_id, sklep_id, status, wartosc FROM zamowienia WHERE zamowienie_id = ?",
                (zamowienie_id,)
            ).fetchone()

            if zamowienie is None:
                return {"blad": f"Zamówienie o ID #{zamowienie_id} nie istnieje w bazie."}

            if zamowienie["status"] == "anulowane":
                return {"komunikat": f"Zamówienie #{zamowienie_id} jest już anulowane."}

            if zamowienie["status"] == "dostarczone":
                return {"blad": f"Nie można anulować zamówienia #{zamowienie_id}, ponieważ zostało już dostarczone."}

            sklep_id = zamowienie["sklep_id"]
            wartosc = float(zamowienie["wartosc"])

            cursor.execute(
                "UPDATE sklepy SET limit_budzetu = limit_budzetu + ? WHERE sklep_id = ?",
                (wartosc, sklep_id)
            )

            cursor.execute(
                "UPDATE zamowienia SET status = 'anulowane' WHERE zamowienie_id = ?",
                (zamowienie_id,)
            )

            conn.commit()

            return {
                "status": "SUKCES",
                "komunikat": f"Anulowano zamówienie #{zamowienie_id}. Zarezerwowana kwota {wartosc:.2f} PLN została zwrócona do budżetu sklepu {sklep_id}.",
                "zamowienie_id": zamowienie_id,
                "nowy_status": "anulowane"
            }

    except sqlite3.Error as e:
        return {"blad": f"Błąd bazy danych SQLite: {str(e)}"}


@mcp.tool()
def rejestruj_dostawe(zamowienie_id: int) -> dict:
    """Rejestruje przyjęcie dostawy dla zamówienia o stanie 'zatwierdzone'.
    Aktualizuje stany magazynowe sklepu oraz zmienia status zamówienia na 'dostarczone'.

    Args:
        zamowienie_id: Numer ID zamówienia do przyjęcia.
    """
    try:
        with polacz() as conn:
            cursor = conn.cursor()

            zamowienie = cursor.execute(
                "SELECT zamowienie_id, sklep_id, status FROM zamowienia WHERE zamowienie_id = ?",
                (zamowienie_id,)
            ).fetchone()

            if zamowienie is None:
                return {"blad": f"Zamówienie o ID #{zamowienie_id} nie istnieje w bazie."}

            if zamowienie["status"] == "dostarczone":
                return {"blad": f"Zamówienie #{zamowienie_id} zostało już wcześniej przyjęte (status: 'dostarczone')."}

            if zamowienie["status"] == "anulowane":
                return {"blad": f"Zamówienie #{zamowienie_id} jest anulowane. Nie można go przyjąć."}

            if zamowienie["status"] == "projekt":
                return {
                    "blad": f"Zamówienie #{zamowienie_id} ma status 'projekt'. Najpierw wymaga zatwierdzenia przez człowieka (użyj zatwierdz_zamowienie)."
                }

            pozycje = cursor.execute(
                "SELECT sku, ilosc FROM pozycje_zamowienia WHERE zamowienie_id = ?",
                (zamowienie_id,)
            ).fetchall()

            sklep_id = zamowienie["sklep_id"]

            for item in pozycje:
                sku = item["sku"]
                ilosc_dostarczona = item["ilosc"]

                cursor.execute(
                    """
                    UPDATE stany_magazynowe 
                    SET ilosc = ilosc + ? 
                    WHERE sklep_id = ? AND sku = ?
                    """,
                    (ilosc_dostarczona, sklep_id, sku)
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        """
                        INSERT INTO stany_magazynowe (sklep_id, sku, ilosc, zapas_bezpieczenstwa)
                        VALUES (?, ?, ?, 10)
                        """,
                        (sklep_id, sku, ilosc_dostarczona)
                    )

            cursor.execute(
                "UPDATE zamowienia SET status = 'dostarczone' WHERE zamowienie_id = ?",
                (zamowienie_id,)
            )

            conn.commit()

            return {
                "status": "SUKCES",
                "komunikat": f"Zamówienie #{zamowienie_id} zostało pomyślnie przyjęte do magazynu sklepu '{sklep_id}'.",
                "zamowienie_id": zamowienie_id,
                "sklep_id": sklep_id,
                "nowy_status": "dostarczone",
                "przyjete_pozycje_liczba": len(pozycje)
            }

    except sqlite3.Error as e:
        return {"blad": f"Błąd bazy danych SQLite: {str(e)}"}


if __name__ == "__main__":
    mcp.run()