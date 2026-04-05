# 🎓 DIPLOMA – Roadmap & TODO

## 🚀 Main Goals (Kritické cíle)
* **Routing Engine & API Selection:**
    * Přepínač typu dopravy (pěší, cyklo, auto, kamiony).
    * Možnost volby zdroje dat (Lokální API vs. OpenRouteService).
    * Víc vytěžit z API – zjistit, která data jsou použitelné a hlouběji je analyzovat.
* **Algoritmy & Logika:**
    * **Možnost nastavení pevného seedu:** Pro reprodukovatelné výsledky algoritmů.
    * **Nové metriky:** Přidat další metriky kromě času/vzdálenosti/haver.
* **Systémová integrita:**
    * **Check integrity GUI:** Ošetřit stavy, aby uživatel nemohl spouštět akce tam, kde to nedává smysl.
    * Implementace cache.

Spotřeba / CO₂ – proxy z ujetých km a typu vozidla (emisní faktor), případně z profilu (auto vs nákladní už máte jako car / hgv).
Převýšení / energie – pokud byste brali výšky (např. z DEM nebo z rozšířených odpovědí směrů), šlo by penalizovat stoupání (u kola/PEV smysluplné).
Mýto / poplatky – jen pokud API nebo vlastní vrstva vrací peněžní náklad (ORS základní matice ho obvykle neřeší jako samostatnou matici).


Elevation Line 
Geocode Reverse (jestli jde na jeden request víc GPS souřadnic)



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
* Canvas map selection.