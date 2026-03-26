import requests

def get_coordinates(city_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": city_name,
        "format": "json",
        "limit": 1
    }
    headers = {"User-Agent": "DistanceScript/1.0 (jakub@example.com)"}
    response = requests.get(url, params=params, headers=headers)
    data = response.json()

    if not data:
        raise ValueError(f"Město '{city_name}' nebylo nalezeno.")

    lat = float(data[0]["lat"])
    lon = float(data[0]["lon"])
    return lat, lon


def get_distance_osrm(lat1, lon1, lat2, lon2):
    url = f"http://localhost:5000/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    response = requests.get(url)
    data = response.json()

    if "routes" not in data:
        raise ValueError("OSRM server nevrátil trasu – zkontroluj, zda běží.")

    route = data["routes"][0]
    distance_km = route["distance"] / 1000
    duration_min = route["duration"] / 60
    return distance_km, duration_min


def main():
    city_a = input("Zadej první město: ")
    city_b = input("Zadej druhé město: ")

    lat1, lon1 = get_coordinates(city_a)
    lat2, lon2 = get_coordinates(city_b)

    print(f"{city_a}: ({lat1}, {lon1})")
    print(f"{city_b}: ({lat2}, {lon2})")

    distance, duration = get_distance_osrm(lat1, lon1, lat2, lon2)

    print(f"\nVýsledek:")
    print(f"Vzdálenost: {distance:.2f} km")
    print(f"Odhadovaná doba jízdy: {duration:.1f} minut")


if __name__ == "__main__":
    main()
