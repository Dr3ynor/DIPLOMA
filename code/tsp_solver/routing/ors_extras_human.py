"""
Lidsky čitelný výpis ORS directions extras (summary + values).

Mapování kódů podle ORS API dokumentace (extra-info, country-list).
"""

from __future__ import annotations

import html
import json
from typing import Any

# country_id → name:en (ORS technical-details/country-list)
ORS_COUNTRY_EN: dict[int, str] = dict(
    [
        (1, "Afghanistan"),
        (2, "Albania"),
        (3, "Algeria"),
        (4, "Andorra"),
        (5, "Angola"),
        (6, "Anguilla"),
        (7, "Antigua and Barbuda"),
        (8, "Argentina"),
        (9, "Armenia"),
        (10, "Australia"),
        (11, "Austria"),
        (12, "Azerbaijan"),
        (13, "Bahrain"),
        (14, "Bangladesh"),
        (15, "Barbados"),
        (16, "Belarus"),
        (17, "Belgium"),
        (18, "Belize"),
        (19, "Benin"),
        (20, "Bermuda"),
        (21, "Bhutan"),
        (22, "Bolivia"),
        (23, "Bosnia and Herzegovina"),
        (24, "Botswana"),
        (25, "Brazil"),
        (26, "British Indian Ocean Territory"),
        (27, "British Sovereign Base Areas"),
        (28, "British Virgin Islands"),
        (29, "Brunei"),
        (30, "Bulgaria"),
        (31, "Burkina Faso"),
        (32, "Burundi"),
        (33, "Cambodia"),
        (34, "Cameroon"),
        (35, "Canada"),
        (36, "Cape Verde"),
        (37, "Cayman Islands"),
        (38, "Central African Republic"),
        (39, "Chad"),
        (40, "Chile"),
        (41, "China"),
        (42, "Colombia"),
        (43, "Comoros"),
        (44, "Congo-Brazzaville"),
        (45, "Congo-Kinshasa"),
        (46, "Cook Islands"),
        (47, "Costa Rica"),
        (48, "Côte d'Ivoire"),
        (49, "Croatia"),
        (50, "Cuba"),
        (51, "Cyprus"),
        (52, "Česko"),
        (53, "Denmark"),
        (54, "Djibouti"),
        (55, "Dominica"),
        (56, "Dominican Republic"),
        (57, "East Timor"),
        (58, "Ecuador"),
        (59, "Egypt"),
        (60, "El Salvador"),
        (61, "Equatorial Guinea"),
        (62, "Eritrea"),
        (63, "Estonia"),
        (64, "Ethiopia"),
        (65, "Falkland Islands"),
        (66, "Faroe Islands"),
        (67, "Federated States of Micronesia"),
        (68, "Fiji"),
        (69, "Finland"),
        (70, "France"),
        (71, "Gabon"),
        (72, "Gambia"),
        (73, "Georgia"),
        (74, "Germany"),
        (75, "Germany - Belgium"),
        (76, "Ghana"),
        (77, "Gibraltar"),
        (78, "Greece"),
        (79, "Greenland"),
        (80, "Grenada"),
        (81, "Guatemala"),
        (82, "Guernsey"),
        (83, "Guinea"),
        (84, "Guinea-Bissau"),
        (85, "Guyana"),
        (86, "Haiti"),
        (87, "Honduras"),
        (88, "Hungary"),
        (89, "Iceland"),
        (90, "India"),
        (91, "Indonesia"),
        (92, "Iran"),
        (93, "Iraq"),
        (94, "Ireland"),
        (95, "Isle of Man"),
        (96, "Israel"),
        (97, "Italy"),
        (98, "Jamaica"),
        (99, "Jangy-ayyl"),
        (100, "Japan"),
        (101, "Jersey"),
        (102, "Jordan"),
        (103, "Kazakhstan"),
        (104, "Kenya"),
        (105, "Kiribati"),
        (106, "Kosovo"),
        (107, "Kuwait"),
        (108, "Kyrgyzstan"),
        (109, "Laos"),
        (110, "Latvia"),
        (111, "Lebanon"),
        (112, "Lesotho"),
        (113, "Liberia"),
        (114, "Libya"),
        (115, "Liechtenstein"),
        (116, "Lithuania"),
        (117, "Luxembourg"),
        (118, "Macedonia"),
        (119, "Madagascar"),
        (120, "Malawi"),
        (121, "Malaysia"),
        (122, "Maldives"),
        (123, "Mali"),
        (124, "Malta"),
        (125, "Marshall Islands"),
        (126, "Mauritania"),
        (127, "Mauritius"),
        (128, "Mexico"),
        (129, "Moldova"),
        (130, "Monaco"),
        (131, "Mongolia"),
        (132, "Montenegro"),
        (133, "Montserrat"),
        (134, "Morocco"),
        (135, "Mozambique"),
        (136, "Myanmar"),
        (138, "Namibia"),
        (139, "Nauru"),
        (140, "Nepal"),
        (141, "Netherlands - Belgium"),
        (142, "New Zealand"),
        (143, "Nicaragua"),
        (144, "Niger"),
        (145, "Nigeria"),
        (146, "Niue"),
        (147, "North Korea"),
        (148, "Norway"),
        (149, "Oman"),
        (150, "Pakistan"),
        (151, "Palau"),
        (152, "Palestinian Territories"),
        (153, "Panama"),
        (154, "Papua New Guinea"),
        (155, "Paraguay"),
        (156, "Peru"),
        (157, "Philippines"),
        (158, "Pitcairn Islands"),
        (159, "Poland"),
        (160, "Portugal"),
        (161, "Qatar"),
        (162, "Romania"),
        (163, "Russian Federation"),
        (164, "Rwanda"),
        (165, "Sahrawi Arab Democratic Republic"),
        (166, "Saint Helena - Ascension and Tristan da Cunha"),
        (167, "Saint Kitts and Nevis"),
        (168, "Saint Lucia"),
        (169, "Saint Vincent and the Grenadines"),
        (170, "Samoa"),
        (171, "San Marino"),
        (172, "São Tomé and Príncipe"),
        (173, "Saudi Arabia"),
        (174, "Senegal"),
        (175, "Serbia"),
        (176, "Seychelles"),
        (177, "Sierra Leone"),
        (178, "Singapore"),
        (179, "Slovakia"),
        (180, "Slovenia"),
        (181, "Solomon Islands"),
        (182, "Somalia"),
        (183, "South Africa"),
        (184, "South Georgia and the South Sandwich Islands"),
        (185, "South Korea"),
        (186, "South Sudan"),
        (187, "Spain"),
        (188, "Sri Lanka"),
        (189, "Sudan"),
        (190, "Suriname"),
        (191, "Swaziland"),
        (192, "Sweden"),
        (193, "Switzerland"),
        (194, "Syria"),
        (195, "Taiwan"),
        (196, "Tajikistan"),
        (197, "Tanzania"),
        (198, "Thailand"),
        (199, "The Bahamas"),
        (200, "The Netherlands"),
        (201, "Togo"),
        (202, "Tokelau"),
        (203, "Tonga"),
        (204, "Trinidad and Tobago"),
        (205, "Tunisia"),
        (206, "Turkey"),
        (207, "Turkmenistan"),
        (208, "Turks and Caicos Islands"),
        (209, "Tuvalu"),
        (210, "Uganda"),
        (211, "Ukraine"),
        (212, "United Arab Emirates"),
        (213, "United Kingdom"),
        (214, "United States of America"),
        (215, "Uruguay"),
        (216, "Uzbekistan"),
        (217, "Vanuatu"),
        (218, "Vatican City"),
        (219, "Venezuela"),
        (220, "Vietnam"),
        (221, "Yemen"),
        (222, "Zambia"),
        (223, "Zimbabwe"),
        (224, "Border India - Bangladesh"),
        (225, "Île Verte"),
        (226, "Border Azerbaijan - Armenia (Enclave AZE)"),
        (227, "Freezland Rock"),
        (228, "Border SI-HR"),
        (229, "Willis Island"),
        (230, "Chong-Kara"),
        (231, "Greece - Pangaio"),
        (232, "Bristol Island"),
        (233, "Dist. Judges Court"),
        (234, "Border Kyrgyzstan - Uzbekistan"),
        (235, "Border Malawi - Mozambique"),
        (236, "Taiwan (ROC)"),
    ]
)

