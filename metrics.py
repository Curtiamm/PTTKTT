import math

class MetricsCalculator:
    def __init__(self, data):
        self.d = data
        self.hull_cache = {}
        
    def calc_td(self, routes):
        total_dist = 0.0
        for r in routes:
            if r.is_empty(): continue
            curr = 0
            ld = 0.0
            for node_id in r:
                node = self.d.nodes[node_id]
                if ld + node.demand > self.d.vehicle_capacity:
                    disp = self.d.get_closest_landfill(curr)
                    # Euclidean distance calculation
                    total_dist += math.hypot(self.d.nodes[curr].x - disp.x, self.d.nodes[curr].y - disp.y)
                    curr = disp.id
                    ld = 0.0
                total_dist += math.hypot(self.d.nodes[curr].x - node.x, self.d.nodes[curr].y - node.y)
                curr = node_id
                ld += node.demand
            disp = self.d.get_closest_landfill(curr)
            total_dist += math.hypot(self.d.nodes[curr].x - disp.x, self.d.nodes[curr].y - disp.y)
            total_dist += math.hypot(disp.x - self.d.depot.x, disp.y - self.d.depot.y)
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
                arr = curr_time + tv
                
                if not lunch_check:
                    if curr_time >= 11.0:
                        lunch_start = max(11.0, curr_time)
                        if lunch_start <= 12.0:
                            curr_time = lunch_start + self.d.lunch_duration
                            lunch_check = True
                            arr = curr_time + tv
                    elif arr >= 11.0:
                        lunch_start = max(11.0, arr)
                        if lunch_start <= 12.0:
                            arr = lunch_start + self.d.lunch_duration
                            lunch_check = True
                            
                curr_time = max(arr, node.early) + node.service
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
        
        max_hours = self.d.depot.late - self.d.depot.early
        
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
                
                if not lunch_check:
                    if curr_time >= 11.0:
                        lunch_start = max(11.0, curr_time)
                        if lunch_start <= 12.0:
                            curr_time = lunch_start + self.d.lunch_duration
                            lunch_check = True
                            arr = curr_time + tv
                    elif arr >= 11.0:
                        lunch_start = max(11.0, arr)
                        if lunch_start <= 12.0:
                            arr = lunch_start + self.d.lunch_duration
                            lunch_check = True
                            
                if arr > node.late:
                    tw_viols += 1
                    
                curr_time = max(arr, node.early) + node.service
                curr_pos = node_id
                ld += node.demand
                
            disp = self.d.get_closest_landfill(curr_pos)
            curr_time += self.d.travel_time(curr_pos, disp.id) + disp.service
            curr_time += self.d.travel_time(disp.id, 0)
            
            # Route duration capacity check using dynamic depot hours
            if (curr_time - self.d.start_time) > max_hours:
                cap_viols += int(curr_time - self.d.start_time - max_hours) * 10
                
        return tw_viols, cap_viols
                
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
        hull_bboxes = []
        for r in routes:
            if len(r) < 3: 
                hulls.append([])
                hull_bboxes.append((0.0, 0.0, 0.0, 0.0))
                continue
                
            key = tuple(sorted(r.sequence))
            if key in self.hull_cache:
                h, bbox = self.hull_cache[key]
            else:
                pts = sorted([(self.d.nodes[n].x, self.d.nodes[n].y) for n in r])
                lw, up = [], []
                for p in pts:
                    while len(lw) >= 2 and self._cross_product(lw[-2], lw[-1], p) <= 0: lw.pop()
                    lw.append(p)
                for p in reversed(pts):
                    while len(up) >= 2 and self._cross_product(up[-2], up[-1], p) <= 0: up.pop()
                    up.append(p)
                h = lw[:-1] + up[:-1]
                
                if h:
                    xs = [pt[0] for pt in h]
                    ys = [pt[1] for pt in h]
                    bbox = (min(xs), max(xs), min(ys), max(ys))
                else:
                    bbox = (0.0, 0.0, 0.0, 0.0)
                self.hull_cache[key] = (h, bbox)
                
            hulls.append(h)
            hull_bboxes.append(bbox)
            
        nh = 0
        for stop in self.d.stops:
            cx, cy = stop.x, stop.y
            inc = 0
            for h, bbox in zip(hulls, hull_bboxes):
                if len(h) < 3: continue
                # Bounding box pre-filter
                min_x, max_x, min_y, max_y = bbox
                if not (min_x <= cx <= max_x and min_y <= cy <= max_y):
                    continue
                
                inside = False
                p1x, p1y = h[0]
                n = len(h)
                for i in range(1, n):
                    p2x, p2y = h[i]
                    if cy > min(p1y, p2y) and cy <= max(p1y, p2y) and cx <= max(p1x, p2x):
                        if p1y != p2y:
                            xint = (cy - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or cx <= xint: inside = not inside
                    p1x, p1y = p2x, p2y
                    
                p2x, p2y = h[0]
                if cy > min(p1y, p2y) and cy <= max(p1y, p2y) and cx <= max(p1x, p2x):
                    if p1y != p2y:
                        xint = (cy - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or cx <= xint: inside = not inside
                        
                if inside: inc += 1
            if inc > 1: nh += 1
        return nh
