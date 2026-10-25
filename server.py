import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Dict, List, Union

from mcp.server.mcpserver import MCPServer

# Inicjalizacja serwera MCP dla systemu Spiżarnik AI (Spiżarnia Bez Dna Sp. z o.o.)
mcp = MCPServer("Spizarnik AI Server")

# Ścieżki do bazy SQLite oraz katalogu z dokumentacją (Single Source of Truth)
DB_PATH = Path(__file__).parent / "data" / "spizarnia.db"
DOCS_PATH = Path(__file__).parent / "docs"


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


def odczytaj_plik_docs(nazwa_pliku: str, domyslna_tresc: str) -> str:
    """Pomocnicza funkcja bezpiecznie odczytująca pliki Markdown z katalogu docs/."""
    sciezka = DOCS_PATH / nazwa_pliku
    if sciezka.exists():
        return sciezka.read_text(encoding="utf-8")
    return domyslna_tresc


def znajdz_sklep(conn: sqlite3.Connection, tekst: str):
    """Szuka sklepu po ID ('S2') albo po nazwie lub jej fragmencie ('Mokotów').
    Zwraca (sklep, None), gdy jest dokładnie jedno dopasowanie,
    albo (None, slownik_z_bledem), gdy nie ma żadnego albo jest ich kilka."""
    tekst = str(tekst).strip()
    if not tekst:
        return None, {"blad": "Podaj identyfikator lub nazwę sklepu."}

    # 1. Najpierw dokładne ID, np. 'S2' albo 's2'
    sklep = conn.execute(
        "SELECT * FROM sklepy WHERE LOWER(sklep_id) = LOWER(?)", (tekst,)
    ).fetchone()
    if sklep:
        return sklep, None

    # 2. Potem fragment nazwy, np. 'Mokotów'
    pasujace = conn.execute(
        "SELECT * FROM sklepy WHERE LOWER(nazwa) LIKE LOWER(?) ORDER BY sklep_id",
        (f"%{tekst}%",),
    ).fetchall()

    if len(pasujace) == 1:
        return pasujace[0], None

    if not pasujace:
        wszystkie = conn.execute("SELECT sklep_id, nazwa FROM sklepy ORDER BY sklep_id").fetchall()
        return None, {
            "blad": f"Nie znaleziono sklepu '{tekst}'.",
            "dostepne_sklepy": [f"{s['nazwa']} ({s['sklep_id']})" for s in wszystkie],
        }

    return None, {
        "blad": f"Nazwa '{tekst}' pasuje do kilku sklepów. Doprecyzuj, o który chodzi.",
        "pasujace_sklepy": [f"{s['nazwa']} ({s['sklep_id']})" for s in pasujace],
    }


def znajdz_dostawce(conn: sqlite3.Connection, tekst: str):
    """Szuka dostawcy po ID ('D1') albo po nazwie lub jej fragmencie ('MlekoHurt').
    Zwraca (dostawca, None), gdy jest dokładnie jedno dopasowanie,
    albo (None, slownik_z_bledem), gdy nie ma żadnego albo jest ich kilka."""
    tekst = str(tekst).strip()
    if not tekst:
        return None, {"blad": "Podaj identyfikator lub nazwę dostawcy."}

    # 1. Dokładne ID albo dokładna nazwa, np. 'D1' albo 'MlekoHurt'
    dokladne = conn.execute(
        """
        SELECT DISTINCT dostawca_id, nazwa FROM dostawcy
        WHERE LOWER(dostawca_id) = LOWER(?) OR LOWER(nazwa) = LOWER(?)
        """,
        (tekst, tekst),
    ).fetchall()
    if len(dokladne) == 1:
        return dokladne[0], None

    # 2. Fragment nazwy, np. 'Mleko'
    pasujace = conn.execute(
        """
        SELECT DISTINCT dostawca_id, nazwa FROM dostawcy
        WHERE LOWER(nazwa) LIKE LOWER(?)
        ORDER BY dostawca_id
        """,
        (f"%{tekst}%",),
    ).fetchall()

    if len(pasujace) == 1:
        return pasujace[0], None

    if not pasujace:
        wszyscy = conn.execute(
            "SELECT DISTINCT dostawca_id, nazwa FROM dostawcy ORDER BY dostawca_id"
        ).fetchall()
        return None, {
            "blad": f"Nie znaleziono dostawcy '{tekst}'.",
            "dostepni_dostawcy": [f"{d['nazwa']} ({d['dostawca_id']})" for d in wszyscy],
        }

    return None, {
        "blad": f"Nazwa '{tekst}' pasuje do kilku dostawców. Doprecyzuj, o którego chodzi.",
        "pasujacy_dostawcy": [f"{d['nazwa']} ({d['dostawca_id']})" for d in pasujace],
    }


