# DIPLOMA

Desktop aplikace k diplomové práci zaměřená na řešení problému obchodního cestujícího (TSP/ATSP) nad mapovými i syntetickými daty.
Projekt obsahuje:
- GUI aplikaci v PyQt6 (`code/`)
- benchmark a vyhodnocení experimentů (`benchmarking/`)
- text diplomové práce a obrázky (`latex/`)

## Co to je

Tento repozitář slouží jako kompletní podklad k diplomové práci:
- implementace solverů pro více algoritmů (např. NN, 2-OPT, 3-OPT, SA, GA, ACO, LK, RSO, LKH)
- práce s různými metrikami vzdálenosti (geografické i maticové)
- mapová vizualizace trasy a import/export instancí
- podpora benchmarku a statistického porovnání výsledků

## Instalace a spuštění

Požadavky:
- Linux/macOS/Windows
- Python 3.10+

Postup (z kořene `DIPLOMA/`):

```bash
cd code
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install PyQt6 numpy requests tsplib95
python main.py
```

Poznámky:
- Pro routování přes OpenRouteService je vhodné nastavit `ORS_API_KEY` (volitelně i `ORS_BASE_URL`).
- Aplikace umí pracovat i s lokálním OSRM fallbackem (pokud běží na `localhost:5000`).

### Benchmarking grafy (volitelně)

```bash
cd benchmarking
pip install -r requirements-graphs.txt
python graphs.py
```

## Co projekt umí / co obsahuje (stručně)

- Interaktivní GUI pro načítání bodů, spouštění solverů a zobrazení výsledné trasy na mapě
- Více optimalizačních algoritmů pro TSP/ATSP a porovnání jejich výkonu
- Import/export instancí (TSP/GPX a související formáty podle implementovaných strategií)
- Nastavení routing profilů, API klíče, seedu solverů a dalších parametrů
- Nástroje pro benchmarking, generování grafů a statistické shrnutí výsledků

## Struktura repozitáře

- `code/` - hlavní aplikace a implementace solverů
- `benchmarking/` - skripty pro analýzu a vizualizaci benchmarku
- `latex/` - zdrojové soubory diplomové práce (kapitoly, obrázky, tabulky)