_STEEPNESS_CS: dict[int, str] = {
    -5: "≥ 16 % klesání",
    -4: "10–16 % klesání",
    -3: "7–10 % klesání",
    -2: "4–7 % klesání",
    -1: "1–4 % klesání",
    0: "téměř vodorovně (0–1 % stoupání)",
    1: "1–4 % stoupání",
    2: "4–7 % stoupání",
    3: "7–10 % stoupání",
    4: "10–16 % stoupání",
    5: "≥ 16 % stoupání",
}

_SURFACE_CS: dict[int, str] = {
    0: "Neznámý",
    1: "Zpevněný (obecně)",
    2: "Nezpevněný",
    3: "Asfalt",
    4: "Beton",
    5: "Dlažební kostky",
    6: "Kov",
    7: "Dřevo",
    8: "Udusaný štěrk",
    9: "Jemný štěrk",
    10: "Štěrk",
    11: "Hlína / zemina",
    12: "Půda / bláto",
    13: "Led / sníh",
    14: "Dlažba / dlaždice",
    15: "Písek",
    16: "Dřevní štěpka",
    17: "Tráva",
    18: "Trávové panely",
}

_WAYTYPE_CS: dict[int, str] = {
    0: "Neznámý",
    1: "Silnice I. třídy / dálnice (primary, motorway, trunk…)",
    2: "Silnice II./III. třídy (secondary, tertiary…)",
    3: "Ulice (obec, obslužné)",
    4: "Cesta (path)",
    5: "Polní / lesní cesta (track)",
    6: "Cyklostezka",
    7: "Chodník",
    8: "Schody",
    9: "Přívoz / trajekt",
    10: "Stavba / rozestavěno",
}