def znajdz_oferte(conn: sqlite3.Connection, dostawca_id: str, tekst: str):
    """Szuka produktu w ofercie wskazanego dostawcy po SKU ('NAB-001') albo po nazwie.
    Zwraca (oferta, None), gdy jest dokładnie jedno dopasowanie,
    albo (None, slownik_z_bledem), gdy nie ma żadnego albo jest ich kilka."""
    tekst = str(tekst).strip()
    zapytanie = """
        SELECT d.sku, d.cena_hurtowa, d.minimum_logistyczne, p.nazwa AS produkt_nazwa
        FROM dostawcy d
        JOIN produkty p ON d.sku = p.sku
        WHERE d.dostawca_id = ? AND {warunek}
        ORDER BY p.nazwa
    """

    # 1. Dokładne SKU albo dokładna nazwa produktu
    dokladne = conn.execute(
        zapytanie.format(warunek="(LOWER(d.sku) = LOWER(?) OR LOWER(p.nazwa) = LOWER(?))"),
        (dostawca_id, tekst, tekst),
    ).fetchall()
    if len(dokladne) == 1:
        return dokladne[0], None

    # 2. Fragment nazwy, np. 'Mleko'
    pasujace = conn.execute(
        zapytanie.format(warunek="LOWER(p.nazwa) LIKE LOWER(?)"),
        (dostawca_id, f"%{tekst}%"),
    ).fetchall()

    if len(pasujace) == 1:
        return pasujace[0], None

    if not pasujace:
        oferta = conn.execute(
            zapytanie.format(warunek="1 = 1"), (dostawca_id,)
        ).fetchall()
        return None, {
            "blad": f"Ten dostawca nie ma w ofercie produktu '{tekst}'.",
            "oferta_dostawcy": [
                f"{o['produkt_nazwa']} (SKU: {o['sku']}, minimum: {o['minimum_logistyczne']} szt.)"
                for o in oferta
            ],
        }

    return None, {
        "blad": f"Nazwa '{tekst}' pasuje do kilku produktów tego dostawcy. Doprecyzuj albo podaj SKU.",
        "pasujace_produkty": [f"{o['produkt_nazwa']} (SKU: {o['sku']})" for o in pasujace],
    }


# ==============================================================================
# MCP RESOURCES (Zasoby Kontekstowe - Wariant B: Dynamiczne źródła z bazy i docs/)
# ==============================================================================

@mcp.resource(
    "spizarnik://sklepy",
    name="Lista sklepów",
    description="Aktualna lista sklepów wraz z ich identyfikatorami i limitami budżetowymi.",
    mime_type="application/json",
)
def lista_sklepow_resource() -> str:
    """Udostępnia aktualną listę sklepów z bazy danych jako zasób MCP w formacie JSON."""
    with closing(polacz()) as conn:
        sklepy = [
            dict(row)
            for row in conn.execute(
                "SELECT sklep_id, nazwa, limit_budzetu FROM sklepy ORDER BY sklep_id"
            ).fetchall()
        ]

    wynik = {
        "liczba_sklepow": len(sklepy),
        "sklepy": sklepy,
    }
    return json.dumps(wynik, ensure_ascii=False, indent=2)


@mcp.resource(
    "spizarnik://produkty",
    name="Katalog produktów",
    description="Aktualny katalog produktów z kodami SKU i podstawowymi informacjami.",
    mime_type="application/json",
)
def katalog_produktow_resource() -> str:
    """Udostępnia katalog produktów z bazy SQLite jako zasób MCP w formacie JSON."""
    with closing(polacz()) as conn:
        produkty = [
            dict(row)
            for row in conn.execute(
                """
                SELECT sku, nazwa, kategoria, cena_sprzedazy, okres_waznosci_dni
                FROM produkty
                ORDER BY kategoria, nazwa
                """
            ).fetchall()
        ]

    wynik = {
        "liczba_produktow": len(produkty),
        "produkty": produkty,
    }
    return json.dumps(wynik, ensure_ascii=False, indent=2)


