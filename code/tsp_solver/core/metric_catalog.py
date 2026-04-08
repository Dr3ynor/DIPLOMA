"""Central catalog of supported distance metrics used by GUI and backend."""

from __future__ import annotations

from typing import Final

# Metric keys
HAVERSINE: Final[str] = "haversine"
EUC_2D: Final[str] = "euc_2d"
MANHATTAN: Final[str] = "manhattan"
CHEBYSHEV: Final[str] = "chebyshev"
ROUTING_DIST: Final[str] = "routing_dist"
ROUTING_TIME: Final[str] = "routing_time"

# Metric groups
PLANAR_POINT_METRICS: Final[tuple[str, ...]] = (EUC_2D, MANHATTAN, CHEBYSHEV)
GEO_POINT_METRICS: Final[tuple[str, ...]] = (HAVERSINE,)
POINT_METRICS: Final[tuple[str, ...]] = GEO_POINT_METRICS + PLANAR_POINT_METRICS
ROUTING_METRICS: Final[tuple[str, ...]] = (ROUTING_DIST, ROUTING_TIME)

# Which metrics should be used per instance type.
GEO_ALLOWED_METRICS: Final[tuple[str, ...]] = GEO_POINT_METRICS + ROUTING_METRICS
NON_GEO_ALLOWED_METRICS: Final[tuple[str, ...]] = PLANAR_POINT_METRICS

# (UI label, key)
METRIC_UI_OPTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("Letecká vzdálenost (Haversine)", HAVERSINE),
    ("Eukleidovská vzdálenost (2D)", EUC_2D),
    ("Manhattan (L1)", MANHATTAN),
    ("Čebyšev (L∞)", CHEBYSHEV),
    ("Trasová vzdálenost – km (dle režimu na mapě, ORS / OSRM)", ROUTING_DIST),
    ("Trasový čas – minuty (dle režimu na mapě, ORS / OSRM)", ROUTING_TIME),
)


def resolve_effective_metric(selected_metric: str, is_geographic: bool) -> str:
    """
    Returns a sensible metric key for the current instance type.

    - GEO instances allow haversine + routing metrics.
    - Non-GEO instances allow planar point metrics.
    """
    if is_geographic:
        if selected_metric in GEO_ALLOWED_METRICS:
            return selected_metric
        return HAVERSINE

    if selected_metric in NON_GEO_ALLOWED_METRICS:
        return selected_metric
    return EUC_2D
