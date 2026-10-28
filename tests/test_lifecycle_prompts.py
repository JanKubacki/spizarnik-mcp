"""Tests for the MCP prompts that guide order lifecycle operations."""

import server


def test_approval_prompt_requires_explicit_confirmation_and_accurate_effect():
    prompt = server.prompt_zatwierdz_projekt_zamowienia(zamowienie_id=17)

    assert "zatwierdz_zamowienie(zamowienie_id=17)" in prompt
    assert "jednoznacznym potwierdzeniu" in prompt
    assert "nie twierdź, że wysłało" in prompt
    assert "status z „projekt”" in prompt


def test_cancellation_prompt_is_conservative_for_approved_orders():
    prompt = server.prompt_anuluj_projekt_zamowienia(zamowienie_id=23)

    assert "anuluj_zamowienie(zamowienie_id=23)" in prompt
    assert "Nie anuluj zamówienia o statusie" in prompt
    assert "zarezerwowana kwota wróci do budżetu" in prompt
    assert "status jest nieznany" in prompt


def test_delivery_prompt_requires_complete_physical_receipt():
    prompt = server.prompt_zarejestruj_otrzymana_dostawe(zamowienie_id=31)

    assert "rejestruj_dostawe(" in prompt
    assert "zamowienie_id=31" in prompt
    assert "dostawa fizycznie dotarła" in prompt
    assert "dostaw częściowych" in prompt
    assert "Nie ponawiaj wywołania po sukcesie" in prompt


def test_connection_prompt_only_calls_health_check():
    prompt = server.prompt_sprawdz_polaczenie_spizarnika()

    assert "wyłącznie narzędzie hello_spizarnik" in prompt
    assert "Nie uruchamiaj narzędzi biznesowych" in prompt
    assert "wszystkie" in prompt
