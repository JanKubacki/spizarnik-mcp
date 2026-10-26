"""
Zestaw testów dla Promptów Scenariuszowych i Zasobów MCP (Spiżarnik AI).
Realizacja scenariuszy 9.1 - 9.4 z arkusza testy_spizarnik.xlsx.
"""
import json
from pathlib import Path
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
    """9.1: Prompt dla S2 zawiera sklep, wymóg zgody i zakaz zatwierdzania."""
    prompt_msg = server.prompt_uzupelnienie_zapasow(sklep_id="S2")
    assert "S2" in prompt_msg
    assert "zgod" in prompt_msg.lower()
    assert "sprawdz_stany_magazynowe" in prompt_msg
    assert "Nie zatwierdzaj" in prompt_msg

    braki = server.sprawdz_stany_magazynowe(store_id="S2", krytyczny_poziom=True)
    skus_brakow = [p["sku"] for p in braki.get("produkty", [])]
    assert set(skus_brakow) == {"NAB-001", "NAB-003", "WAR-001", "NAP-002"}


def test_9_2_prompt_porownaj_oferty_dostawcow():
    """9.2: Prompt porównania nie tworzy zamówienia; narzędzie rekomenduje D1."""
    prompt_msg = server.prompt_porownaj_oferty_dostawcow(
        nazwa_produktu="Mleko 2% 1 l", ilosc=40
    )
    assert "porownaj_dostawcow" in prompt_msg
    assert "nie twórz zamówienia" in prompt_msg.lower()

    res = server.porownaj_dostawcow(nazwa_produktu="NAB-001", ilosc=40)
    assert "D1" in str(res.get("rekomendacja", "")) or "MlekoHurt" in str(res.get("rekomendacja", ""))


def test_9_3_prompt_wyjasnij_krytyczne_stany_S3():
    """9.3: Prompt istnieje i zwraca dokładnie 12 braków dla S3."""
    prompt_msg = server.prompt_wyjasnij_krytyczne_stany(sklep_id="S3")
    assert "S3" in prompt_msg
    assert "Nie twórz zamówienia" in prompt_msg

    res = server.sprawdz_stany_magazynowe(store_id="S3", krytyczny_poziom=True)
    assert len(res.get("produkty", [])) == 12


def test_9_4_zasob_regulamin_zgodny_z_plikiem_docs():
    """9.4: Zasób spizarnik://regulamin zwraca treść pliku docs/regulamin_logistyki.md."""
    tresc = server.regulamin_resource()
    plik = (Path(server.DOCS_PATH) / "regulamin_logistyki.md").read_text(encoding="utf-8")
    assert tresc == plik
    assert "REGULAMIN LOGISTYKI" in tresc
    assert "`projekt`" in tresc
    assert "zatwierdz_zamowienie" in tresc


def test_9_5_zasob_sklepy_json_z_bazy():
    """9.5: Zasób spizarnik://sklepy zwraca 3 sklepy z bazy."""
    dane = json.loads(server.lista_sklepow_resource())
    assert dane["liczba_sklepow"] == 3
    assert {s["sklep_id"] for s in dane["sklepy"]} == {"S1", "S2", "S3"}


def test_9_6_brak_zduplikowanych_definicji_w_server_py():
    """9.6: Regresja - każda funkcja promptu/zasobu zdefiniowana tylko raz."""
    import re
    zrodlo = (Path(server.__file__)).read_text(encoding="utf-8")
    nazwy = re.findall(r"^def (prompt_\w+|\w+_resource)\(", zrodlo, flags=re.M)
    assert len(nazwy) == len(set(nazwy)), f"Duplikaty: {nazwy}"
    assert "spizarnik://lista_sklepow" not in zrodlo
    assert "spizarnik://regulamin_logistyki" not in zrodlo