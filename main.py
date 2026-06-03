import os
import time
import math
import random
import copy
from parser import load_benchmark
from clustering import CapacitatedClustering
from insertion import ExtendedInsertion
from metrics import MetricsCalculator
from models import Route

class VRPTWSolver:
    def __init__(self, vrp_data):
        self.d = vrp_data
        self.clustering = CapacitatedClustering(self.d)
        self.insertion = ExtendedInsertion(self.d)
        self.metrics = MetricsCalculator(self.d)
        
    def _sa_optimize(self, routes, iterations=100, optimize_overlap=False):
        # Step 6: Enhanced SA meta-heuristic with ALNS operators
        
        # Soft cost function
        def calc_soft_cost(rts):
            td = self.metrics.calc_td(rts)
            tw_viols, cap_viols = self.metrics.calc_violations(rts)
            # Soft penalty: 50.0 per violation to allow search space transitions
            penalty = (tw_viols + cap_viols) * 50.0
            if optimize_overlap:
                nh = self.metrics.calc_nh(rts)
                return td + (nh * 25.0) + penalty
            return td + penalty
            
        best_feasible_routes = [Route(list(r.sequence)) for r in routes]
        best_feasible_cost = calc_soft_cost(best_feasible_routes)
        
        curr_routes = [Route(list(r.sequence)) for r in routes]
        curr_cost = calc_soft_cost(curr_routes)
        
        temp = 100.0  
        cooling = math.pow(0.001, 1.0 / max(1, iterations)) 
        
        for it in range(iterations):
            valid_routes = [i for i, r in enumerate(curr_routes) if not r.is_empty()]
            if not valid_routes: break
            
            new_routes = [Route(list(r.sequence)) for r in curr_routes]
            # Vary seed per iteration to avoid repeatable paths in SA
            random.seed(42 + it)
            op = random.random()
            
            if op < 0.25 and len(valid_routes) >= 2:
                # 1. RELOCATE
                r1, r2 = random.sample(valid_routes, 2)
                seq1, seq2 = list(new_routes[r1].sequence), list(new_routes[r2].sequence)
                if seq1:
                    idx1 = random.randint(0, len(seq1) - 1)
                    node = seq1.pop(idx1)
                    idx2 = random.randint(0, len(seq2))
                    seq2.insert(idx2, node)
                    new_routes[r1], new_routes[r2] = Route(seq1), Route(seq2)
            elif op < 0.50 and len(valid_routes) >= 2:
                # 2. SWAP
                r1, r2 = random.sample(valid_routes, 2)
                seq1, seq2 = list(new_routes[r1].sequence), list(new_routes[r2].sequence)
                if seq1 and seq2:
                    idx1, idx2 = random.randint(0, len(seq1) - 1), random.randint(0, len(seq2) - 1)
                    seq1[idx1], seq2[idx2] = seq2[idx2], seq1[idx1]
                    new_routes[r1], new_routes[r2] = Route(seq1), Route(seq2)
            elif op < 0.75:
                # 3. 2-OPT
                r1 = random.choice(valid_routes)
                seq1 = list(new_routes[r1].sequence)
                if len(seq1) > 2:
                    idx1 = random.randint(0, len(seq1) - 2)
                    idx2 = random.randint(idx1 + 1, len(seq1) - 1)
                    seq1[idx1:idx2+1] = reversed(seq1[idx1:idx2+1])
                    new_routes[r1] = Route(seq1)
            else:
                # 4. CROSS EXCHANGE
                if len(valid_routes) >= 2:
                    r1, r2 = random.sample(valid_routes, 2)
                    seq1, seq2 = list(new_routes[r1].sequence), list(new_routes[r2].sequence)
                    if len(seq1) > 1 and len(seq2) > 1:
                        i1, i2 = random.randint(1, len(seq1) - 1), random.randint(1, len(seq2) - 1)
                        new_routes[r1] = Route(seq1[:i1] + seq2[i2:])
                        new_routes[r2] = Route(seq2[:i2] + seq1[i1:])
            
            new_cost = calc_soft_cost(new_routes)
            
            # Acceptance criteria
            if new_cost < curr_cost or math.exp((curr_cost - new_cost) / temp) > random.random():
                curr_routes = new_routes
                curr_cost = new_cost
                
                # If the new solution is fully feasible and has a better cost, update best_feasible_routes
                tw, cap = self.metrics.calc_violations(new_routes)
                if tw == 0 and cap == 0:
                    new_cost = calc_soft_cost(new_routes)
                    if new_cost < best_feasible_cost:
                        best_feasible_routes = [Route(list(r.sequence)) for r in new_routes]
                        best_feasible_cost = new_cost
            temp *= cooling
            
        return best_feasible_routes

    def solve(self, algo_type=2, initial_vehicles=3, sa_iterations=10, optimize_overlap=False, num_seeds=5):
        n_list = [s for s in self.d.stops]
        final_routes = []
        
        # Algorithm 1: Solomon Insertion without initial clustering
        if algo_type == 1:
            routes = []
            unrouted = set(s.id for s in n_list)
            while unrouted:
                route_obj = self.insertion.solve_route(unrouted)
                if not route_obj or route_obj.is_empty():
                    break
                routes.append(route_obj)
                for n in route_obj:
                    if n in unrouted:
                        unrouted.remove(n)
            final_routes = routes
            
        # Algorithm 2: Clustering-based (Cluster-First, Route-Second)
        else:
            # Calculate theoretical minimum N based on capacity and stops limit
            min_n_capacity = sum(s.demand for s in self.d.stops) / max(1.0, self.d.route_capacity)
            min_n_stops = len(self.d.stops) / max(1.0, self.d.max_stops)
            lower_bound_N = math.ceil(max(min_n_capacity, min_n_stops))
            N = max(initial_vehicles, lower_bound_N)
            
            best_routes = None
            best_vn = float('inf')
            best_td = float('inf')
            
            # Search over K-Means seeds to find the most route-feasible initial configuration
            for seed in range(num_seeds):
                curr_N = N
                while True:
                    assgn = self.clustering.generate_clusters(n_list, curr_N, seed=seed)
                    clusters = [list(c) for c in assgn]
                    
                    routes = []
                    unrouted = set(s.id for s in n_list)
                    
                    # Step 2: Build routes and reassign leftovers
                    for n in range(curr_N):
                        cluster_unrouted = [x for x in clusters[n] if x in unrouted]
                        cluster_unrouted_set = set(cluster_unrouted)
                        
                        if not cluster_unrouted_set:
                            routes.append(Route())
                            continue
                            
                        route_obj = self.insertion.solve_route(cluster_unrouted_set)
                        
                        if not route_obj or route_obj.is_empty():
                            leftovers = list(cluster_unrouted)
                            routes.append(Route())
                        else:
                            routes.append(route_obj)
                            for node_id in route_obj:
                                unrouted.discard(node_id)
                            leftovers = [x for x in cluster_unrouted if x in unrouted]
                            
                        # Reassign leftovers to closest non-finalized cluster
                        if leftovers and n < curr_N - 1:
                            remaining_centroids = {}
                            for m in range(n + 1, curr_N):
                                active_nodes = [x for x in clusters[m] if x in unrouted]
                                if active_nodes:
                                    cx = sum(self.d.nodes[x].x for x in active_nodes) / len(active_nodes)
                                    cy = sum(self.d.nodes[x].y for x in active_nodes) / len(active_nodes)
                                    remaining_centroids[m] = (cx, cy)
                                else:
                                    if clusters[m]:
                                        cx = sum(self.d.nodes[x].x for x in clusters[m]) / len(clusters[m])
                                        cy = sum(self.d.nodes[x].y for x in clusters[m]) / len(clusters[m])
                                        remaining_centroids[m] = (cx, cy)
                                    else:
                                        remaining_centroids[m] = (self.d.depot.x, self.d.depot.y)
                                        
                            for stop_id in leftovers:
                                stop_node = self.d.nodes[stop_id]
                                closest_m = min(
                                    remaining_centroids.keys(),
                                    key=lambda m: math.hypot(stop_node.x - remaining_centroids[m][0], stop_node.y - remaining_centroids[m][1])
                                )
                                clusters[closest_m].append(stop_id)
                                
                    actual_unrouted = [x for x in unrouted]
                    if not actual_unrouted:
                        break
                    else:
                        curr_N += 1
                        if curr_N > N + 2:
                            break
                            
                valid_routes = [r for r in routes if not r.is_empty()]
                vn = len(valid_routes)
                td = self.metrics.calc_td(valid_routes)
                
                # Pick the configuration that minimizes Vn, then TD
                if vn < best_vn or (vn == best_vn and td < best_td):
                    best_vn = vn
                    best_td = td
                    best_routes = valid_routes
                    
            final_routes = best_routes
                
        # Step 6: Improve routes
        best_routes = self._sa_optimize(final_routes, iterations=sa_iterations, optimize_overlap=optimize_overlap)
        
        vn = len([r for r in best_routes if not r.is_empty()])
        td = self.metrics.calc_td(best_routes)
        rtd = self.metrics.calc_rtd(best_routes)
        sm = self.metrics.calc_shape_metric(best_routes)
        nh = self.metrics.calc_nh(best_routes)
        
        return vn, sm, nh, td, rtd, best_routes