@mcp.resource(
    "spizarnik://regulamin",
    name="Regulamin logistyki i AI Governance",
    description="Wewnętrzny regulamin logistyki i zasady nadzoru ludzkiego czytane z pliku docs/regulamin_logistyki.md.",
    mime_type="text/markdown",
)
def regulamin_resource() -> str:
    """Odczytuje aktualną treść regulaminu z pliku docs/regulamin_logistyki.md."""
    domyslna = """
    === REGULAMIN LOGISTYKI I AI GOVERNANCE ===
    Spiżarnia Bez Dna Sp. z o.o.
    1. PROCEDURA NADZORU LUDZKIEGO (EU AI Act): Zamówienia generowane są jako 'projekt' i wymagają zatwierdzenia przez człowieka.
    2. FINOPS: Projekty zamówień rezerwują budżet sklepu.
    """
    return odczytaj_plik_docs("regulamin_logistyki.md", domyslna)


@mcp.resource(
    "spizarnik://warunki-dostawcow",
    name="Warunki kontraktowe i Supply Chain dostawców",
    description="Szczegółowa specyfikacja hurtowni (D1, D2, D3), harmonogramy dostaw i kryteria wyboru oferty.",
    mime_type="application/json",
)
def warunki_dostawcow_resource() -> str:
    """Udostępnia profile dostawców i zestawienie dostępnych ofert hurtowych z bazy w formacie JSON."""
    with closing(polacz()) as conn:
        oferty = [
            dict(row)
            for row in conn.execute(
                """
                SELECT d.dostawca_id, d.nazwa AS dostawca_nazwa, d.sku, p.nazwa AS produkt_nazwa,
                       d.cena_hurtowa, d.czas_dostawy_dni, d.minimum_logistyczne
                FROM dostawcy d
                JOIN produkty p ON d.sku = p.sku
                ORDER BY d.dostawca_id, p.nazwa
                """
            ).fetchall()
        ]

    wynik = {
        "opis": "Baza umów B2B z dostawcami Spiżarni Bez Dna Sp. z o.o.",
        "profil_dostawcow": {
            "D1_MlekoHurt": "Specjalizacja: Nabiał. Szybka dostawa (1 dzień), małe minima logistyczne. Realizacja dostaw od poniedziałku do piątku.",
            "D2_WarzywaExpress": "Specjalizacja: Świeże warzywa i owoce. Czas dostawy: 1 dzień. Wymagany natychmiastowy odbiór jakościowy przy przyjęciu.",
            "D3_HurtoSfera": "Specjalizacja: Hurtownia ogólnoasortymentowa. Niższe ceny hurtowe, ale dłuższy czas dostawy (3 dni) i wyższe minima logistyczne."
        },
        "oferty_hurtowe": oferty
    }
    return json.dumps(wynik, ensure_ascii=False, indent=2)


@mcp.resource(
    "spizarnik://rodo-compliance",
    name="Polityka ochrony danych RODO i Compliance",
    description="Zasady anonimizacji danych osobowych i ograniczeń prawne czytane z pliku docs/rodo_compliance.md.",
    mime_type="text/markdown",
)
def rodo_compliance_resource() -> str:
    """Odczytuje zasady ochrony danych i RODO z pliku docs/rodo_compliance.md."""
    domyslna = """
    === POLITYKA OCHRONY DANYCH OSOBOWYCH (RODO/GDPR) ===
    Spiżarnia Bez Dna Sp. z o.o.
    1. System AI operuje wyłącznie na identyfikatorach technicznych B2B.
    2. Dane osobowe są filtrowane przed przekazaniem do LLM.
    """
    return odczytaj_plik_docs("rodo_compliance.md", domyslna)


# ==============================================================================
# MCP PROMPTS (Parametryzowane Szablony Procedur Biznesowych)
# ==============================================================================

