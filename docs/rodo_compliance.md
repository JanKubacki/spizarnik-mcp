# POLITYKA OCHRONY DANYCH OSOBOWYCH (RODO/GDPR) I COMPLIANCE
**Spiżarnia Bez Dna Sp. z o.o.**

---

### 1. ANONIMIZACJA I IZOLACJA DANYCH DLA LLM
* System Spiżarnik AI operuje wyłącznie na anonimowych identyfikatorach technicznych (`sklep_id: 'S1'`, `dostawca_id: 'D1'`, `sku: 'NAB-001'`)[cite: 2, 28].
* Zabrania się przesyłania do zewnętrznych modeli językowych nazwisk kierowników sklepów, prywatnych numerów telefonów i adresów e-mail[cite: 9].
* Wszystkie komunikaty przekazywane do modeli LLM podlegają automatycznemu filtrowaniu danych osobowych[cite: 9].

---

### 2. OBSŁUGA PRAWA DO USUNIĘCIA DANYCH (Art. 17 RODO)
* Baza danych SQLite zawiera wyłącznie dane operacyjne B2B i nie przechowuje danych osobowych osób fizycznych[cite: 9, 28].
* Dzienniki systemowe wywołań narzędzi są audytowane i anonimizowane po 30 dniach[cite: 9].

---

### 3. OGRAICZENIA AUTONOMICZNEGO PROFILOWANIA
* System AI ma zakaz podejmowania decyzji oceniających pracę personelu sklepów lub automatycznego nakładania kar na dostawców[cite: 9].
* Decyzje finansowe i zatwierdzanie wniosków należą wyłącznie do uprawnionego człowieka (Human-in-the-loop)[cite: 1, 2, 9].