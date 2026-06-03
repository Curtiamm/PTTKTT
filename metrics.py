import math

class MetricsCalculator:
    def __init__(self, data):
        self.d = data
        
    def calc_td(self, routes):
        total_dist = 0.0
        for r in routes:
            if r.is_empty(): continue
            curr = 0
            ld = 0.0
            for node_id in r:
                if ld + self.d.nodes[node_id].demand > self.d.vehicle_capacity:
                    disp = self.d.get_closest_landfill(curr)
                    total_dist += self.d.distance_matrix[curr][disp.id]
                    curr = disp.id
                    ld = 0.0
                total_dist += self.d.distance_matrix[curr][node_id]
                curr = node_id
                ld += self.d.nodes[node_id].demand
            disp = self.d.get_closest_landfill(curr)
            total_dist += self.d.distance_matrix[curr][disp.id] + self.d.distance_matrix[disp.id][0]
        return total_dist

    def calc_rtd(self, routes):
        rtds = []
        for r in routes:
            if r.is_empty(): continue
            curr_time = self.d.start_time
            curr_pos = 0
            ld = 0.0
            lunch_check = False
            
            for node_id in r:
                node = self.d.nodes[node_id]
                
                if ld + node.demand > self.d.vehicle_capacity:
                    disp = self.d.get_closest_landfill(curr_pos)
                    tv = self.d.travel_time(curr_pos, disp.id)
                    curr_time += tv + disp.service
                    curr_pos = disp.id
                    ld = 0.0
                    
                tv = self.d.travel_time(curr_pos, node_id)
                arr = max(curr_time + tv, node.early)
                
                if not lunch_check and arr >= self.d.start_time + 3.0:
                    curr_time += self.d.lunch_duration
                    lunch_check = True
                    arr = max(curr_time + tv, node.early)
                    
                curr_time = arr + node.service
                curr_pos = node_id
                ld += node.demand
                
            disp = self.d.get_closest_landfill(curr_pos)
            curr_time += self.d.travel_time(curr_pos, disp.id) + disp.service
            curr_time += self.d.travel_time(disp.id, 0)
            
            rtds.append((curr_time - self.d.start_time) * 3600.0)
            
        return max(rtds) - min(rtds) if rtds else 0.0

    def calc_violations(self, routes):
        tw_viols = 0
        cap_viols = 0
        
        for r in routes:
            if r.is_empty(): continue
            
            # Check capacity violations
            if len(r) > self.d.max_stops:
                cap_viols += (len(r) - self.d.max_stops) * 10
            
            route_load = sum(self.d.nodes[n].demand for n in r)
            if route_load > self.d.route_capacity:
                cap_viols += (route_load - self.d.route_capacity) * 2
                
            curr_time = self.d.start_time
            curr_pos = 0
            ld = 0.0
            lunch_check = False
            
            for node_id in r:
                node = self.d.nodes[node_id]
                
                if ld + node.demand > self.d.vehicle_capacity:
                    disp = self.d.get_closest_landfill(curr_pos)
                    tv = self.d.travel_time(curr_pos, disp.id)
                    curr_time += tv + disp.service
                    curr_pos = disp.id
                    ld = 0.0
                    
                tv = self.d.travel_time(curr_pos, node_id)
                arr = curr_time + tv
                
                if arr > node.late:
                    tw_viols += 1
                    
                arr = max(arr, node.early)
                
                if not lunch_check and arr >= self.d.start_time + 3.0:
                    curr_time += self.d.lunch_duration
                    lunch_check = True
                    arr = max(curr_time + tv, node.early)
                    if curr_time + tv > node.late:
                        tw_viols += 1
                        
                curr_time = arr + node.service
                curr_pos = node_id
                ld += node.demand
                
            disp = self.d.get_closest_landfill(curr_pos)
            curr_time += self.d.travel_time(curr_pos, disp.id) + disp.service
            curr_time += self.d.travel_time(disp.id, 0)
            
            # Route duration capacity
            if (curr_time - self.d.start_time) > 11.0:
                cap_viols += int(curr_time - self.d.start_time - 11.0) * 10
                
        return tw_viols, cap_viols


    def calc_shape_metric(self, routes):
        sm = 0.0
        for r in routes:
            if r.is_empty(): continue
            cx = sum(self.d.nodes[n].x for n in r) / len(r)
            cy = sum(self.d.nodes[n].y for n in r) / len(r)
            sm += sum(math.hypot(self.d.nodes[n].x - cx, self.d.nodes[n].y - cy) for n in r)
        return sm

    def _cross_product(self, p1, p2, p3):
        return (p2[0]-p1[0])*(p3[1]-p1[1]) - (p2[1]-p1[1])*(p3[0]-p1[0])

    def calc_nh(self, routes):
        hulls = []
        for r in routes:
            if len(r) < 3: 
                hulls.append([])
                continue
            pts = sorted([(self.d.nodes[n].x, self.d.nodes[n].y) for n in r])
            lw, up = [], []
            for p in pts:
                while len(lw) >= 2 and self._cross_product(lw[-2], lw[-1], p) <= 0: lw.pop()
                lw.append(p)
            for p in reversed(pts):
                while len(up) >= 2 and self._cross_product(up[-2], up[-1], p) <= 0: up.pop()
                up.append(p)
            hulls.append(lw[:-1] + up[:-1])
            
        nh = 0
        for stop in self.d.stops:
            cx, cy = stop.x, stop.y
            inc = 0
            for h in hulls:
                if len(h) < 3: continue
                inside = False
                p1x, p1y = h[0]
                for i in range(1, len(h) + 1):
                    p2x, p2y = h[i % len(h)]
                    if cy > min(p1y, p2y) and cy <= max(p1y, p2y) and cx <= max(p1x, p2x):
                        if p1y != p2y:
                            xint = (cy - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or cx <= xint: inside = not inside
                    p1x, p1y = p2x, p2y
                if inside: inc += 1
            if inc > 1: nh += 1
        return nh