# waycategory: bitové příznaky (ORS)
_WAYCATEGORY_BITS: tuple[tuple[int, str], ...] = (
    (16, "Brod"),
    (8, "Přívoz"),
    (4, "Schody"),
    (2, "Zpoplatněný úsek (toll)"),
    (1, "Dálnice / rychlostní komunikace"),
)

# roadaccessrestrictions: bitové příznaky (ORS)
_ROADACCESS_BITS: tuple[tuple[int, str], ...] = (
    (64, "Povolení (permit)"),
    (32, "Permisivní přístup"),
    (16, "Soukromá cesta"),
    (8, "Rozvoz / zásobování"),
    (4, "Jen cíl (destination)"),
    (2, "Jen zákazníci"),
    (1, "Zákázáno (no)"),
)

_TRAIL_DIFFICULTY_CS: dict[int, str] = {
    0: "Bez značení obtížnosti",
    1: "Turistická chůze / MTB 0",
    2: "Horská turistika / MTB 1",
    3: "Náročná horská / MTB 2",
    4: "Alpská turistika / MTB 3",
    5: "Velmi náročná alpská / MTB 4",
    6: "Extrémní alpská / MTB 5",
    7: "MTB 6",
}


def _norm_summary_value(v: Any) -> float | int:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v == int(v):
            return int(v)
        return v
    try:
        x = float(v)
        if x == int(x):
            return int(x)
        return x
    except (TypeError, ValueError):
        return 0


def aggregate_summary_by_value(summary: list[Any]) -> list[dict[str, Any]]:
    """Sloučí řádky se stejným `value`, přepočítá amount (%)."""
    acc: dict[Any, float] = {}
    for row in summary:
        if not isinstance(row, dict):
            continue
        if "value" not in row or "distance" not in row:
            continue
        try:
            d = float(row["distance"])
        except (TypeError, ValueError):
            continue
        key = _norm_summary_value(row["value"])
        acc[key] = acc.get(key, 0.0) + d
    total = sum(acc.values())
    out: list[dict[str, Any]] = []
    for key, dist in acc.items():
        pct = (100.0 * dist / total) if total > 0 else 0.0
        out.append({"value": key, "distance": dist, "amount": round(pct, 2)})
    out.sort(key=lambda r: r["distance"], reverse=True)
    return out


def _decode_bitmask(v: int, bits: tuple[tuple[int, str], ...]) -> str:
    if v == 0:
        return "Žádná"
    parts: list[str] = []
    for mask, label in bits:
        if v & mask:
            parts.append(label)
    if not parts:
        return f"Kód {v}"
    return " + ".join(parts)


