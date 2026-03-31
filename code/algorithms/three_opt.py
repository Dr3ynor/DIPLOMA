# ==========================================
#             3-OPT (TĚŽKÉ LOKÁLNÍ HLEDÁNÍ)
# ==========================================

from algorithms.nearest_neighbor import _nearest_neighbor

def _three_opt(matrix, route=None):
    """
    Předchůdce a jádro Lin-Kernighan algoritmu.
    Využívá Search Window (okno), aby nezavařil procesor u velkých instancí.
    """
    n = len(matrix)
    
    # 1. Odrazový můstek: Nejprve to proženeme rychlým 2-Optem
    if route is None:
        best_route = _nearest_neighbor(matrix)
    else:
        best_route = list(route)

    improvement = True
    
    # OCHRANA VÝKONU: Zkoumáme jen města, která jsou na trase blízko sebe.
    # Max 40 uzlů dopředu. Pro malé instance (do 40 měst) se prohledá všechno.
    window = min(n, 40) 
    
    while improvement:
        improvement = False
        
        for i in range(1, n - 4):
            # j nepojede až do konce, ale jen do vzdálenosti 'window' od i
            for j in range(i + 2, min(i + window, n - 2)):
                # k nepojede až do konce, ale jen do vzdálenosti 'window' od j
                for k in range(j + 2, min(j + window, n)):
                    
                    A, B = best_route[i-1], best_route[i]
                    C, D = best_route[j-1], best_route[j]
                    E, F = best_route[k-1], best_route[k % n]

                    d0 = matrix[A][B] + matrix[C][D] + matrix[E][F]

                    d1 = matrix[A][C] + matrix[B][E] + matrix[D][F]
                    d2 = matrix[A][D] + matrix[E][B] + matrix[C][F]
                    d3 = matrix[A][D] + matrix[E][C] + matrix[B][F]
                    d4 = matrix[A][E] + matrix[D][B] + matrix[C][F]

                    best_d = min(d1, d2, d3, d4)

                    if best_d < d0:
                        if best_d == d1:
                            best_route = best_route[:i] + best_route[j-1:i-1:-1] + best_route[k-1:j-1:-1] + best_route[k:]
                        elif best_d == d2:
                            best_route = best_route[:i] + best_route[j:k] + best_route[i:j] + best_route[k:]
                        elif best_d == d3:
                            best_route = best_route[:i] + best_route[j:k] + best_route[j-1:i-1:-1] + best_route[k:]
                        elif best_d == d4:
                            best_route = best_route[:i] + best_route[k-1:j-1:-1] + best_route[i:j] + best_route[k:]

                        improvement = True
                        break
                if improvement: break
            if improvement: break

    return best_route