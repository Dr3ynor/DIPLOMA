# 🎓 DIPLOMA – Roadmap & TODO

## 🚀 Main Goals (Kritické cíle)
* **Algoritmy & Logika:**
* **Možnost nastavení pevného seedu:** Pro reprodukovatelné výsledky algoritmů.
* **Systémová integrita:**
* **Check integrity GUI:** Ošetřit stavy, aby uživatel nemohl spouštět akce tam, kde to nedává smysl.

## 📊 Data & Výpočty (Palivo & Parametry)
* **Palivový modul:** Počítání litrů paliva, popřípadě průměrná cena paliv, nebo Spotřeba CO₂ / spotřebovaná energie v elektroautě
* **Převýšení** Asi Elevation Line 
* **Clustering:** Shlukování dat. (performance issue vyřešen přechodem na PyQt6)

* **Prozkoumat!**
* POIs endpoint
* ** avoid_features **
* highways – dálnice (driving*)
* tollways – mýtné (driving*)
* ferries – přívozy (driving*, cycling*, foot*, wheelchair)
* fords – brody (driving*, cycling*, foot*)
* steps – schody (cycling*, foot*, wheelchair)

## 🛠️ GUI & UX (Uživatelské rozhraní)
* **Napojit prozkoumané věci do UI**

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
* Podpora souborů: Více typů (JSON, ATT).
