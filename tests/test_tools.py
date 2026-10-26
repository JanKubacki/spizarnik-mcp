"""
Zestaw testów automatycznych dla narzędzi MCP Spiżarnik AI.
Realizacja testów z arkusza testy_spizarnik.xlsx (Sekcje 2.x - 7.x).
"""

import os
import subprocess
import pytest
import server  # Wymaga importu funkcji z server.py

@pytest.fixture(autouse=True)
def reset_database():
    """Resetuje lokalną bazę SQLite do stanu początkowego z init_db.py przed każdym testem."""
    subprocess.run(["uv", "run", "python", "init_db.py"], check=True)

# ==============================================================================
# 2. sprawdz_stany_magazynowe
# ==============================================================================

def test_2_1_sprawdz_stany_wszystkie_S1():
    """2.1: Pokaż wszystkie stany magazynowe w sklepie S1."""
    res = server.sprawdz_stany_magazynowe(store_id="S1", krytyczny_poziom=False)
    assert len(res.get("produkty", [])) == 18

def test_2_2_sprawdz_stany_krytyczne_mokotow():
    """2.2: Które produkty w sklepie Mokotów są poniżej zapasu bezpieczeństwa?"""
    res = server.sprawdz_stany_magazynowe(store_id="Mokotów", krytyczny_poziom=True)
    skus = [p["sku"] for p in res.get("produkty", [])]
    # Oczekiwane 4 produkty: mleko (NAB-001), masło (NAB-003), pomidory (WAR-001), sok (NAP-002)
    assert len(skus) == 4
    assert set(skus) == {"NAB-001", "NAB-003", "WAR-001", "NAP-002"}

def test_2_3_sprawdz_stany_graniczne_kajzerki():
    """2.3: Kajzerki w Mokotowie mają stan 80/80 - nie powinny trafić na listę braków."""
    res = server.sprawdz_stany_magazynowe(store_id="Mokotów", krytyczny_poziom=True)
    skus = [p["sku"] for p in res.get("produkty", [])]
    assert "PIE-002" not in skus

def test_2_4_sprawdz_stany_braki_sklep_3():
    """2.4: Jakie są braki w sklepie Nr 3 Osiedle?"""
    res = server.sprawdz_stany_magazynowe(store_id="Sklep Nr 3 Osiedle", krytyczny_poziom=True)
    assert len(res.get("produkty", [])) == 12

def test_2_5_sprawdz_stany_nieistniejacy_sklep():
    """2.5: Pokaż stany w sklepie S9."""
    res = server.sprawdz_stany_magazynowe(store_id="S9")
    assert res.get("status") == "error"
    assert "S1" in res.get("dostepne_sklepy", [])

def test_2_6_sprawdz_stany_niejednoznaczny_sklep():
    """2.6: Pokaż stany w sklepie Sklep."""
    res = server.sprawdz_stany_magazynowe(store_id="Sklep")
    assert res.get("status") == "ambiguous"
    assert len(res.get("dopasowane_sklepy", [])) == 3

# ==============================================================================
# 3. porownaj_dostawcow
# ==============================================================================

def test_3_1_porownaj_dostawcow_minimum_logistyczne():
    """3.1: Porównaj dostawców dla 40 sztuk mleka 2%."""
    res = server.porownaj_dostawcow(nazwa_produktu="Mleko 2% 1 l", ilosc=40)
    oferty = res.get("oferty", {})
    assert oferty["D3"]["minimum_spelnione"] is False
    assert oferty["D1"]["minimum_spelnione"] is True
    assert res.get("rekomendacja") == "D1"

def test_3_2_porownaj_dostawcow_cena_a_czas():
    """3.2: Porównaj dostawców dla 100 sztuk mleka 2%."""
    res = server.porownaj_dostawcow(nazwa_produktu="NAB-001", ilosc=100)
    oferty = res.get("oferty", {})
    assert oferty["D3"]["wartosc"] == 255.00
    assert oferty["D1"]["wartosc"] == 285.00
    assert oferty["D3"]["minimum_spelnione"] is True

def test_3_3_porownaj_dostawcow_ser_gouda():
    """3.3: Porównaj dostawców dla 20 sztuk sera gouda."""
    res = server.porownaj_dostawcow(nazwa_produktu="Ser gouda plastry 150 g", ilosc=20)
    oferty = res.get("oferty", {})
    assert oferty["D1"]["wartosc"] == 90.00
    assert oferty["D3"]["wartosc"] == 94.00

def test_3_4_porownaj_dostawcow_jeden_dostawca():
    """3.4: Porównaj oferty na 30 bochenków chleba."""
    res = server.porownaj_dostawcow(nazwa_produktu="Chleb pszenny 500 g", ilosc=30)
    assert len(res.get("oferty", {})) == 1
    assert "D3" in res.get("oferty", {})

def test_3_5_porownaj_dostawcow_brak_w_katalogu():
    """3.5: Porównaj dostawców dla 10 opakowań kawy."""
    res = server.porownaj_dostawcow(nazwa_produktu="Kawa ziarnista", ilosc=10)
    assert res.get("status") == "error"

def test_3_6_porownaj_dostawcow_bledna_ilosc():
    """3.6: Porównaj dostawców dla -5 sztuk mleka."""
    res = server.porownaj_dostawcow(nazwa_produktu="NAB-001", ilosc=-5)
    assert res.get("status") == "error"

# ==============================================================================
# 4. generuj_zamowienie
# ==============================================================================

def test_4_1_generuj_zamowienie_sukces():
    """4.1: Utwórz projekt zamówienia dla S2 u MlekoHurt: 30 mleka i 12 masła."""
    pozycje = [{"sku": "NAB-001", "ilosc": 30}, {"sku": "NAB-003", "ilosc": 12}]
    res = server.generuj_zamowienie(sklep_id="S2", dostawca="MlekoHurt", pozycje=pozycje)
    assert res.get("status") == "projekt"
    assert res.get("zamowienie_id") == 5
    assert abs(res.get("wartosc", 0) - 153.90) < 0.01

