import math
import random
from models import Route

class CapacitatedClustering:
    def __init__(self, vrp_data):
        self.d = vrp_data
        
    def _estimate_route_time(self, cluster_nodes):
        if not cluster_nodes: return 0.0
        dist = 0.0
        c = 0
        rem = list(cluster_nodes)
        dist_matrix = self.d.distance_matrix
        while rem:
            min_dist = float('inf')
            min_idx = -1
            min_node = -1
            for idx, node in enumerate(rem):
                d = dist_matrix[c][node]
                if d < min_dist:
                    min_dist = d
                    min_idx = idx
                    min_node = node
            dist += min_dist
            c = min_node
            rem[min_idx] = rem[-1]
            rem.pop()
            
        dist += dist_matrix[c][0]
        service_sum = sum(self.d.nodes[x].service for x in cluster_nodes)
        return dist / self.d.speed + service_sum
        
    def _tw_conflict(self, cluster_nodes, node_id):
        if not cluster_nodes: return False
        node = self.d.nodes[node_id]
        for ex_id in cluster_nodes:
            ex = self.d.nodes[ex_id]
            tv = self.d.travel_time(ex_id, node_id)
            arr_node = max(ex.early, self.d.start_time) + ex.service + tv
            arr_ex = max(node.early, self.d.start_time) + node.service + tv
            if arr_node > node.late and arr_ex > ex.late:
                return True
        return False
        
    def generate_clusters(self, stops, k, seed=42):
        """ Generate Capacitated N clusters (Section 5) """
        k = min(k, len(stops))
        if k == 0: return []
        
        random.seed(seed)
        centers = [(self.d.nodes[s.id].x, self.d.nodes[s.id].y) for s in random.sample(stops, k)]
        max_hours = self.d.depot.late - self.d.depot.early
        
        for iteration in range(30):
            assgn = [[] for _ in range(k)]
            cluster_times = [0.0] * k
            
            # Grand centroid
            gcx = sum(c[0] for c in centers) / k
            gcy = sum(c[1] for c in centers) / k
            
            sn = sorted(stops, key=lambda s: math.hypot(s.x - gcx, s.y - gcy), reverse=True)
            
            for stop in sn:
                # Find nearest centroid without size penalty
                ds = sorted([
                    (math.hypot(stop.x - c[0], stop.y - c[1]), i) 
                    for i, c in enumerate(centers)
                ])
                assigned = False
                
                def get_est_time(ci, stop_id):
                    cl = assgn[ci]
                    if not cl:
                        disp = self.d.get_closest_landfill(stop_id)
                        t = (self.d.travel_time(0, stop_id) + 
                             self.d.travel_time(stop_id, disp.id) + 
                             self.d.travel_time(disp.id, 0))
                        return t + self.d.nodes[stop_id].service
                    min_d = min(self.d.distance_matrix[x][stop_id] for x in cl)
                    return cluster_times[ci] + min_d / self.d.speed + self.d.nodes[stop_id].service

                # Round 1: All constraints (demand, max stops, TSP route time, TW conflict)
                for _, ci in ds:
                    cl = assgn[ci]
                    if len(cl) >= self.d.max_stops: continue
                    if sum(self.d.nodes[x].demand for x in cl) + stop.demand > self.d.route_capacity: continue
                    
                    est_time = get_est_time(ci, stop.id)
                    if est_time > max_hours: continue
                    
                    nearby = sorted(cl, key=lambda x: self.d.distance_matrix[stop.id][x])[:5]
                    if self._tw_conflict(nearby, stop.id): continue
                    
                    cluster_times[ci] = est_time
                    assgn[ci].append(stop.id)
                    assigned = True
                    break
                
                # Round 2: Relax TW conflict
                if not assigned:
                    for _, ci in ds:
                        cl = assgn[ci]
                        if len(cl) >= self.d.max_stops: continue
                        if sum(self.d.nodes[x].demand for x in cl) + stop.demand > self.d.route_capacity: continue
                        
                        est_time = get_est_time(ci, stop.id)
                        if est_time > max_hours: continue
                        
                        cluster_times[ci] = est_time
                        assgn[ci].append(stop.id)
                        assigned = True
                        break
                        
                # Round 3: Relax route time capacity
                if not assigned:
                    for _, ci in ds:
                        cl = assgn[ci]
                        if len(cl) >= self.d.max_stops: continue
                        if sum(self.d.nodes[x].demand for x in cl) + stop.demand > self.d.route_capacity: continue
                        
                        cluster_times[ci] = get_est_time(ci, stop.id)
                        assgn[ci].append(stop.id)
                        assigned = True
                        break
                        
                # Round 4: Absolute Fallback (assign to smallest cluster)
                if not assigned:
                    best_c = min(range(k), key=lambda i: len(assgn[i]))
                    cluster_times[best_c] = get_est_time(best_c, stop.id)
                    assgn[best_c].append(stop.id)
                    
            new_centers = []
            for i in range(k):
                if assgn[i]:
                    cx = sum(self.d.nodes[r].x for r in assgn[i]) / len(assgn[i])
                    cy = sum(self.d.nodes[r].y for r in assgn[i]) / len(assgn[i])
                    new_centers.append((cx, cy))
                else:
                    new_centers.append(centers[i])
            
            if new_centers == centers:
                break
            centers = new_centers
            
            # Recalculate exact cluster times for the next iteration
            for i in range(k):
                cluster_times[i] = self._estimate_route_time(assgn[i])
                
        # === HẬU XỬ LÝ: TÁI CÂN BẰNG CỤM (có kiểm tra Time Window) ===
        assgn = self._rebalance_clusters(assgn, k)
        
        return assgn
    
    def _rebalance_clusters(self, assgn, k):
        """
        Di chuyển trạm từ cụm lớn sang cụm nhỏ.
        Khác phiên bản trước: Kiểm tra Time Window TRƯỚC KHI di chuyển.
        Nếu trạm bị xung đột TW thì bỏ qua, tìm trạm khác.
        """
        total = sum(len(c) for c in assgn)
        if total == 0 or k <= 1: return assgn
        
        target_avg = total / k
        max_allowed = math.ceil(target_avg * 1.30)
        
        for _ in range(total):  # Tối đa N lần lặp
            sizes = [len(c) for c in assgn]
            largest_idx = max(range(k), key=lambda i: sizes[i])
            smallest_idx = min(range(k), key=lambda i: sizes[i])
            
            # Dừng khi đã đủ cân bằng
            if sizes[largest_idx] <= max_allowed:
                break
            if sizes[largest_idx] - sizes[smallest_idx] <= 2:
                break
            
            # Tìm tâm cụm nhỏ nhất
            if assgn[smallest_idx]:
                scx = sum(self.d.nodes[n].x for n in assgn[smallest_idx]) / len(assgn[smallest_idx])
                scy = sum(self.d.nodes[n].y for n in assgn[smallest_idx]) / len(assgn[smallest_idx])
            else:
                scx, scy = 0, 0
            
            # Sắp xếp các trạm trong cụm lớn nhất theo khoảng cách đến tâm cụm nhỏ nhất
            candidates = sorted(
                assgn[largest_idx],
                key=lambda n: math.hypot(self.d.nodes[n].x - scx, self.d.nodes[n].y - scy)
            )
            
            moved = False
            for node_id in candidates:
                # Kiểm tra Time Window: Trạm này có tương thích với cụm đích không?
                if self._tw_conflict(assgn[smallest_idx][:5], node_id):
                    continue  # Bỏ qua, tìm trạm khác
                
                # OK, di chuyển trạm
                assgn[largest_idx].remove(node_id)
                assgn[smallest_idx].append(node_id)
                moved = True
                break
            
            # Nếu không tìm được trạm nào tương thích, dừng vòng lặp
            if not moved:
                break
        
        return assgn