# Known benchmark values from Table 3 for exact synchronization
benchmarks = {
    "102_stop.txt":  {1: (2,  869.4,   55,  218.4, 22296), 2: (3,  399.1,    0,  205.1,  9903)},
    "277_stop.txt":  {1: (3,  858.0,  208,  521.9, 13843), 2: (3,  385.9,  104,  527.3,  4201)},
    "335_stop.txt":  {1: (5,  410.4,  225,  191.1,  2377), 2: (6,  243.3,    0,  205.0,  8983)},
    "444_stop.txt":  {1: (10,  70.0,  291,   82.9,  2422), 2: (11,  28.5,    1,   87.0,  2636)},
    "804_stop.txt":  {1: (5, 3793.5,  675,  798.9, 32741), 2: (5, 2350.4,  264,  769.5, 18047)}
}

if __name__ == '__main__':
    d = os.path.join("Code GitHub", "WCVRPTW-benchmark-main", "instances")
    files = sorted([f for f in os.listdir(d) if f.endswith('.txt') and f in benchmarks], key=lambda x: int(x.split('_')[0]))
    
    print("-" * 88)
    print(f"{'Problem set':<16} | {'A':>1} | {'Vn':>4} | {'Sm(mile)':>10} | {'Nh':>4} | {'TD(mile)':>10} | {'RTD(sec)':>10} | {'CT(sec)':>7}")
    print("-" * 88)
    
    for f in files:
        data = load_benchmark(os.path.join(d, f))
        solver = VRPTWSolver(data)
        
        for algo_type in [1, 2]:
            st = time.time()
            vn, sm, nh, td, rtd, best_routes = solver.solve(algo_type=algo_type)
            ct = time.time() - st
            
            # ĐÃ BỎ GHI ĐÈ KẾT QUẢ BENCHMARK (OVERRIDE)
            # Để console in ra các con số "phá kỷ lục" thực tế mà cậu chạy được
            # if f in benchmarks and algo_type in benchmarks[f]:
            #     vn, sm, nh, td, rtd = benchmarks[f][algo_type]
                
            if algo_type == 1:
                print(f"{f:<16} | {algo_type:1d} | {vn:4d} | {sm:10.1f} | {nh:4d} | {td:10.1f} | {int(rtd):10d} | {ct:7.3f}")
            else:
                print(f"{'':<16} | {algo_type:1d} | {vn:4d} | {sm:10.1f} | {nh:4d} | {td:10.1f} | {int(rtd):10d} | {ct:7.3f}")
                
    print("-" * 88)
