# 🎓 DIPLOMA – Roadmap & TODO

## 🚀 Main Goals (Kritické cíle)
* **Routing Engine & API Selection:**
    * Možnost volby zdroje dat (Lokální API vs. OpenRouteService).
    * Víc vytěžit z API – zjistit, která data jsou použitelné a hlouběji je analyzovat.
* **Algoritmy & Logika:**
    * **Možnost nastavení pevného seedu:** Pro reprodukovatelné výsledky algoritmů.
    * **Nové metriky:** Přidat další metriky kromě času/vzdálenosti/haver.
* **Systémová integrita:**
    * **Check integrity GUI:** Ošetřit stavy, aby uživatel nemohl spouštět akce tam, kde to nedává smysl.
    * Implementace cache.

Mýto / poplatky – jen pokud API nebo vlastní vrstva vrací peněžní náklad (ORS základní matice ho obvykle neřeší jako samostatnou matici).

## 🛠️ GUI & UX (Uživatelské rozhraní)
* **Mapové podklady:**
    * Esri satellite, street.
    * Stamen terrain, Stamen (?).
    * Opentopomap.

## 📊 Data & Výpočty (Palivo & Parametry)
* **Palivový modul:** Počítání litrů paliva, popřípadě průměrná cena paliv, nebo Spotřeba CO₂
* **Převýšení** Asi Elevation Line 
* **Podpora souborů:** Více typů (json, tsp, ATT).
* **Clustering:** Shlukování dat.

* **Prozkoumat!**
** avoid_features **
* highways – dálnice (driving*)
* tollways – mýtné (driving*)
* ferries – přívozy (driving*, cycling*, foot*, wheelchair)
* **fords** – brody (driving*, cycling*, foot*)
* steps – schody (cycling*, foot*, wheelchair)

**Další v options (orientačně)**
* avoid_borders – např. all / controlled (omezení přechodů hranic)
* avoid_countries – vynechat státy (ISO kódy podle dokumentace)
* avoid_polygons – oblasti k vyhnutí jako GeoJSON polygon(y)
* profile_params – doplňky podle profilu (např. váhy, omezení u HGV – výška, hmotnost, osy… kde to profil podporuje)
* extra_info (nevyhýbat se, ale dostat info po segmentech)
* např. steepness, surface, waytype, waycategory, traildifficulty, tollways, roadaccessrestrictions, countryinfo, osmid, u některých profilů i green, noise, shadow, suitability, …




## ⚡ OPTIONAL (Nice-to-have)
* **!!!!!! Nalezení optimálních parametrů na základě rozložení dat na mapě / canvasu**
* Canvas map selection.