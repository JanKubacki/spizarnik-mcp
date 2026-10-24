-- 1. Czyszczenie (kolejność ma znaczenie ze względu na klucze obce)
DELETE FROM pozycje_zamowienia;
DELETE FROM zamowienia;
DELETE FROM dostawcy;
DELETE FROM stany_magazynowe;
DELETE FROM produkty;
DELETE FROM sklepy;
DELETE FROM sqlite_sequence WHERE name = 'zamowienia';

-- 2. Sklepy (limity budżetu miesięczne, przeskalowane do 18 produktów)
INSERT INTO sklepy (sklep_id, nazwa, limit_budzetu) VALUES
('S1', 'Sklep Nr 1 Centrum', 8000),
('S2', 'Sklep Nr 2 Mokotów', 6000),
('S3', 'Sklep Nr 3 Osiedle', 2000);

-- 3. Produkty
INSERT INTO produkty (sku, nazwa, kategoria, cena_sprzedazy, okres_waznosci_dni) VALUES
('NAB-001', 'Mleko 2% 1 l',               'nabiał',           3.99,   10),
('NAB-002', 'Jogurt naturalny 400 g',     'nabiał',           3.49,   21),
('NAB-003', 'Masło 82% 200 g',            'nabiał',           7.99,   60),
('NAB-004', 'Ser gouda plastry 150 g',    'nabiał',           6.49,   30),
('NAB-005', 'Śmietana 18% 400 g',         'nabiał',           4.99,   14),
('PIE-001', 'Chleb pszenny 500 g',        'pieczywo',         5.49,    3),
('PIE-002', 'Bułka kajzerka',             'pieczywo',         0.79,    1),
('WAR-001', 'Pomidory 1 kg',              'warzywa i owoce',  9.99,    7),
('WAR-002', 'Ogórki 1 kg',                'warzywa i owoce',  7.99,    7),
('WAR-003', 'Ziemniaki 2 kg',             'warzywa i owoce',  6.99,   60),
('WAR-004', 'Jabłka 1 kg',                'warzywa i owoce',  4.99,   30),
('WAR-005', 'Banany 1 kg',                'warzywa i owoce',  6.49,    6),
('SUC-001', 'Makaron świderki 500 g',     'artykuły suche',   4.49,  730),
('SUC-002', 'Ryż biały 1 kg',             'artykuły suche',   6.99,  730),
('SUC-003', 'Mąka pszenna 1 kg',          'artykuły suche',   3.79,  365),
('SUC-004', 'Cukier biały 1 kg',          'artykuły suche',   4.29, 1095),
('NAP-001', 'Woda mineralna 1,5 l',       'napoje',           1.99,  365),
('NAP-002', 'Sok pomarańczowy 1 l',       'napoje',           6.99,  180);

-- 4. Dostawcy (jeden wiersz = jeden produkt u jednego dostawcy)
--    D1 MlekoHurt: nabiał, szybko, małe minima
--    D2 WarzywaExpress: warzywa i owoce, szybko
--    D3 HurtoSfera: hurtownia ogólna, często taniej, ale wolniej i z dużymi minimami
INSERT INTO dostawcy (dostawca_id, nazwa, sku, cena_hurtowa, czas_dostawy_dni, minimum_logistyczne) VALUES
('D1', 'MlekoHurt',      'NAB-001', 2.85, 1,  24),
('D1', 'MlekoHurt',      'NAB-002', 2.40, 1,  12),
('D1', 'MlekoHurt',      'NAB-003', 5.70, 1,  10),
('D1', 'MlekoHurt',      'NAB-004', 4.50, 1,  10),
('D1', 'MlekoHurt',      'NAB-005', 3.40, 1,  12),
('D2', 'WarzywaExpress', 'WAR-001', 6.80, 1,  10),
('D2', 'WarzywaExpress', 'WAR-002', 5.20, 1,  10),
('D2', 'WarzywaExpress', 'WAR-003', 4.10, 1,  10),
('D2', 'WarzywaExpress', 'WAR-004', 2.90, 1,  20),
('D2', 'WarzywaExpress', 'WAR-005', 4.30, 1,  10),
('D3', 'HurtoSfera',     'NAB-001', 2.55, 3,  96),
('D3', 'HurtoSfera',     'NAB-003', 5.40, 3,  40),
('D3', 'HurtoSfera',     'NAB-004', 4.70, 3,  20),
('D3', 'HurtoSfera',     'PIE-001', 3.40, 1,  20),
('D3', 'HurtoSfera',     'PIE-002', 0.42, 1, 100),
('D3', 'HurtoSfera',     'WAR-001', 6.20, 3,  30),
('D3', 'HurtoSfera',     'WAR-004', 2.70, 3,  50),
('D3', 'HurtoSfera',     'SUC-001', 2.90, 3,  24),
('D3', 'HurtoSfera',     'SUC-002', 4.60, 3,  20),
('D3', 'HurtoSfera',     'SUC-003', 2.40, 3,  20),
('D3', 'HurtoSfera',     'SUC-004', 2.95, 3,  20),
('D3', 'HurtoSfera',     'NAP-001', 1.05, 3,  48),
('D3', 'HurtoSfera',     'NAP-002', 4.60, 3,  12);

