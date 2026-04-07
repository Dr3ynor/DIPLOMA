# 🎓 DIPLOMA – Roadmap & TODO

## 🚀 Main Goals (Kritické cíle)
* **Algoritmy & Logika:**
* **Možnost nastavení pevného seedu:** Pro reprodukovatelné výsledky algoritmů.

* **Systémová integrita:**
* **Check integrity GUI:** Ošetřit stavy, aby uživatel nemohl spouštět akce tam, kde to nedává smysl.

## 📊 Data & Výpočty (Palivo & Parametry)
* **Clustering:** Shlukování dat. (performance issue vyřešen přechodem na PyQt6)

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

profile_params
Doplňkové parametry konkrétního profilu (váhy preferencí, limity pro HGV – výška, hmotnost, počet náprav…).
K čemu: realističtější trasy pro nákladní auto, dodávku, nebo jemné doladění chování profilu (co upřednostnit). Pro „osobní auto“ často default stačí; pro diplomovou práci o nákladní dopravě je to přímo relevantní.

extra_info
Nemění geometrii trasy – do odpovědi přidává atributy po segmentech / úsecích (strmost, povrch, typ cesty, kategorie, obtížnost trailu, mýtné, omezení vjezdu, země, OSM ID, případně green/noise/shadow/suitability… podle profilu).
K čemu:

Analýza a vizualizace: „kolik % trasy je špatný povrch“, kde jsou prudké úseky, kde je mýto.
Validace: kontrola, jestli trasa nevede přes nevhodné úseky (i když ORS ji našel).
Rozšířený výpis / PDF: bohatší popis než čistý turn-by-turn.
Výzkum / práce: metriky kvality trasy mimo čistý čas a délku.