def label_for_extra_value(extra_key: str, value: Any) -> str:
    k = extra_key.lower()
    vk = _norm_summary_value(value)
    iv = int(vk) if isinstance(vk, float) and vk == int(vk) else vk

    if k == "countryinfo":
        cid = int(iv) if isinstance(iv, (int, float)) else int(float(vk))
        return ORS_COUNTRY_EN.get(cid, f"Země ORS #{cid}")

    if k == "steepness" and isinstance(iv, int):
        return _STEEPNESS_CS.get(iv, f"Sklon kód {iv}")

    if k == "surface" and isinstance(iv, int):
        return _SURFACE_CS.get(iv, f"Povrch kód {iv}")

    if k == "waytype" and isinstance(iv, int):
        return _WAYTYPE_CS.get(iv, f"Typ cesty kód {iv}")

    if k == "tollways":
        if iv == 0:
            return "Bez mýta"
        if iv == 1:
            return "Mýtný úsek"
        return f"Mýtné kód {iv}"

    if k == "traildifficulty" and isinstance(iv, int):
        return _TRAIL_DIFFICULTY_CS.get(iv, f"Obtížnost kód {iv}")

    if k == "waycategory" and isinstance(iv, int):
        return _decode_bitmask(iv, _WAYCATEGORY_BITS)

    if k == "roadaccessrestrictions" and isinstance(iv, int):
        if iv == 0:
            return "Bez omezení vjezdu"
        return _decode_bitmask(iv, _ROADACCESS_BITS)

    if k in ("suitability", "green", "noise", "shadow") and isinstance(iv, int):
        if k == "suitability":
            return f"Vhodnost {iv} (1 = nevhodné … 10 = velmi vhodné)"
        if k == "green":
            return f"Zeleň {iv} (0 = málo … 10 = hodně)"
        if k == "noise":
            return f"Hluk {iv} (0 = ticho … 10 = hlučné)"
        return f"Stín / slunce {iv} (0 = stín … 10 = slunce)"

    if isinstance(iv, int):
        return f"Hodnota {iv}"
    return f"Hodnota {vk}"


def _fallback_json_block(raw: Any) -> str:
    try:
        pretty = json.dumps(raw, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        pretty = str(raw)
    return f"<pre style='white-space:pre-wrap;font-size:12px'>{html.escape(pretty)}</pre>"


def format_standard_extra_html(
    extra_key: str,
    data: dict[str, Any],
    *,
    border_color: str = "#64748b",
    dim_color: str = "#94a3b8",
) -> str:
    summary = data.get("summary")
    if not isinstance(summary, list) or not summary:
        return _fallback_json_block(data)

    agg = aggregate_summary_by_value(summary)
    if not agg:
        return _fallback_json_block(data)
    rows: list[str] = []
    for row in agg:
        lbl = html.escape(label_for_extra_value(extra_key, row["value"]))
        km = float(row["distance"]) / 1000.0
        pct = float(row["amount"])
        rows.append(
            "<tr>"
            f"<td style='padding:6px 8px;border:1px solid {border_color}'>{lbl}</td>"
            f"<td style='padding:6px 8px;border:1px solid {border_color};text-align:right;white-space:nowrap'>{km:.1f} km</td>"
            f"<td style='padding:6px 8px;border:1px solid {border_color};text-align:right'>{pct:.1f} %</td>"
            "</tr>"
        )

    thead = (
        "<thead><tr>"
        f"<th style='padding:6px 8px;border-bottom:2px solid {border_color};text-align:left'>Kategorie</th>"
        f"<th style='padding:6px 8px;border-bottom:2px solid {border_color};text-align:right'>Vzdálenost</th>"
        f"<th style='padding:6px 8px;border-bottom:2px solid {border_color};text-align:right'>Podíl</th>"
        "</tr></thead>"
    )
    table = (
        f"<table style='border-collapse:collapse;width:100%;margin-bottom:10px'>{thead}"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )

    return table


def format_ors_extras_html(
    extras: dict[str, Any],
    *,
    title_cs: dict[str, str] | None = None,
    palette: dict[str, str] | None = None,
) -> str:
    """Celé tělo HTML pro QTextBrowser (bez wrapperu html/body)."""
    if not extras:
        return (
            "<p>API nevrátilo žádná pole <code>extras</code> "
            "(zkuste jiný profil nebo zkontrolujte klíč).</p>"
        )

    border = (palette or {}).get("border", "#64748b")
    dim = (palette or {}).get("text_dim", "#94a3b8")

    blocks: list[str] = []
    titles = title_cs or {}
    for k in sorted(extras.keys()):
        title = html.escape(titles.get(k, k))
        raw = extras[k]
        blocks.append(f"<h3 style='margin:16px 0 8px'>{title}</h3>")
        if (
            isinstance(raw, dict)
            and isinstance(raw.get("summary"), list)
            and raw["summary"]
        ):
            blocks.append(
                format_standard_extra_html(
                    k,
                    raw,
                    border_color=border,
                    dim_color=dim,
                )
            )
        else:
            blocks.append(_fallback_json_block(raw))

    return "\n".join(blocks)
