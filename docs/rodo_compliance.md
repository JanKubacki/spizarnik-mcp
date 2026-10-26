# POLITYKA OCHRONY DANYCH OSOBOWYCH (RODO/GDPR) I COMPLIANCE
**Spiżarnia Bez Dna Sp. z o.o.**

---

### 1. ANONIMIZACJA I IZOLACJA DANYCH DLA LLM
* System Spiżarnik AI operuje wyłącznie na anonimowych identyfikatorach technicznych (`sklep_id: 'S1'`, `dostawca_id: 'D1'`, `sku: 'NAB-001'`).
* Zabrania się przesyłania do zewnętrznych modeli językowych nazwisk kierowników sklepów, prywatnych numerów telefonów i adresów e-mail.
* Wszystkie komunikaty przekazywane do modeli LLM podlegają automatycznemu filtrowaniu danych osobowych.

---

### 2. OBSŁUGA PRAWA DO USUNIĘCIA DANYCH (Art. 17 RODO)
* Baza danych SQLite zawiera wyłącznie dane operacyjne B2B i nie przechowuje danych osobowych osób fizycznych.
* Dzienniki systemowe wywołań narzędzi są audytowane i anonimizowane po 30 dniach.

---

### 3. OGRAICZENIA AUTONOMICZNEGO PROFILOWANIA
* System AI ma zakaz podejmowania decyzji oceniających pracę personelu sklepów lub automatycznego nakładania kar na dostawców.
* Decyzje finansowe i zatwierdzanie wniosków należą wyłącznie do uprawnionego człowieka (Human-in-the-loop).