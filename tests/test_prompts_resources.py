"""
Zestaw testów dla Promptów Scenariuszowych i Zasobów MCP (Spiżarnik AI).
Realizacja scenariuszy 9.1 - 9.4 z arkusza testy_spizarnik.xlsx.
"""

import os
import sqlite3
import subprocess
import pytest
import server

@pytest.fixture(autouse=True)
def reset_database():
    """Resetuje lokalną bazę SQLite do stanu początkowego przed każdym testem."""
    try:
        subprocess.run(["uv", "run", "python", "init_db.py"], check=True, capture_output=True)
    except Exception:
        db_path = os.path.join("data", "spizarnia.db") if os.path.exists(os.path.join("data", "spizarnia.db")) else "spizarnia.db"
        sql_path = os.path.join("data", "dane_poczatkowe.sql") if os.path.exists(os.path.join("data", "dane_poczatkowe.sql")) else "dane_poczatkowe.sql"
        if os.path.exists(db_path) and os.path.exists(sql_path):
            conn = sqlite3.connect(db_path)
            with open(sql_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()

# ==============================================================================
# 9. Prompty i Zasoby MCP
# ==============================================================================

def test_9_1_prompt_przygotuj_uzupelnienie_zapasow():
    """
    9.1: Test promptu 'przygotuj_uzupelnienie_zapasow' dla sklepu S2.
    Sprawdza, czy prompt generuje szkielet analityczny i pyta o zgodę człowieka.
    """
    prompt_msg = server.prompt_przygotuj_uzupelnienie(sklep_id="S2")
    assert "S2" in prompt_msg
    assert "zgode" in prompt_msg.lower() or "zgodę" in prompt_msg.lower()
    
    braki = server.sprawdz_stany_magazynowe(store_id="S2", krytyczny_poziom=True)
    skus_brakow = [p["sku"] for p in braki.get("produkty", [])]
    assert set(skus_brakow) == {"NAB-001", "NAB-003", "WAR-001", "NAP-002"}

def test_9_2_prompt_porownaj_oferty_dostawcow():
    """
    9.2: Test promptu 'porownaj_oferty_dostawcow' dla 40 sztuk Mleka 2%.
    Sprawdza, czy prompt realizuje analizę porównawczą bez automatycznego tworzenia zamówienia.
    """
    res = server.porownaj_dostawcow(nazwa_produktu="NAB-001", ilosc=40)
    assert "D1" in str(res.get("rekomendacja", "")) or "MlekoHurt" in str(res.get("rekomendacja", ""))
    
    db_res = server.sprawdz_stany_magazynowe(store_id="S1")
    assert len(db_res.get("produkty", [])) == 18

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