def test_4_2_generuj_zamowienie_brak_minimum():
    """4.2: Zamów dla S1 u HurtoSfery 40 sztuk mleka 2%."""
    pozycje = [{"sku": "NAB-001", "ilosc": 40}]
    res = server.generuj_zamowienie(sklep_id="S1", dostawca="HurtoSfera", pozycje=pozycje)
    assert res.get("status") == "error"
    assert "minimum" in res.get("komunikat", "").lower()

def test_4_3_generuj_zamowienie_brak_produktu_u_dostawcy():
    """4.3: Zamów dla S1 u WarzywaExpress 24 sztuki mleka."""
    pozycje = [{"sku": "NAB-001", "ilosc": 24}]
    res = server.generuj_zamowienie(sklep_id="S1", dostawca="WarzywaExpress", pozycje=pozycje)
    assert res.get("status") == "error"

def test_4_4_generuj_zamowienie_przekroczony_budzet():
    """4.4: Zamów dla S3 u HurtoSfery 2000 butelek wody."""
    pozycje = [{"sku": "NAP-001", "ilosc": 2000}]
    res = server.generuj_zamowienie(sklep_id="S3", dostawca="HurtoSfera", pozycje=pozycje)
    assert res.get("status") == "error"
    assert "budżet" in res.get("komunikat", "").lower()

def test_4_5_generuj_zamowienie_budzet_uwzglednia_istniejace():
    """4.5: Zamów dla S3 u HurtoSfery 1400 butelek wody."""
    pozycje = [{"sku": "NAP-001", "ilosc": 1400}]
    res = server.generuj_zamowienie(sklep_id="S3", dostawca="HurtoSfera", pozycje=pozycje)
    assert res.get("status") == "error"

def test_4_6_generuj_zamowienie_niejednoznaczny_dostawca():
    """4.6: Utwórz zamówienie dla S1 u dostawcy Hurt na 96 sztuk mleka."""
    pozycje = [{"sku": "NAB-001", "ilosc": 96}]
    res = server.generuj_zamowienie(sklep_id="S1", dostawca="Hurt", pozycje=pozycje)
    assert res.get("status") == "ambiguous"

# ==============================================================================
# 5. zatwierdz_zamowienie, 6. rejestruj_dostawe, 7. anuluj_zamowienie
# ==============================================================================

def test_5_1_i_6_4_zatwierdz_i_dostarcz_zamowienie_5():
    """5.1 i 6.4: Tworzenie zamówienia #5, zatwierdzenie i rejestracja dostawy."""
    pozycje = [{"sku": "NAB-001", "ilosc": 30}, {"sku": "NAB-003", "ilosc": 12}]
    server.generuj_zamowienie(sklep_id="S2", dostawca="MlekoHurt", pozycje=pozycje)
    
    # 5.1 Zatwierdzenie
    res_z = server.zatwierdz_zamowienie(zamowienie_id=5)
    assert res_z.get("status") == "zatwierdzone"
    
    # 6.4 Rejestracja dostawy
    res_d = server.rejestruj_dostawe(zamowienie_id=5)
    assert res_d.get("status") == "dostarczone"

def test_5_2_zatwierdz_juz_zatwierdzone():
    """5.2: Zatwierdź zamówienie nr 2 (już zatwierdzone)."""
    res = server.zatwierdz_zamowienie(zamowienie_id=2)
    assert res.get("status") == "error"

def test_5_3_zatwierdz_dostarczone():
    """5.3: Zatwierdź zamówienie nr 1 (już dostarczone)."""
    res = server.zatwierdz_zamowienie(zamowienie_id=1)
    assert res.get("status") == "error"

def test_5_4_zatwierdz_nieistniejace():
    """5.4: Zatwierdź zamówienie nr 999."""
    res = server.zatwierdz_zamowienie(zamowienie_id=999)
    assert res.get("status") == "error"

def test_6_1_rejestruj_dostawe_sukces():
    """6.1: Zarejestruj dostawę do zamówienia nr 2."""
    res = server.rejestruj_dostawe(zamowienie_id=2)
    assert res.get("status") == "dostarczone"

def test_6_2_rejestruj_dostawe_powtorna():
    """6.2: Zarejestruj jeszcze raz dostawę do zamówienia nr 2."""
    server.rejestruj_dostawe(zamowienie_id=2)
    res_2 = server.rejestruj_dostawe(zamowienie_id=2)
    assert res_2.get("status") == "error"

def test_6_3_rejestruj_dostawe_projekt():
    """6.3: Zarejestruj dostawę do zamówienia nr 3 (status projekt)."""
    res = server.rejestruj_dostawe(zamowienie_id=3)
    assert res.get("status") == "error"

def test_7_1_anuluj_zamowienie_projekt_zwrot_budzetu():
    """7.1: Anuluj zamówienie nr 3 i sprawdź zwrot budżetu S1."""
    res = server.anuluj_zamowienie(zamowienie_id=3)
    assert res.get("status") == "anulowane"
    assert res.get("zwrocona_kwota") == 250.80

def test_7_2_anuluj_dostarczone():
    """7.2: Anuluj zamówienie nr 1 (dostarczone)."""
    res = server.anuluj_zamowienie(zamowienie_id=1)
    assert res.get("status") == "error"

def test_7_3_anuluj_juz_anulowane():
    """7.3: Anuluj zamówienie nr 4 (już anulowane)."""
    res = server.anuluj_zamowienie(zamowienie_id=4)
    assert res.get("status") == "error"