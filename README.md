# 🎓 DIPLOMA – Roadmap & TODO

## 🚀 Main Goals (Kritické cíle)
* **Routing Engine & API Selection:**
    * Implementace Geoapify / OpenRouteService (ORS).
    * Přepínač typu dopravy (pěší, cyklo, auto, kamiony).
    * Možnost volby zdroje dat (Lokální API vs. OpenRouteService).
    * Víc vytěžit z API – zjistit, která data jsou použitelné a hlouběji je analyzovat.
* **Algoritmy & Logika:**
    * **Možnost nastavení pevného seedu:** Pro reprodukovatelné výsledky algoritmů.
    * **Nové metriky:** Přidat další metriky kromě času/vzdálenosti/haver.
* **Systémová integrita:**
    * **Check integrity GUI:** Ošetřit stavy, aby uživatel nemohl spouštět akce tam, kde to nedává smysl.
    * Implementace cache.

## 🛠️ GUI & UX (Uživatelské rozhraní)
* **Interaktivita & Navigace:**
    * **Search bar:** Možnost zadání adresy. -> poslání na api / na lokální OSRM
    * **Click v listu na bod:** Najde ho na mapě; v listu zobrazit GPS + nejbližší POI.
    * Nastavení zobrazení/skrytí indexů jednotlivých bodů.
* **Layout & Design:**
    * Možná upravit GUI (Top bar / Bottom bar).
    * Settings appky: clear cache.
* **Mapové podklady:**
    * Esri satellite, street.
    * Stamen terrain, Stamen (?).
    * Opentopomap.

## 📊 Data & Výpočty (Palivo & Parametry)
* **Palivový modul:** Počítání litrů paliva, popřípadě průměrná cena paliv.
* **Podpora souborů:** Více typů (json, tsp, ATT).
* **Clustering:** Shlukování dat.

## ⚡ OPTIONAL (Nice-to-have)
* **!!!!!! Nalezení optimálních parametrů na základě rozložení dat na mapě / canvasu**
* **API Settings:** Přidání vlastního externího i lokálního API. (spíš ne xd)
* Canvas map selection.