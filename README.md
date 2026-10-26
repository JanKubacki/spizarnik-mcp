# Spiżarnik AI (`spizarnik-mcp`)

Serwer **MCP (Model Context Protocol)** dla fikcyjnej firmy **Spiżarnia Bez Dna Sp. z o.o.**, czyli sieci lokalnych sklepów spożywczych. Spiżarnik AI to asystent logistyki i zaopatrzenia: analizuje stany magazynowe, porównuje oferty dostawców i przygotowuje **projekty zamówień**, które zatwierdza człowiek (Human-in-the-loop).

Projekt zaliczeniowy z przedmiotu „Budowa i wykorzystanie systemów AI" (nr 224390).

> **Status:** prototyp edukacyjny. Działa lokalnie (transport stdio, baza SQLite).

---

## Spis treści

1. [Koncepcja](#1-koncepcja)
2. [Architektura](#2-architektura)
3. [Wymagania](#3-wymagania)
4. [Instalacja i uruchomienie krok po kroku](#4-instalacja-i-uruchomienie-krok-po-kroku)
5. [Specyfikacja MCP](#5-specyfikacja-mcp)
6. [Cykl życia zamówienia i nadzór ludzki](#6-cykl-życia-zamówienia-i-nadzór-ludzki)
7. [Model danych](#7-model-danych)
8. [Testy](#8-testy)
9. [Scenariusz demonstracyjny](#9-scenariusz-demonstracyjny)
10. [AI Governance i zgodność](#10-ai-governance-i-zgodność)
11. [Struktura repozytorium](#11-struktura-repozytorium)

---

## 1. Koncepcja

| Element | Opis |
|---|---|
| Firma | Spiżarnia Bez Dna Sp. z o.o., sieć sklepów spożywczych (handel detaliczny, logistyka) |
| Rola agenta AI | Asystent zaopatrzenia: analiza stanów, porównanie ofert dostawców, przygotowanie projektów zamówień |
| Agent | serwer MCP (to repozytorium) + klient (Claude Desktop) + model językowy (LLM) |
| Zasada nadrzędna | AI **proponuje**, człowiek **decyduje**. Każde zamówienie powstaje jako `projekt` |

Dane początkowe: 3 sklepy, 18 produktów, 3 dostawców (23 oferty) i 4 zamówienia testowe w różnych statusach.

## 2. Architektura

```text
┌──────────────────┐   stdio (JSON-RPC)   ┌─────────────────────┐   SQL    ┌──────────────────┐
│  Claude Desktop  │ ───────────────────► │  server.py (MCP)    │ ───────► │ data/spizarnia.db│
│  (klient + LLM)  │ ◄─────────────────── │  Tools/Resources/   │ ◄─────── │ (SQLite)         │
└──────────────────┘                      │  Prompts            │          └──────────────────┘
        ▲                                 └─────────┬───────────┘
        │ potwierdzenie wywołań                     │ odczyt
     CZŁOWIEK                                       ▼
   (nadzór ludzki)                          docs/*.md (regulamin, RODO)
```

- **Transport:** stdio (serwer uruchamiany jako proces potomny przez klienta).
- **SDK:** `mcp[cli]>=2.3.0`, klasa `MCPServer` (`from mcp.server.mcpserver import MCPServer`).
- **Baza:** SQLite, tworzona skryptem `init_db.py` ze `schemat.sql` i `dane_poczatkowe.sql`. Plik `*.db` jest w `.gitignore`.
- **Zapytania SQL są parametryzowane** (brak sklejania tekstu zapytań z danych wejściowych).

## 3. Wymagania

- Windows 10/11 (instrukcje poniżej dla PowerShell; na macOS/Linux analogicznie)
- Python **3.12** (`.python-version`); wystarczy, że zainstaluje go `uv`
- [`uv`](https://docs.astral.sh/uv/) – menedżer pakietów i środowisk
- [Claude Desktop](https://claude.com/download)
- Git

Instalacja `uv` (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 4. Instalacja i uruchomienie krok po kroku

```powershell
# 1. Pobranie repozytorium
git clone <ADRES_REPOZYTORIUM> spizarnik-mcp
cd spizarnik-mcp

# 2. Instalacja zależności (tworzy .venv na podstawie uv.lock)
uv sync

# 3. Utworzenie bazy danych (wykonaj też, aby ZRESETOWAĆ dane przed testami i demo)
uv run python init_db.py

# 4. (opcjonalnie) szybki test uruchomienia serwera w inspektorze MCP
uv run mcp dev server.py
```

Alternatywa bez `uv`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
```

Jeśli `init_db.py` zgłasza, że baza jest otwarta w innym programie, zamknij DB Browser oraz Claude Desktop (prawy przycisk na ikonie w zasobniku → *Exit*) i uruchom skrypt ponownie.

> `requirements.txt` jest generowany z `uv.lock` poleceniem
> `uv export --format requirements.txt --no-hashes --no-emit-project -o requirements.txt`.

## 5. Specyfikacja MCP

### Tools (7)

| Narzędzie | Opis | Zmienia dane? |
|---|---|---|
| `hello_spizarnik()` | Test połączenia z serwerem | nie |
| `sprawdz_stany_magazynowe(store_id, krytyczny_poziom=False)` | Stany sklepu (ID lub fragment nazwy, np. `S2`, `Mokotów`). Przy `krytyczny_poziom=True` tylko pozycje z `ilosc < zapas_bezpieczenstwa` | nie |
| `porownaj_dostawcow(nazwa_produktu, ilosc=1)` | Oferty dostawców (cena, wartość, minimum logistyczne, braki do minimum, czas dostawy) wraz z rekomendacją. Nie tworzy zamówienia | nie |
| `generuj_zamowienie(sklep_id, dostawca, pozycje)` | Tworzy **projekt** zamówienia u jednego dostawcy. Waliduje minima logistyczne i budżet, rezerwuje budżet | **tak** |
| `zatwierdz_zamowienie(zamowienie_id)` | `projekt` → `zatwierdzone` (narzędzie nadzoru ludzkiego) | **tak** |
| `anuluj_zamowienie(zamowienie_id)` | Anuluje zamówienie i zwraca kwotę do budżetu sklepu | **tak** |
| `rejestruj_dostawe(zamowienie_id)` | `zatwierdzone` → `dostarczone`, zwiększa stany magazynowe | **tak** |

Mechanizmy pomocnicze:

- **Smart Matching** (`znajdz_sklep`, `znajdz_dostawce`, `znajdz_oferte`): wyszukiwanie po ID, dokładnej nazwie lub fragmencie. Przy braku dopasowania serwer zwraca listę dostępnych opcji, a przy wielu dopasowaniach prosi o doprecyzowanie.
- `pozycje` w `generuj_zamowienie` mogą mieć postać listy `[{"sku": "NAB-001", "ilosc": 24}]` albo tekstu JSON.
- Walidacje: ilość musi być dodatnią liczbą całkowitą, minimum logistyczne dostawcy, limit budżetu sklepu.

### Resources (5)

| URI | Zawartość | Źródło |
|---|---|---|
| `spizarnik://sklepy` | Sklepy i ich pozostałe limity budżetowe | baza (JSON) |
| `spizarnik://produkty` | Katalog produktów (SKU, kategoria, cena, ważność) | baza (JSON) |
| `spizarnik://warunki-dostawcow` | Profile dostawców i oferty hurtowe | baza (JSON) |
| `spizarnik://regulamin` | Regulamin logistyki i AI Governance | `docs/regulamin_logistyki.md` |
| `spizarnik://rodo-compliance` | Polityka ochrony danych | `docs/rodo_compliance.md` |

### Prompts (3)

| Prompt | Parametry | Cel |
|---|---|---|
| `przygotuj_uzupelnienie_zapasow` | `sklep_id` | Analiza braków, porównanie dostawców, propozycja zamówienia. **Wymaga zgody użytkownika** przed `generuj_zamowienie` i zabrania zatwierdzania zamówień |
| `porownaj_oferty_dostawcow` | `nazwa_produktu`, `ilosc` | Porównanie ofert bez tworzenia zamówienia |
| `wyjasnij_krytyczne_stany` | `sklep_id` | Zestawienie produktów poniżej zapasu bezpieczeństwa, bez prognoz i zamówień |

## 6. Cykl życia zamówienia i nadzór ludzki

```text
generuj_zamowienie ──► projekt ──zatwierdz_zamowienie──► zatwierdzone ──rejestruj_dostawe──► dostarczone
                          │                                   │
                          └────────── anuluj_zamowienie ──────┴──► anulowane (zwrot środków do budżetu)
```

- Zamówienie utworzone przez AI ma zawsze status `projekt`.
- Utworzenie projektu **rezerwuje budżet** (zmniejsza `limit_budzetu`), a anulowanie go zwraca.
- `rejestruj_dostawe` działa tylko dla `zatwierdzone`, więc podwójne przyjęcie dostawy jest blokowane.
- Narzędzia są idempotentne: ponowne wywołanie zwraca komunikat, a nie zmienia danych.

**Jak egzekwowany jest nadzór ludzki w prototypie:** narzędzia `zatwierdz_zamowienie` i `anuluj_zamowienie` są technicznie dostępne dla modelu. Kontrolą są (1) potwierdzanie każdego wywołania narzędzia przez użytkownika w Claude Desktop oraz (2) instrukcje w promptach. To zabezpieczenie proceduralne, a nie techniczne. Docelowo: osobny kanał zatwierdzania poza LLM (np. panel/CLI z PIN-em) i tabela audytowa.

## 7. Model danych

| Tabela | Klucz | Opis |
|---|---|---|
| `sklepy` | `sklep_id` | Sklep i **budżet pozostały** (`limit_budzetu` maleje przy nowych projektach) |
| `produkty` | `sku` | Katalog: nazwa, kategoria, cena sprzedaży, okres ważności |
| `dostawcy` | (`dostawca_id`, `sku`) | Jeden wiersz = jeden produkt u jednego dostawcy (cena hurtowa, czas dostawy, minimum logistyczne) |
| `stany_magazynowe` | (`sklep_id`, `sku`) | Ilość i zapas bezpieczeństwa |
| `zamowienia` | `zamowienie_id` | Nagłówek: sklep, dostawca, status, wartość, data |
| `pozycje_zamowienia` | (`zamowienie_id`, `sku`) | Pozycje zamówienia |

Dostawcy w danych początkowych: **D1 MlekoHurt** (nabiał, 1 dzień, małe minima), **D2 WarzywaExpress** (warzywa i owoce, 1 dzień), **D3 HurtoSfera** (hurt ogólny, taniej, ale zwykle 3 dni i duże minima).

Reset do stanu początkowego: `uv run python init_db.py`.

## 8. Testy

```powershell
uv run python init_db.py     # opcjonalnie; testy resetują bazę same przed każdym testem
uv run pytest -v
```

| Plik | Zakres |
|---|---|
| `tests/test_tools.py` | Narzędzia: stany, porównanie dostawców, generowanie/zatwierdzanie/anulowanie zamówień, rejestracja dostaw |
| `tests/test_prompts_resources.py` | Prompty i zasoby MCP, w tym regresja braku zduplikowanych definicji |
| `tests/test_red_teaming.py` | Odporność: brak narzędzi do edycji stanów, usuwania danych i wykonywania dowolnego SQL; reguła Human-in-the-loop |

Fixture `reset_database` przed każdym testem odtwarza bazę poleceniem `uv run python init_db.py`. Uruchamiaj `pytest` z katalogu głównego repozytorium.

## 9. Scenariusz demonstracyjny

Przed demo wykonaj `uv run python init_db.py` i zrestartuj Claude Desktop.

1. **Krytyczne stany:** „Jakie produkty w sklepie Mokotów są poniżej zapasu bezpieczeństwa?" Oczekiwane: NAB-001 (0/30), NAB-003 (8/12), WAR-001 (6/12), NAP-002 (4/10).
2. **Prompt** `przygotuj_uzupelnienie_zapasow` dla `S2`.
3. **Porównanie dostawców** dla brakujących produktów.
4. **Projekt zamówienia:** `generuj_zamowienie` po wyraźnej zgodzie użytkownika. Powstaje zamówienie w statusie `projekt`.
5. **Zatwierdzenie przez człowieka:** `zatwierdz_zamowienie`.
6. **Przyjęcie dostawy:** `rejestruj_dostawe`. Stany magazynowe rosną.
7. **Zasób** `spizarnik://regulamin`: omówienie zasad nadzoru ludzkiego.

Przypadki negatywne do pokazania:

| Działanie | Oczekiwany wynik |
|---|---|
| `generuj_zamowienie`: S2, D1, NAB-003, ilość 4 | `ODRZUCONO` (minimum logistyczne: 10) |
| `generuj_zamowienie`: S3, D3, NAP-001 × 480 | `ODRZUCONO` (przekroczony budżet) |
| `rejestruj_dostawe` na zamówieniach #1, #3, #4 | błąd (odpowiednio: już dostarczone, projekt, anulowane) |
| `anuluj_zamowienie(3)` | S1 wraca do budżetu 8000,00 zł |

## 10. AI Governance i zgodność

Dokumenty w katalogu `docs/` są udostępniane modelowi jako zasoby MCP:

- [`docs/regulamin_logistyki.md`](docs/regulamin_logistyki.md): nadzór ludzki, limity budżetowe, minima logistyczne,
- [`docs/rodo_compliance.md`](docs/rodo_compliance.md): ochrona danych osobowych.

## 11. Struktura repozytorium

```text
spizarnik-mcp/
├── server.py                  # serwer MCP: tools, resources, prompts
├── init_db.py                 # budowa/reset bazy SQLite
├── pyproject.toml             # zależności i konfiguracja pytest
├── uv.lock
├── requirements.txt           # eksport z uv.lock
├── .python-version            # 3.12
├── data/
│   ├── schemat.sql            # struktura bazy
│   └── dane_poczatkowe.sql    # dane testowe i demo
├── docs/
│   ├── regulamin_logistyki.md # zasób spizarnik://regulamin
│   └── rodo_compliance.md     # zasób spizarnik://rodo-compliance
├── config/
│   └── claude_desktop_config.json.example
├── tests/
│   ├── test_tools.py
│   ├── test_prompts_resources.py
│   └── test_red_teaming.py
└── src/spizarnik_mcp/         # pozostałość po szablonie uv (do usunięcia)
```