from __future__ import annotations

def tour_length(route, matrix):
    n = len(route)
    if n < 2:
        return 0.0
    total = 0.0
    for i in range(n - 1):
        total += matrix[route[i]][route[i + 1]]
    total += matrix[route[-1]][route[0]]
    return total


def two_opt_delta(route, matrix, i, j):
    n = len(route)
    if j - i <= 1:
        return 0.0
    a, b, c, d = route[i - 1], route[i], route[j], route[(j + 1) % n]
    old_e = matrix[a][b] + matrix[c][d]
    new_e = matrix[a][c] + matrix[b][d]
    return new_e - old_e


def default_polish_budget(n: int) -> int:
    return min(80_000, max(2_000, 12 * n * n))


def polish_route_random_two_opt(route, matrix, rng, max_checks: int | None = None):
    n = len(route)
    if n < 4:
        return route
    budget = default_polish_budget(n) if max_checks is None else max_checks
    for _ in range(budget):
        i, j = sorted(rng.sample(range(1, n), 2))
        if j - i <= 1:
            continue
        dlt = two_opt_delta(route, matrix, i, j)
        if dlt < 0:
            route[i : j + 1] = reversed(route[i : j + 1])
    return route


def random_tour_zero_fixed(n, rng):
    inner = list(range(1, n))
    rng.shuffle(inner)
    return [0] + inner


def _apply_relocate(route, src: int, dst: int):
    node = route.pop(src)
    route.insert(dst, node)


def _apply_or_opt(route, start: int, length: int, dst: int):
    block = route[start : start + length]
    del route[start : start + length]
    route[dst:dst] = block


def random_atsp_neighbor(route, rng):
    n = len(route)
    if n < 4:
        return list(route)
    candidate = list(route)
    op = rng.random()
    if op < 0.45:
        i, j = rng.sample(range(1, n), 2)
        candidate[i], candidate[j] = candidate[j], candidate[i]
        return candidate
    if op < 0.80:
        src = rng.randrange(1, n)
        dst = rng.randrange(1, n)
        if dst == src:
            return candidate
        _apply_relocate(candidate, src, dst)
        return candidate
    if n < 6:
        i, j = rng.sample(range(1, n), 2)
        candidate[i], candidate[j] = candidate[j], candidate[i]
        return candidate
    length = 2 if rng.random() < 0.65 else 3
    start = rng.randrange(1, n - length + 1)
    valid_dests = [d for d in range(1, n - length + 1) if d < start or d > start + length]
    if not valid_dests:
        return candidate
    dst = rng.choice(valid_dests)
    _apply_or_opt(candidate, start, length, dst)
    return candidate


def polish_route_random_atsp(route, matrix, rng, max_checks: int | None = None):
    n = len(route)
    if n < 4:
        return route
    budget = default_polish_budget(n) if max_checks is None else max_checks
    best_cost = tour_length(route, matrix)
    for _ in range(budget):
        candidate = random_atsp_neighbor(route, rng)
        cand_cost = tour_length(candidate, matrix)
        if cand_cost < best_cost:
            route[:] = candidate
            best_cost = cand_cost
    return route
