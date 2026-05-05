from models import Route

class ExtendedInsertion:
    def __init__(self, vrp_data):
        self.d = vrp_data
        
    def solve_route(self, unrouted_stops):
        if not unrouted_stops: return None
        
        full_route = Route()
        lunch_check = False
        current_time = self.d.start_time
        current_pos = 0 # Depot
        route_total_load = 0.0
        
        while unrouted_stops:
            feasible_seeds = []
            for n in unrouted_stops:
                tv = self.d.travel_time(current_pos, n)
                arr = max(current_time + tv, self.d.nodes[n].early)
                
                if route_total_load + self.d.nodes[n].demand > self.d.route_capacity:
                    continue
                    
                lc_temp = lunch_check
                if not lc_temp and arr >= self.d.start_time + 3.0:
                    arr = max(current_time + tv + self.d.lunch_duration, self.d.nodes[n].early)
                    lc_temp = True
                    
                if arr <= self.d.nodes[n].late:
                    feasible_seeds.append(n)
                    
            if not feasible_seeds:
                break
                
            seed_node_id = max(feasible_seeds, key=lambda n: (self.d.distance_matrix[current_pos][n], -self.d.nodes[n].late))
            
            tv = self.d.travel_time(current_pos, seed_node_id)
            arr = max(current_time + tv, self.d.nodes[seed_node_id].early)
            if not lunch_check and arr >= self.d.start_time + 3.0:
                current_time += self.d.lunch_duration
                lunch_check = True
                arr = max(current_time + tv, self.d.nodes[seed_node_id].early)
                
            current_sub_route = [seed_node_id]
            unrouted_stops.remove(seed_node_id)
            
            current_time = arr + self.d.nodes[seed_node_id].service
            route_total_load += self.d.nodes[seed_node_id].demand
            current_pos = seed_node_id
            
            while unrouted_stops:
                best_node_id = None
                best_score = float('inf')
                
                for node_id in unrouted_stops:
                    node = self.d.nodes[node_id]
                    if route_total_load + node.demand > self.d.route_capacity:
                        continue
                        
                    travel = self.d.travel_time(current_pos, node_id)
                    arr = max(current_time + travel, node.early)
                    
                    if arr <= node.late:
                        score = travel + (arr - current_time - travel)
                        if score < best_score:
                            best_score = score
                            best_node_id = node_id
                            
                if best_node_id is not None:
                    node = self.d.nodes[best_node_id]
                    travel = self.d.travel_time(current_pos, best_node_id)
                    arr = max(current_time + travel, node.early)
                    
                    if not lunch_check and arr >= self.d.start_time + 3.0:
                        current_time += self.d.lunch_duration
                        lunch_check = True
                        arr = max(current_time + travel, node.early)
                        
                    current_sub_route.append(best_node_id)
                    unrouted_stops.remove(best_node_id)
                    current_time = arr + node.service
                    route_total_load += node.demand
                    current_pos = best_node_id
                else:
                    break
                    
            temp_load = 0.0
            for idx, node_id in enumerate(current_sub_route):
                node = self.d.nodes[node_id]
                if temp_load + node.demand > self.d.vehicle_capacity:
                    for rem in current_sub_route[idx:]:
                        unrouted_stops.add(rem)
                        route_total_load -= self.d.nodes[rem].demand
                    current_sub_route = current_sub_route[:idx]
                    break
                else:
                    temp_load += node.demand
                    
            for node_id in current_sub_route:
                full_route.add(node_id)
                
            if current_sub_route:
                last_node = current_sub_route[-1]
                disp = self.d.get_closest_landfill(last_node)
                current_time += self.d.travel_time(last_node, disp.id) + disp.service
                current_pos = disp.id
            
        if full_route.is_empty():
            return None
            
        return full_route
