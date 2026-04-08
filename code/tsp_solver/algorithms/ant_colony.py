import random
def _ant_colony(matrix, num_iterations=50, num_ants=None, alpha=1.0, beta=2.0, vaporization_coeff=0.5, Q=1.0):
    """
    Vylepšené ACO inspirované maticovým předpočítáváním.
    """
    n = len(matrix)
    
    # --- ZARÁŽKA NA MAXIMÁLNÍ POČET MRAVENCŮ ---
    if num_ants is None:
        num_ants = min(n, 20)
    
    # 1. PŘEDPOČÍTÁNÍ VIDITELNOSTI (Visibility Matrix)
    # Rovnou umocníme na 'beta'. Tím uvnitř cyklu ušetříme statisíce matematických operací!
    visibility_beta = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dist = matrix[i][j] if matrix[i][j] > 0 else 0.0001
                visibility_beta[i][j] = (1.0 / dist) ** beta

    # Inicializace feromonů (podle tvého vzoru inicializujeme na 1.0)
    pheromones = [[1.0] * n for _ in range(n)]
    
    best_route = None
    best_distance = float('inf')

    for _ in range(num_iterations):
        all_routes = []
        all_distances = []

        # 2. OMEZENÝ POČET MRAVENCŮ
        for _ in range(num_ants):
            # Startujeme z náhodného města kvůli zarážce
            ant = random.randint(0, n - 1)
            
            route = [ant]
            unvisited = set(range(n))
            unvisited.remove(ant)
            route_dist = 0.0

            while unvisited:
                curr = route[-1]
                probabilities = []
                prob_sum = 0.0

                # 3. RYCHLÝ VÝPOČET PRAVDĚPODOBNOSTÍ (čtení z matic)
                for next_node in unvisited:
                    # Pokud je alpha 1.0, ignorujeme zbytečné mocnění
                    tau = pheromones[curr][next_node] if alpha == 1.0 else pheromones[curr][next_node] ** alpha
                    eta_beta = visibility_beta[curr][next_node]
                    
                    prob = tau * eta_beta
                    probabilities.append((next_node, prob))
                    prob_sum += prob

                # Ruleta pro výběr města
                if prob_sum == 0:
                    chosen_node = random.choice(list(unvisited))
                else:
                    r = random.uniform(0, prob_sum)
                    cumulative = 0.0
                    for node, prob in probabilities:
                        cumulative += prob
                        if cumulative >= r:
                            chosen_node = node
                            break
                    else:
                        chosen_node = probabilities[-1][0]

                route.append(chosen_node)
                unvisited.remove(chosen_node)
                # Používáme přímý přístup do matice místo funkce get_dist
                route_dist += matrix[curr][chosen_node] if matrix[curr][chosen_node] > 0 else 0.0001

            # Návrat do startu (uzavření kruhu)
            route_dist += matrix[route[-1]][route[0]] if matrix[route[-1]][route[0]] > 0 else 0.0001
            
            # Normalizace, aby trasa začínala nulou (pro konzistenci v UI)
            zero_idx = route.index(0)
            normalized_route = route[zero_idx:] + route[:zero_idx]
            
            all_routes.append(normalized_route)
            all_distances.append(route_dist)

            if route_dist < best_distance:
                best_distance = route_dist
                best_route = list(normalized_route)

        # 4. ODPAŘOVÁNÍ (Vaporization)
        for i in range(n):
            for j in range(n):
                pheromones[i][j] *= vaporization_coeff

        # Přidání nových feromonů
        for route, dist in zip(all_routes, all_distances):
            pheromone_to_add = Q / dist
            for k in range(n - 1):
                pheromones[route[k]][route[k+1]] += pheromone_to_add
            pheromones[route[-1]][route[0]] += pheromone_to_add

    return best_route if best_route else list(range(n))