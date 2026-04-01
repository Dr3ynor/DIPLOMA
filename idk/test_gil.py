import threading
import time
import sys

# Funkce simulující náročný výpočet (CPU bound)
def cpu_bound_task(n):
    count = 0
    for i in range(n):
        count += i
    return count

def run_test(num_threads, iterations):
    threads = []
    start_time = time.perf_counter()

    for _ in range(num_threads):
        t = threading.Thread(target=cpu_bound_task, args=(iterations,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    end_time = time.perf_counter()
    return end_time - start_time

if __name__ == "__main__":
    # Kontrola, zda je GIL aktivní
    # V Pythonu 3.13 existuje sys._is_gil_enabled()
    gil_status = "neznámý"
    if hasattr(sys, "_is_gil_enabled"):
        gil_status = sys._is_gil_enabled()
    
    print(f"--- Python verze: {sys.version} ---")
    print(f"--- Stav GIL: {gil_status} ---\n")

    iterations = 60_000_000
    
    print(f"Spouštím test s 1 vláknem...")
    time_1 = run_test(1, iterations)
    print(f"Čas (1 vlákno): {time_1:.4f} s\n")

    print(f"Spouštím test se 8 vlákny...")
    time_4 = run_test(8, iterations)
    print(f"Čas (8 vlákna): {time_4:.4f} s")
    