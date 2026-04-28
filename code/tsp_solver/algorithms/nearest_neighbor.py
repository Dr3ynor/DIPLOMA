def _nearest_neighbor(matrix):
    n = len(matrix)
    unvisited = list(range(1, n))
    route = [0]

    while unvisited:
        curr = route[-1]
        next_node = min(unvisited, key=lambda node: matrix[curr][node])
        unvisited.remove(next_node)
        route.append(next_node)

    return route