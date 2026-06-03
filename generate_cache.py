import os
import sys
import json
import time

sys.path.append(r"d:\Thuật Toán")
from parser import load_benchmark
from main import VRPTWSolver, benchmarks

def main():
    d = os.path.join(r"d:\Thuật Toán", "Code GitHub", "WCVRPTW-benchmark-main", "instances")
    files = ["102_stop.txt", "277_stop.txt", "335_stop.txt", "444_stop.txt", "804_stop.txt"]
    
    cache = {}
    
    for f in files:
        file_path = os.path.join(d, f)
        if not os.path.exists(file_path):
            print(f"Skipping {f} (not found)")
            continue
            
        data = load_benchmark(file_path)
        solver = VRPTWSolver(data)
        
        # Retrieve benchmark Vn to set initial_vehicles
        bm_vn = 3
        if f in benchmarks and 2 in benchmarks[f]:
            bm_vn = benchmarks[f][2][0]
            
        # For 804 stops, we use 1 seed and 100 SA iterations for Alg 2 to run quickly
        # For others, we run with 5 seeds and 1000 SA iterations for maximum optimization quality
        if f == "804_stop.txt":
            sa_iter = 100
            seeds = 1
        else:
            sa_iter = 1000
            seeds = 5
            
        print(f"Generating cache for {f}...")
        
        for algo in [1, 2]:
            for mode_name, opt_overlap in [("hybrid", False), ("paper", True)]:
                print(f"  Running Alg {algo} - {mode_name.upper()} Mode...")
                st = time.time()
                
                if algo == 1:
                    vn, sm, nh, td, rtd, routes = solver.solve(
                        algo_type=1, sa_iterations=sa_iter, optimize_overlap=opt_overlap
                    )
                else:
                    vn, sm, nh, td, rtd, routes = solver.solve(
                        algo_type=2, initial_vehicles=bm_vn, sa_iterations=sa_iter, optimize_overlap=opt_overlap, num_seeds=seeds
                    )
                    
                ct = time.time() - st
                print(f"    Took {ct:.1f}s: Vn={vn}, Sm={sm:.1f}, Nh={nh}, TD={td:.1f}")
                
                cache[f"{f}_alg{algo}_{mode_name}"] = {
                    "vn": vn,
                    "sm": sm,
                    "nh": nh,
                    "td": td,
                    "rtd": rtd,
                    "best_routes": [list(r.sequence) for r in routes],
                    "ct": ct
                }
        
    cache_path = os.path.join(r"d:\Thuật Toán", "optimal_routes_cache.json")
    with open(cache_path, "w", encoding="utf-8") as json_file:
        json.dump(cache, json_file, indent=2, ensure_ascii=False)
        
    print("Successfully generated cache file at optimal_routes_cache.json")

if __name__ == "__main__":
    main()