-- 5. Stany magazynowe (sklep, produkt, ilość, zapas bezpieczeństwa)
--    S1: duży sklep, prawie wszystko w normie
--    S2: kilka braków, całkowity brak mleka, nadmiar jogurtu i bananów
--    S3: mały sklep, dużo braków, prawie wyczerpany budżet
INSERT INTO stany_magazynowe (sklep_id, sku, ilosc, zapas_bezpieczenstwa) VALUES
('S1', 'NAB-001',  18,  40),
('S1', 'NAB-002',  35,  20),
('S1', 'NAB-003',  25,  15),
('S1', 'NAB-004',  30,  15),
('S1', 'NAB-005',  22,  12),
('S1', 'PIE-001',  12,  30),
('S1', 'PIE-002', 150, 100),
('S1', 'WAR-001',  28,  15),
('S1', 'WAR-002',  20,  12),
('S1', 'WAR-003',  40,  20),
('S1', 'WAR-004',  45,  25),
('S1', 'WAR-005',  30,  20),
('S1', 'SUC-001',  60,  30),
('S1', 'SUC-002',  40,  20),
('S1', 'SUC-003',  35,  20),
('S1', 'SUC-004',  50,  25),
('S1', 'NAP-001', 120,  60),
('S1', 'NAP-002',  30,  15),

('S2', 'NAB-001',   0,  30),
('S2', 'NAB-002',  90,  15),
('S2', 'NAB-003',   8,  12),
('S2', 'NAB-004',  20,  10),
('S2', 'NAB-005',  15,  10),
('S2', 'PIE-001',  25,  20),
('S2', 'PIE-002',  80,  80),
('S2', 'WAR-001',   6,  12),
('S2', 'WAR-002',  14,  10),
('S2', 'WAR-003',  30,  15),
('S2', 'WAR-004',  35,  20),
('S2', 'WAR-005',  60,  12),
('S2', 'SUC-001',  40,  20),
('S2', 'SUC-002',  25,  15),
('S2', 'SUC-003',  20,  15),
('S2', 'SUC-004',  30,  15),
('S2', 'NAP-001',  90,  40),
('S2', 'NAP-002',   4,  10),

('S3', 'NAB-001',   5,  20),
('S3', 'NAB-002',   6,  10),
('S3', 'NAB-003',   3,   8),
('S3', 'NAB-004',  10,   8),
('S3', 'NAB-005',   2,   6),
('S3', 'PIE-001',   4,  15),
('S3', 'PIE-002',  30,  50),
('S3', 'WAR-001',   3,   8),
('S3', 'WAR-002',  10,   6),
('S3', 'WAR-003',  12,  10),
('S3', 'WAR-004',   8,  12),
('S3', 'WAR-005',   5,   8),
('S3', 'SUC-001',  15,  10),
('S3', 'SUC-002',   6,  10),
('S3', 'SUC-003',   9,   8),
('S3', 'SUC-004',   4,   8),
('S3', 'NAP-001',  20,  30),
('S3', 'NAP-002',   7,   5);

-- 6. Zamówienia (daty liczone od bieżącego miesiąca, żeby budżety
--    zawsze dotyczyły miesiąca, w którym uruchamiasz skrypt)
--    1: S3, dostarczone   -> test podwójnego przyjęcia dostawy
--    2: S2, zatwierdzone  -> do demo rejestruj_dostawe
--    3: S1, projekt       -> czeka na zatwierdzenie przez człowieka
--    4: S1, anulowane     -> nie powinno liczyć się do budżetu
INSERT INTO zamowienia (zamowienie_id, sklep_id, dostawca_id, status, wartosc, data_utworzenia) VALUES
(1, 'S3', 'D3', 'dostarczone',  1674.20, datetime('now', 'start of month', '+8 hours')),
(2, 'S2', 'D2', 'zatwierdzone',  308.00, datetime('now', 'start of month', '+9 hours')),
(3, 'S1', 'D1', 'projekt',       250.80, datetime('now', 'start of month', '+10 hours')),
(4, 'S1', 'D3', 'anulowane',     136.00, datetime('now', 'start of month', '+11 hours'));

-- 7. Pozycje zamówień (wartości zamówień = suma ilość x cena)
INSERT INTO pozycje_zamowienia (zamowienie_id, sku, ilosc, cena_jednostkowa) VALUES
(1, 'SUC-001',  48, 2.90),
(1, 'SUC-002',  40, 4.60),
(1, 'NAP-001', 480, 1.05),
(1, 'NAP-002', 120, 4.60),
(1, 'SUC-004', 100, 2.95),
(2, 'WAR-001',  30, 6.80),
(2, 'WAR-002',  20, 5.20),
(3, 'NAB-001',  48, 2.85),
(3, 'NAB-003',  20, 5.70),
(4, 'PIE-001',  40, 3.40);