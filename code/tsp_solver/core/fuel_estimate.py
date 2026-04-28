"""
Odhad spotřeby paliva – orientační model (ne homologace).

Základ: litry = (D_km / 100) * spotřeba_l_per_100km
S výškovým profilem: segmentové úpravy podle Δh a délky úseku.
"""

from __future__ import annotations

# Litry navíc na 100 m převýšení při úseku (~1 km referenční škála)
_EXTRA_L_PER_100M_CLIMB = 0.12
# Útlum spotřeby při klesání
_DOWNHILL_RECOVERY = 0.35
# Minimální segmentová spotřeba jako zlomek základní
_MIN_SEGMENT_FACTOR = 0.08


def distance_km_for_fuel(
    metric_key: str | None,
    total_value: float | None,
) -> tuple[float | None, str]:
    """
    Vrátí (délka_km, poznámka).
    Pro routing_time nelze z času spolehlivě odvodit objem paliva bez rychlosti.
    """
    if total_value is None:
        return None, "chybí souhrn trasy"
    mk = metric_key or ""
    if mk == "routing_dist":
        return float(total_value), ""
    if mk == "routing_time":
        return None, "odhad paliva z času nelze použít"
    if mk == "haversine":
        return float(total_value), "hrubý odhad (vzdušná vzdálenost)"
    return float(total_value), ""


def estimate_liters_base(distance_km: float, l_per_100km: float) -> float:
    if distance_km <= 0 or l_per_100km < 0:
        return 0.0
    return (distance_km / 100.0) * l_per_100km


def estimate_liters_with_elevation(
    distance_km: float,
    l_per_100km: float,
    profile: list[tuple[float, float]],
) -> float:
    """
    profile: (km_along_route, elevation_m)
    Segmentový model: základ l/100 na úsek, + stoupání / klesání.
    """
    if distance_km <= 0 or l_per_100km < 0:
        return 0.0
    if len(profile) < 2:
        return estimate_liters_base(distance_km, l_per_100km)

    total_l = 0.0
    for i in range(1, len(profile)):
        d_prev, h_prev = profile[i - 1]
        d_curr, h_curr = profile[i]
        seg_km = max(0.0, d_curr - d_prev)
        if seg_km <= 0:
            continue
        dh = h_curr - h_prev
        base_seg = (seg_km / 100.0) * l_per_100km
        if dh > 0:
            extra = (dh / 100.0) * _EXTRA_L_PER_100M_CLIMB * max(0.5, seg_km)
            seg_liters = base_seg + extra
        elif dh < 0:
            reduction = _DOWNHILL_RECOVERY * base_seg * min(1.0, abs(dh) / 50.0)
            seg_liters = max(base_seg * _MIN_SEGMENT_FACTOR, base_seg - reduction)
        else:
            seg_liters = base_seg
        total_l += seg_liters

    if total_l <= 0:
        return estimate_liters_base(distance_km, l_per_100km)
    scale = (distance_km / profile[-1][0]) if profile[-1][0] > 0 else 1.0
    if 0.85 <= scale <= 1.15:
        return total_l
    return total_l * scale
