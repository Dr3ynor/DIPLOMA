# ==========================================
#             2-OPT (LOKÁLNÍ HLEDÁNÍ)
# ==========================================
from tsp_solver.algorithms.nearest_neighbor import _nearest_neighbor

def _two_opt(matrix, route=None):
    """
    Vezme počáteční trasu (pokud není, vytvoří ji přes NN) a 'rozplete' 
    překřížené cesty zrcadlovým otočením segmentů.
    """
    n = len(matrix)
    # Odrazový můstek
    if route is None:
        best_route = _nearest_neighbor(matrix)
    else:
        best_route = list(route)

    improvement = True
    
    # Cyklus běží, dokud dokážeme trasu zlepšovat
    while improvement:
        improvement = False
        for i in range(1, n - 2):
            for j in range(i + 1, n):
                if j - i == 1: 
                    continue # Nemá smysl otáčet sousední body

                # Délka dvou aktuálních hran
                current_edges = matrix[best_route[i-1]][best_route[i]] + matrix[best_route[j]][best_route[(j+1)%n]]
                # Délka hran, kdybychom je překřížili
                new_edges = matrix[best_route[i-1]][best_route[j]] + matrix[best_route[i]][best_route[(j+1)%n]]

                # Pokud nové spojení zkrátí trasu, otočíme segment
                if new_edges < current_edges:
                    best_route[i:j+1] = reversed(best_route[i:j+1])
                    improvement = True
    
    return best_route