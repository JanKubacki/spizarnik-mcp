BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "dostawcy" (
	"dostawca_id"	TEXT NOT NULL,
	"nazwa"	TEXT NOT NULL,
	"sku"	TEXT NOT NULL,
	"cena_hurtowa"	REAL NOT NULL CHECK("cena_hurtowa" > 0),
	"czas_dostawy_dni"	INTEGER CHECK("czas_dostawy_dni" > 0),
	"minimum_logistyczne"	INTEGER NOT NULL CHECK("minimum_logistyczne" > 0),
	PRIMARY KEY("dostawca_id","sku"),
	CONSTRAINT "fku_dostawcy_produkty" FOREIGN KEY("sku") REFERENCES "produkty"("sku")
);
CREATE TABLE IF NOT EXISTS "pozycje_zamowienia" (
	"zamowienie_id"	INTEGER NOT NULL,
	"sku"	TEXT NOT NULL,
	"ilosc"	INTEGER NOT NULL CHECK("ilosc" > 0),
	"cena_jednostkowa"	REAL NOT NULL CHECK("cena_jednostkowa" > 0),
	PRIMARY KEY("zamowienie_id","sku"),
	CONSTRAINT "fk_sku" FOREIGN KEY("sku") REFERENCES "produkty"("sku"),
	CONSTRAINT "fk_zamowienia_id" FOREIGN KEY("zamowienie_id") REFERENCES "zamowienia"("zamowienie_id")
);
CREATE TABLE IF NOT EXISTS "produkty" (
	"sku"	TEXT NOT NULL,
	"nazwa"	TEXT NOT NULL,
	"kategoria"	TEXT NOT NULL,
	"cena_sprzedazy"	REAL NOT NULL CHECK("cena_sprzedazy" > 0),
	"okres_waznosci_dni"	INTEGER NOT NULL CHECK("okres_waznosci_dni" > 0),
	PRIMARY KEY("sku")
);
CREATE TABLE IF NOT EXISTS "sklepy" (
	"sklep_id"	TEXT NOT NULL,
	"nazwa"	TEXT NOT NULL,
	"limit_budzetu"	REAL NOT NULL CHECK("limit_budzetu" >= 0),
	PRIMARY KEY("sklep_id")
);
CREATE TABLE IF NOT EXISTS "stany_magazynowe" (
	"sklep_id"	TEXT NOT NULL,
	"sku"	TEXT NOT NULL,
	"ilosc"	INTEGER NOT NULL CHECK("ilosc" >= 0),
	"zapas_bezpieczenstwa"	INTEGER NOT NULL,
	PRIMARY KEY("sklep_id","sku"),
	CONSTRAINT "fk_sklep_id" FOREIGN KEY("sklep_id") REFERENCES "sklepy"("sklep_id"),
	CONSTRAINT "fk_sku" FOREIGN KEY("sku") REFERENCES "produkty"("sku")
);
CREATE TABLE IF NOT EXISTS "zamowienia" (
	"zamowienie_id"	INTEGER,
	"sklep_id"	TEXT NOT NULL,
	"dostawca_id"	TEXT NOT NULL,
	"status"	TEXT NOT NULL DEFAULT 'projekt' CHECK("status" IN ('projekt', 'zatwierdzone', 'dostarczone', 'anulowane')),
	"wartosc"	REAL NOT NULL CHECK("wartosc" >= 0),
	"data_utworzenia"	TEXT NOT NULL DEFAULT (datetime('now')),
	PRIMARY KEY("zamowienie_id" AUTOINCREMENT),
	CONSTRAINT "fk_zamowienia_sklepy" FOREIGN KEY("sklep_id") REFERENCES "sklepy"("sklep_id")
);
COMMIT;
