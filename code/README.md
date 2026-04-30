# DIPLOMA

## CZ

Desktop aplikace k diplomové práci zaměřená na řešení problému obchodního cestujícího (TSP/ATSP) nad mapovými i syntetickými daty.

Projekt obsahuje:
- GUI aplikaci v PyQt6 (`code/`)
- benchmarking a vyhodnocení experimentů (`benchmarking/`)
- text diplomové práce a obrázky (`latex/`)

### Co to je

Tento repozitář slouží jako kompletní podklad k diplomové práci:
- implementace solverů pro více algoritmů (např. NN, 2-OPT, 3-OPT, SA, GA, ACO, LK, RSO, LKH)
- práce s různými metrikami vzdálenosti (geografické i maticové)
- mapová vizualizace trasy a import/export instancí
- podpora benchmarku a statistického porovnání výsledků

### Instalace a spuštění

Požadavky:
- Linux/macOS/Windows
- Python 3.10+

Postup (z kořene `DIPLOMA/`):

```bash
cd code
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Poznámky:
- Pro routování přes OpenRouteService je vhodné nastavit `ORS_API_KEY` (volitelně i `ORS_BASE_URL`).
- Aplikace umí pracovat i s lokálním OSRM fallbackem (pokud běží na `localhost:5000`).

#### Benchmarking grafy (volitelně)

```bash
cd benchmarking
pip install -r requirements.txt
python graphs.py # pouhé vygenerování grafu, samotný běh se spouští přes /benchmarking/main.py
```

## Co projekt umí / co obsahuje

- Interaktivní GUI pro načítání bodů, spouštění solverů a zobrazení výsledné trasy na mapě
- Více optimalizačních algoritmů pro TSP/ATSP a porovnání jejich výkonu
- Import/export instancí (TSP/GPX a související formáty podle implementovaných strategií)
- Nastavení routing profilů, API klíče, seedu solverů a dalších parametrů
- Nástroje pro benchmarking, generování grafů a statistické shrnutí výsledků

### Struktura repozitáře

- `code/` - hlavní aplikace a implementace solverů
- `benchmarking/` - skripty pro analýzu a vizualizaci benchmarku
- `latex/` - zdrojové soubory diplomové práce (kapitoly, obrázky, tabulky)

---

## EN

Desktop application developed for a master's thesis focused on solving the Traveling Salesman Problem (TSP/ATSP) on both map-based and synthetic data.

This repository contains:
- a PyQt6 GUI application (`code/`)
- benchmarking and experiment evaluation scripts (`benchmarking/`)
- thesis text and figures (`latex/`)

### What this is

This repository serves as a complete project package for the thesis:
- solver implementations for multiple algorithms (e.g., NN, 2-OPT, 3-OPT, SA, GA, ACO, LK, RSO, LKH)
- support for different distance metrics (geographic and matrix-based)
- map visualization of routes and instance import/export
- benchmarking support and statistical comparison of results

### Installation and run

Requirements:
- Linux/macOS/Windows
- Python 3.10+

Steps (from repository root `DIPLOMA/`):

```bash
cd code
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Notes:
- For routing via OpenRouteService, set `ORS_API_KEY` (optionally `ORS_BASE_URL`).
- The application can also use a local OSRM fallback (if running on `localhost:5000`).

#### Benchmarking plots (optional)

```bash
cd benchmarking
pip install -r requirements.txt
python graphs.py
```

Benchmark runs are executed via:

```bash
cd benchmarking
python main.py
```

### What the project provides

- Interactive GUI for loading points, running solvers, and visualizing resulting routes on a map
- Multiple optimization algorithms for TSP/ATSP with performance comparison
- Instance import/export (TSP/GPX and related formats based on implemented strategies)
- Configuration of routing profiles, API keys, solver seeds, and additional parameters
- Benchmarking tools, plot generation, and statistical summaries

### Repository structure

- `code/` - main application and solver implementations
- `benchmarking/` - scripts for benchmark analysis and visualization
- `latex/` - thesis source files (chapters, figures, tables)
