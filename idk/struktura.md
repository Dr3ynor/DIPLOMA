# Úvod
**Cíl práce** – vysvětlit, že cílem je vývoj generátoru TSP instancí využívajícího moderní mapová API a vizualizační nástroje

**Motivace** – proč jsou klasické TSP datasety zastaralé a proč má smysl využít reálná geografická data

# Teoretická část
## 2.1 Problém obchodního cestujícího (TSP)

Formální definice problému

Typy TSP (symetrický, asymetrický, dynamický)

Matematická formulace (např. minimalizace součtu vzdáleností)

NP-úplnost a výpočetní složitost

## 2.2 Metody řešení TSP

**Přesné metody**: brute force, branch & bound, dynamic programming

**Heuristické metody**: nearest neighbor, 2-opt, 3-opt

**Metaheuristiky**: genetické algoritmy, simulované žíhání, mravenčí kolonie apod.

Stručné porovnání **výhod a nevýhod**

## 2.3 Datové sady TSP

Přehled existujících datasetů (TSPLIB, TSPLIB95)

Popis formátu .tsp, .opt.tour

Důvody, proč je potřeba vytvářet nové reálné instance (např. městská logistika, aktuální dopravní síť)

## 2.4 Geolokační a mapové služby

**Přehled možností:**

OpenStreetMap – komunitně tvořená otevřená mapa světa s volně dostupnými geografickými daty

OSRM (Open Source Routing Machine) – výpočet tras a vzdáleností

GraphHopper – plánování tras a navigaci

Mapy.cz API

# Analýza a návrh systému
## 3.1 Požadavky na systém

Funkční požadavky:

Vstup seznamu lokalit (města, souřadnice)

Výpočet matice vzdáleností pomocí mapového API

Export dat do formátu (CSV, JSON, TSPLIB)

Vizualizace bodů a tras

Nefunkční požadavky:

Open-source řešení bez nutnosti tokenu

Přenositelnost (Python, multiplatformní)

...

## 3.2 Návrh architektury

Blokové schéma systému (moduly:výpočet vzdáleností, generátor instancí, vizualizace)

Datový tok mezi moduly

Návrh struktury dat (např. DistanceMatrix, TSPInstance)

## 3.3 Návrh datového modelu

Popis formátu uložených dat (CSV, TSPLIB, JSON)

Popis atributů, jejich význam a validace

## 3.4 Volba technologií

Programovací jazyk: Python / Java ???

Knihovny: requests, ???

Mapové API: OSRM (lokálně provozované)

**Vizualizace**
OpenStreetMap

# Implementace
## 4.1 Implementace generátoru instancí

Vstupní data (seznam lokalit, region, způsob generování)

Funkce pro výpočet vzdáleností mezi všemi body pomocí OSRM API

Ukládání matice vzdáleností

## 4.2 Generování reálných a syntetických instancí

Generování podle reálných měst (např. okresní města, krajská města)

Náhodné generování souřadnic (syntetické instance)

Automatizované generování

## 4.3 Vizualizace

Implementace interaktivní mapy

Zobrazení uzlů (měst) a hran (tras)

Zobrazení nalezeného řešení (např. nejkratší trasa)

## 4.4 Export a kompatibilita

Export do TSPLIB formátu (pro testování s existujícími TSP solvery) - vybrat jednu variantu

Možnost ukládání do CSV a JSON

# Experimentální část
## 5.1 Kolekce vytvořených instancí

Popis vytvořených datasetů (počet uzlů, region, charakteristika)

Ukázky konkrétních instancí

## 5.2 Testování TSP řešení

Použití jednoduchých heuristik a metaheuristik (např. nearest neighbor, 2-opt)

Porovnání výsledků (délka trasy, čas výpočtu)

Vizualizace vybraných řešení

## 5.3 Porovnání s existujícími daty (např. TSPLIB)

Analýza podobnosti / rozdílů (distribuce vzdáleností, symetrie)

# Diskuze

Vyhodnocení úspěšnosti vytvořeného generátoru

Výhody a limity použitého přístupu

Možnosti rozšíření (např. zahrnutí dopravních dat, časových oken, dynamického TSP)

# Závěr

Shrnutí dosažených cílů

Zhodnocení přínosu práce

Možnosti budoucího vývoje (např. REST API, webová aplikace, integrace AI heuristik)

# Přílohy

Ukázkové instance TSP (.csv, .tsp)

Ukázky map a vizualizací

Zdrojové kódy (např. GitHub repozitář)