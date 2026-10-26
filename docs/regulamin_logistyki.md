# REGULAMIN LOGISTYKI I AI GOVERNANCE
**Spiżarnia Bez Dna Sp. z o.o.**

---

### 1. PROCEDURA NADZORU LUDZKIEGO (EU AI Act - Human-in-the-loop)
* Wszystkie propozycje zamówień wygenerowane przez system Spiżarnik AI rejestrowane są w bazie danych ze statusem **`projekt`**.
* System AI nie posiada uprawnień do samodzielnego zatwierdzania i przekazywania zamówień do hurtowni.
* Przekazanie zamówienia do realizacji wymaga bezwzględnej akceptacji przez operatora (wywołanie narzędzia `zatwierdz_zamowienie`).

---

### 2. LIMIT PRZEKROCZEŃ BUDŻETOWYCH (FinOps)
* Wygenerowanie projektu zamówienia automatycznie rezerwuje środki finansowe i pomniejsza wartość `limit_budzetu` danego sklepu.
* System blokuje tworzenie projektów zamówień przekraczających dostępny limit budżetowy.
* Zarezerwowany budżet uwalniany jest wyłącznie po wywołaniu akcji `anuluj_zamowienie`.

---

### 3. MINIMA LOGISTYCZNE I REZERWY BEZPIECZEŃSTWA (Supply Chain)
* Zamówienia poniżej wartości `minimum_logistyczne` określonej przez dostawcę są odrzucane przez walidator.
* Uzupełnienie zapasów jest rekomendowane w sytuacji, gdy ilość towaru spada poniżej wskaźnika `zapas_bezpieczenstwa`.