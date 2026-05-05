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
            
            for stop in sn:
                ds = sorted([(math.hypot(stop.x - c[0], stop.y - c[1]), i) for i, c in enumerate(centers)])
                assigned = False
                for _, ci in ds:
                    cl = assgn[ci]
                    
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
                    
                if not assigned:
                    best_c = ds[0][1]
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
            
        return assgn
