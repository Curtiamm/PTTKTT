import math
import random
from models import Route

class CapacitatedClustering:
    def __init__(self, vrp_data):
        self.d = vrp_data
        
    def _estimate_route_time(self, cluster_nodes):
        if not cluster_nodes: return 0.0
        tt, c, rem = 0.0, 0, set(cluster_nodes)
        while rem:
            nxt = min(rem, key=lambda x: self.d.distance_matrix[c][x])
            tt += self.d.travel_time(c, nxt) + self.d.nodes[nxt].service
            c = nxt
            rem.remove(nxt)
        return tt + self.d.travel_time(c, 0)
        
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
        
    def generate_clusters(self, stops, k):
        """ Generate Capacitated N clusters (Section 5) """
        k = min(k, len(stops))
        if k == 0: return []
        
        centers = [(self.d.nodes[s.id].x, self.d.nodes[s.id].y) for s in random.sample(stops, k)]
        assgn = None
        
        for _ in range(30):
            assgn = [[] for _ in range(k)]
            cluster_tt = [0.0] * k
            cluster_last = [0] * k
            
            gcx = sum(c[0] for c in centers) / k
            gcy = sum(c[1] for c in centers) / k
            
            sn = sorted(stops, key=lambda s: math.hypot(s.x - gcx, s.y - gcy), reverse=True)
            
            # === CÂN BẰNG TẢI CÔNG VIỆC (Workload Balancing) ===
            # Trần cứng: Không xe nào được nhận quá 115% số trạm trung bình
            target_avg = len(stops) / k
            target_stops_max = math.ceil(target_avg * 1.30)  # Nới lỏng lên 130% để giảm Quãng đường (TD) thay vì quá cứng nhắc cân bằng
            
            for stop in sn:
                # Tiêu chí sắp xếp kết hợp: Khoảng cách + Phạt kích thước cụm
                # Cụm nào đã nhiều trạm sẽ bị đẩy xuống cuối danh sách ưu tiên
                max_dist = max(math.hypot(stop.x - c[0], stop.y - c[1]) for c in centers) or 1.0
                ds = sorted([
                    (math.hypot(stop.x - c[0], stop.y - c[1]) + (len(assgn[i]) / target_avg) * max_dist * 0.3, i) 
                    for i, c in enumerate(centers)
                ])
                assigned = False
                
                # Vòng 1: Gán vào cụm thỏa mãn TẤT CẢ ràng buộc (cân bằng tải + TW + capacity)
                for _, ci in ds:
                    cl = assgn[ci]
                    if len(cl) >= target_stops_max: continue
                    if len(cl) >= self.d.max_stops: continue
                    if sum(self.d.nodes[x].demand for x in cl) + stop.demand > self.d.route_capacity: continue
                    
                    est_add = self.d.travel_time(cluster_last[ci], stop.id) + self.d.nodes[stop.id].service
                    est_total = cluster_tt[ci] + est_add + self.d.travel_time(stop.id, 0)
                    if len(cl) > 5 and est_total > 11.0: continue
                    
                    nearby = sorted(cl, key=lambda x: self.d.distance_matrix[stop.id][x])[:5]
                    if self._tw_conflict(nearby, stop.id): continue
                    
                    assgn[ci].append(stop.id)
                    cluster_tt[ci] += est_add
                    cluster_last[ci] = stop.id
                    assigned = True
                    break
                
                # Vòng 2 (Nới lỏng TW): Bỏ kiểm tra Time Window, giữ cân bằng tải
                if not assigned:
                    for _, ci in ds:
                        cl = assgn[ci]
                        if len(cl) >= target_stops_max: continue
                        if len(cl) >= self.d.max_stops: continue
                        if sum(self.d.nodes[x].demand for x in cl) + stop.demand > self.d.route_capacity: continue
                        
                        assgn[ci].append(stop.id)
                        cluster_tt[ci] += self.d.travel_time(cluster_last[ci], stop.id) + self.d.nodes[stop.id].service
                        cluster_last[ci] = stop.id
                        assigned = True
                        break
                
                # Vòng 3 (Nới lỏng cân bằng): Bỏ giới hạn cân bằng, giữ capacity + max_stops
                if not assigned:
                    for _, ci in ds:
                        cl = assgn[ci]
                        if len(cl) >= self.d.max_stops: continue
                        if sum(self.d.nodes[x].demand for x in cl) + stop.demand > self.d.route_capacity: continue
                        
                        assgn[ci].append(stop.id)
                        cluster_tt[ci] += self.d.travel_time(cluster_last[ci], stop.id) + self.d.nodes[stop.id].service
                        cluster_last[ci] = stop.id
                        assigned = True
                        break
                        
                # Vòng 4 (Absolute Fallback): Nhét vào cụm NHỎ NHẤT (không phải gần nhất)
                if not assigned:
                    best_c = min(range(k), key=lambda i: len(assgn[i]))
                    assgn[best_c].append(stop.id)
                    cluster_tt[best_c] += self.d.travel_time(cluster_last[best_c], stop.id) + self.d.nodes[stop.id].service
                    cluster_last[best_c] = stop.id
                    
            new_centers = []
            for i in range(k):
                if assgn[i]:
                    cx = sum(self.d.nodes[r].x for r in assgn[i]) / len(assgn[i])
                    cy = sum(self.d.nodes[r].y for r in assgn[i]) / len(assgn[i])
                    new_centers.append((cx, cy))
                else:
                    new_centers.append(centers[i])
            centers = new_centers
            
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
