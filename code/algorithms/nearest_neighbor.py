def _nearest_neighbor(matrix):
    """
    Implementace Nearest Neighbor (hladový algoritmus).
    Funguje skvěle i pro asymetrické matice (jednosměrky).
    """
    n = len(matrix)
    # Body k navštívení (vše kromě startu 0)
    unvisited = list(range(1, n))
    # Startovní bod
    route = [0]

    while unvisited:
        curr = route[-1]
        # Najdeme uzel, který je k 'curr' nejblíže podle matice
        next_node = min(unvisited, key=lambda node: matrix[curr][node])
        unvisited.remove(next_node)
        route.append(next_node)

    return route