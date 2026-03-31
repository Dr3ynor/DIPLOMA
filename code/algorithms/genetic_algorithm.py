# ==========================================
#         3. GENETIC ALGORITHM (GA)
# ==========================================
import random
from algorithms.nearest_neighbor import _nearest_neighbor

def _genetic_algorithm(matrix, pop_size=20, generations=2500, mutation_rate=0.66):
    n = len(matrix)
    pop_size = min(pop_size, n * 2)

    def get_route_distance(route):
        dist = sum(matrix[route[i]][route[i+1]] for i in range(n - 1))
        dist += matrix[route[-1]][route[0]]
        return dist

    population = []
    
    nn_route = _nearest_neighbor(matrix)
    nn_dist = get_route_distance(nn_route)
    population.append((nn_route, nn_dist))
    
    best_route = list(nn_route)
    best_distance = nn_dist

    base_route = list(range(1, n))
    for _ in range(pop_size - 1):
        ind = base_route.copy()
        random.shuffle(ind)
        route = [0] + ind
        population.append((route, get_route_distance(route)))

    generations_without_improvement = 0

    for gen in range(generations):
        new_population = []
        improvement_in_this_gen = False

        for i in range(pop_size):
            parent_A_route, parent_A_dist = population[i]

            parent_B_route = random.choice(population)[0]
            attempts = 0
            # Pokud po 10 pokusech nenajde jiného rodiče (populace je samý klon), konec
            while parent_B_route == parent_A_route and attempts < 10:
                parent_B_route = random.choice(population)[0]
                attempts += 1

            # Křížení
            start, end = sorted(random.sample(range(1, n), 2))
            child_route = [None] * n
            child_route[0] = 0
            child_route[start:end] = parent_A_route[start:end]

            inherited_from_A = set(parent_A_route[start:end])

            p2_idx = 1
            for k in range(1, n):
                if child_route[k] is None:
                    while parent_B_route[p2_idx] in inherited_from_A:
                        p2_idx += 1
                    child_route[k] = parent_B_route[p2_idx]
                    p2_idx += 1

            # Mutace
            if random.random() < mutation_rate:
                a, b = random.sample(range(1, n), 2)
                child_route[a], child_route[b] = child_route[b], child_route[a]

            # Vyhodnocení
            child_dist = get_route_distance(child_route)
            
            if child_dist < parent_A_dist:
                new_population.append((child_route, child_dist))
                
                if child_dist < best_distance:
                    best_distance = child_dist
                    best_route = child_route
                    improvement_in_this_gen = True
            else:
                new_population.append((parent_A_route, parent_A_dist))

        population = new_population

        # EARLY STOPPING
        if improvement_in_this_gen:
            generations_without_improvement = 0
        else:
            generations_without_improvement += 1

        if generations_without_improvement > 300:
            print(f"DEBUG: GA ukončen předčasně v generaci {gen} (žádné další zlepšení).")
            break

    return best_route
