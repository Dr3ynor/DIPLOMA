import math

def tsplib_geo_to_decimal(coord: float) -> float:
    sign = 1 if coord >= 0 else -1
    coord = abs(coord)
    degrees = math.trunc(coord)
    minutes = (coord - degrees) * 100.0
    return sign * (degrees + minutes / 60.0)

def build_geo_tsplib_lines(name: str, points: list[tuple[float, float]]) -> list[str]:
    lines = [
        f"NAME: {name}",
        "TYPE: TSP",
        f"DIMENSION: {len(points)}",
        "EDGE_WEIGHT_TYPE: GEO",
        "COMMENT: MODERN_GPS_DIPLOMA",
        "NODE_COORD_SECTION",
    ]
    for i, (lat, lon) in enumerate(points):
        lines.append(f" {i+1} {lat:.6f} {lon:.6f}")
    lines.append("EOF")
    return lines

def convert_legacy_geo_points(raw_points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [
        (tsplib_geo_to_decimal(lat), tsplib_geo_to_decimal(lon))
        for lat, lon in raw_points
    ]
