from __future__ import annotations

"""Shared TSP route utilities: length and budgeted random 2-opt polishing."""


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
    """Signed cost change if segment route[i : j+1] is reversed (classic 2-opt)."""
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
    """
    In-place random 2-opt search capped by max_checks proposals.
    Returns the same route list (for chaining).
    """
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
    """Hamiltonian cycle as permutation with city 0 fixed at index 0."""
    inner = list(range(1, n))
    rng.shuffle(inner)
    return [0] + inner
