import os
import sys
import json
import time

sys.path.append(r"d:\Thuật Toán")
from parser import load_benchmark
from main import VRPTWSolver

def main():
    cache_path = os.path.join(r"d:\Thuật Toán", "optimal_routes_cache.json")
    if not os.path.exists(cache_path):
        print("Cache file not found. Wait for generate_cache.py to finish.")
        return
        
    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)
        
    d = os.path.join(r"d:\Thuật Toán", "Code GitHub", "WCVRPTW-benchmark-main", "instances")
    f = "277_stop.txt"
    file_path = os.path.join(d, f)
    
    data = load_benchmark(file_path)
    solver = VRPTWSolver(data)
    
    print("Fixing 277_stop.txt Alg 2 Paper Mode in cache...")
    st = time.time()
    vn, sm, nh, td, rtd, routes = solver.solve(
        algo_type=2, initial_vehicles=3, sa_iterations=500, optimize_overlap=True, num_seeds=5
    )
    ct = time.time() - st
    print(f"  Result: Vn={vn}, Sm={sm:.1f}, Nh={nh}, TD={td:.1f} in {ct:.1f}s")
    
    cache[f"{f}_alg2_paper"] = {
        "vn": vn,
        "sm": sm,
        "nh": nh,
        "td": td,
        "rtd": rtd,
        "best_routes": [list(r.sequence) for r in routes],
        "ct": ct
    }
    
    with open(cache_path, "w", encoding="utf-8") as json_file:
        json.dump(cache, json_file, indent=2, ensure_ascii=False)
        
    print("Successfully updated 277_stop.txt Alg 2 Paper Mode entry in cache!")

if __name__ == "__main__":
    main()