@mcp.prompt(
    name="przygotuj_uzupelnienie_zapasow",
    title="Przygotuj uzupełnienie zapasów",
    description="Analizuje krytyczne stany i przygotowuje propozycję zamówienia do akceptacji.",
)
def prompt_uzupelnienie_zapasow(sklep_id: str) -> str:
    """Przygotowuje propozycję uzupełnienia krytycznych zapasów w wybranym sklepie."""
    return f"""
Przygotuj propozycję uzupełnienia krytycznych zapasów w sklepie: {sklep_id}.

1. Użyj narzędzia sprawdz_stany_magazynowe dla sklepu {sklep_id},
   ustawiając krytyczny_poziom=True.
2. Dla każdego zwróconego produktu oblicz brakującą ilość:
   zapas_bezpieczenstwa - ilosc.
3. Dla każdego produktu użyj porownaj_dostawcow, przekazując SKU produktu
   i obliczoną brakującą ilość.
4. Porównaj cenę, czas dostawy i minimum logistyczne. Jako domyślne kryterium
   rekomenduj najtańszą ofertę spełniającą minimum; przy remisie krótszy czas dostawy.
5. Jeśli minimum dostawcy wymaga zamówienia większej ilości, pokaż tę różnicę
   i poproś użytkownika o zgodę na zwiększenie ilości.
6. Przedstaw podsumowanie: sklep, produkt, stan obecny, zapas bezpieczeństwa,
   proponowana ilość, dostawca, koszt i czas dostawy.
7. Nie wywołuj generuj_zamowienie bez wyraźnej zgody użytkownika.
   Utworzenie projektu rezerwuje środki w budżecie.
8. Po uzyskaniu zgody pogrupuj pozycje według dostawcy. Narzędzie
   generuj_zamowienie obsługuje jednego dostawcę na jedno zamówienie,
   więc dla różnych dostawców utwórz osobne projekty.
9. Nie zatwierdzaj zamówień. Zatwierdzenie wymaga osobnej decyzji człowieka.

Jeśli nie ma krytycznych produktów albo brakuje danych do porównania,
powiedz to wprost i nie zgaduj.
"""


@mcp.prompt(
    name="porownaj_oferty_dostawcow",
    title="Porównaj oferty dostawców",
    description="Porównuje oferty dostawców dla produktu i wskazanej ilości.",
)
def prompt_porownaj_oferty_dostawcow(
    nazwa_produktu: str,
    ilosc: int,
) -> str:
    """Porównuje dostępne oferty bez tworzenia zamówienia."""
    return f"""
Porównaj oferty dostawców dla produktu „{nazwa_produktu}” w ilości {ilosc} sztuk.

Użyj narzędzia porownaj_dostawcow z podanym produktem i ilością.
Przedstaw osobno dla każdej oferty: dostawcę, cenę jednostkową, całkowitą
wartość, minimum logistyczne, brakującą liczbę sztuk do minimum i czas dostawy.

Wskaż najtańszą ofertę, która spełnia minimum logistyczne. Jeśli żadna
oferta go nie spełnia, wyjaśnij, ile sztuk brakuje do minimum w każdej ofercie.
Nie zmieniaj samodzielnie zamawianej ilości i nie twórz zamówienia.
Jeśli produkt jest niejednoznaczny lub nie ma ofert, poproś o doprecyzowanie
albo jasno poinformuj o braku ofert.
"""


@mcp.prompt(
    name="wyjasnij_krytyczne_stany",
    title="Wyjaśnij krytyczne stany",
    description="Pokazuje produkty poniżej zapasu bezpieczeństwa i wyjaśnia różnicę.",
)
def prompt_wyjasnij_krytyczne_stany(sklep_id: str) -> str:
    """Wyjaśnia, które produkty w sklepie wymagają uzupełnienia."""
    return f"""
Sprawdź krytyczne stany magazynowe w sklepie {sklep_id}.

Użyj narzędzia sprawdz_stany_magazynowe dla sklepu {sklep_id},
ustawiając krytyczny_poziom=True. Dla każdego zwróconego produktu podaj
nazwę, SKU, aktualną ilość i zapas bezpieczeństwa. Wyjaśnij różnicę
(ile sztuk brakuje do poziomu bezpieczeństwa).

Nie wyciągaj wniosków o przyczynach braku towaru, sprzedaży ani prognozach,
jeśli nie ma takich danych. Jeśli nie ma produktów poniżej poziomu
bezpieczeństwa, poinformuj o tym. Nie twórz zamówienia.
"""


# ==============================================================================
# MCP TOOLS (Narzędzia Biznesowe i Operacyjne)
# ==============================================================================

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
        sklep, blad = znajdz_sklep(conn, store_id)
        if blad:
            return blad

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
            sklep, blad = znajdz_sklep(conn, sklep_param)
            if blad:
                return blad

            real_sklep_id = sklep["sklep_id"]
            limit_budzetu = float(sklep["limit_budzetu"])

            # 2. Identyfikacja dostawcy
            dostawca_rec, blad = znajdz_dostawce(conn, dostawca_param)
            if blad:
                return blad

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

                oferta, blad = znajdz_oferte(conn, real_dostawca_id, term)
                if blad:
                    blad["dostawca"] = dostawca_nazwa
                    return blad

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

            nowy_limit = round(limit_budzetu - laczna_wartosc, 2)
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
                "UPDATE sklepy SET limit_budzetu = ROUND(limit_budzetu + ?, 2) WHERE sklep_id = ?",
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