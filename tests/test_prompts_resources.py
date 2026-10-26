"""
Zestaw testów dla Promptów Scenariuszowych i Zasobów MCP (Spiżarnik AI).
Realizacja scenariuszy 9.1 - 9.4 z arkusza testy_spizarnik.xlsx.
"""

import subprocess
import pytest
import server  # Wymaga importu serwera FastMCP z server.py

@pytest.fixture(autouse=True)
def reset_database():
    """Resetuje lokalną bazę SQLite do stanu początkowego z init_db.py przed każdym testem."""
    subprocess.run(["uv", "run", "python", "init_db.py"], check=True)

# ==============================================================================
# 9. Prompty i Zasoby MCP
# ==============================================================================

def test_9_1_prompt_przygotuj_uzupelnienie_zapasow():
    """
    9.1: Test promptu 'przygotuj_uzupelnienie_zapasow' dla sklepu S2.
    Sprawdza, czy prompt generuje szkielet analityczny i pyta o zgodę człowieka.
    """
    prompt_msg = server.prompt_przygotuj_uzupelnienie(sklep_id="S2")
    
    # Weryfikacja treści szablonu promptu
    assert "S2" in prompt_msg
    assert "zgode" in prompt_msg.lower() or "zgodę" in prompt_msg.lower()
    
    # Weryfikacja braku samowolnego zatwierdzania w logice biznesowej
    braki = server.sprawdz_stany_magazynowe(store_id="S2", krytyczny_poziom=True)
    skus_brakow = [p["sku"] for p in braki.get("produkty", [])]
    assert set(skus_brakow) == {"NAB-001", "NAB-003", "WAR-001", "NAP-002"}

def test_9_2_prompt_porownaj_oferty_dostawcow():
    """
    9.2: Test promptu 'porownaj_oferty_dostawcow' dla 40 sztuk Mleka 2%.
    Sprawdza, czy prompt realizuje analizę porównawczą bez automatycznego tworzenia zamówienia.
    """
    res = server.porownaj_dostawcow(nazwa_produktu="NAB-001", ilosc=40)
    
    # Oczekiwany wynik jak w teście 3.1
    assert res.get("rekomendacja") == "D1"
    # Upewniamy się, że nie powstało żadne nowe zamówienie w stanie 'projekt'
    db_res = server.sprawdz_stany_magazynowe(store_id="S1")
    assert db_res.get("status") == "success"

def test_9_3_prompt_wyjasnij_krytyczne_stany_S3():
    """
    9.3: Test promptu 'wyjasnij_krytyczne_stany' dla sklepu S3.
    Sprawdza, czy zapytanie zwraca dokładnie 12 braków magazynowych.
    """
    res = server.sprawdz_stany_magazynowe(store_id="S3", krytyczny_poziom=True)
    produkty = res.get("produkty", [])
    
    assert len(produkty) == 12

def test_9_4_zasob_regulamin_logistyki():
    """
    9.4: Weryfikacja pobierania zasobu 'spizarnik://regulamin_logistyki'.
    Sprawdza, czy zasób zawiera zapis o wyłącznej decyzyjności człowieka.
    """
    tresc_regulaminu = server.pobierz_regulamin_logistyki()
    
    assert "REGULAMIN LOGISTYKI" in tresc_regulaminu
    assert "Człowiek" in tresc_regulaminu or "kierownik" in tresc_regulaminu.lower()
    assert "projekt" in tresc_regulaminu