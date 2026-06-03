from models import Route

class ExtendedInsertion:
    def __init__(self, vrp_data):
        self.d = vrp_data
        
    def check_sequence_feasible(self, seq):
        curr_time = self.d.start_time
        curr_pos = 0
        route_load = 0.0
        vehicle_load = 0.0
        lunch_check = False
        
        max_hours = self.d.depot.late - self.d.depot.early
        
        for idx, node_id in enumerate(seq):
            if idx == 0:
                continue
                
            node = self.d.nodes[node_id]
            
            if node.type == 2:
                tv = self.d.travel_time(curr_pos, node_id)
                # Check lunch before travel to landfill
                if not lunch_check and curr_time >= 11.0:
                    lunch_start = max(11.0, curr_time)
                    if lunch_start <= 12.0:
                        curr_time = lunch_start + self.d.lunch_duration
                        lunch_check = True
                
                curr_time += tv + node.service
                curr_pos = node_id
                vehicle_load = 0.0
                continue
                
            if vehicle_load + node.demand > self.d.vehicle_capacity:
                return False, "vehicle_capacity"
            if route_load + node.demand > self.d.route_capacity:
                return False, "route_capacity"
                
            tv = self.d.travel_time(curr_pos, node.id)
            arr = curr_time + tv
            
            if not lunch_check:
                # Option A: Take lunch before travel
                if curr_time >= 11.0:
                    lunch_start = max(11.0, curr_time)
                    if lunch_start <= 12.0:
                        curr_time = lunch_start + self.d.lunch_duration
                        lunch_check = True
                        arr = curr_time + tv
                # Option B: Take lunch after arrival but before service
                elif arr >= 11.0:
                    lunch_start = max(11.0, arr)
                    if lunch_start <= 12.0:
                        arr = lunch_start + self.d.lunch_duration
                        lunch_check = True
            
            if arr > node.late:
                return False, f"time_window_late_{node_id}"
                
            curr_time = max(arr, node.early) + node.service
            curr_pos = node_id
            vehicle_load += node.demand
            route_load += node.demand
            
        if curr_pos != 0:
            if not lunch_check and curr_time >= 11.0:
                lunch_start = max(11.0, curr_time)
                if lunch_start <= 12.0:
                    curr_time = lunch_start + self.d.lunch_duration
                    lunch_check = True
            disp = self.d.get_closest_landfill(curr_pos)
            curr_time += self.d.travel_time(curr_pos, disp.id) + disp.service
            curr_time += self.d.travel_time(disp.id, 0)
            
        if (curr_time - self.d.start_time) > max_hours:
            return False, "route_duration"
            
        return True, curr_time

    def solve_route(self, unrouted_stops, initial_seed=None):
        if not unrouted_stops: return None
        
        # Convert to set if it is list
        unrouted_stops = set(unrouted_stops)
        
        # Step 3: Initialize route sequence with a seed stop
        if initial_seed is not None and initial_seed in unrouted_stops:
            seed = initial_seed
        else:
            # Choose seed: farthest stop from depot
            feasible_seeds = []
            for n in unrouted_stops:
                feasible, _ = self.check_sequence_feasible([0, n, self.d.get_closest_landfill(n).id, 0])
                if feasible:
                    feasible_seeds.append(n)
            if not feasible_seeds:
                return None
            seed = max(feasible_seeds, key=lambda n: (self.d.distance_matrix[0][n], -self.d.nodes[n].late))
            
        unrouted_stops.remove(seed)
        disp = self.d.get_closest_landfill(seed)
        seq = [0, seed, disp.id, 0]
        
        max_hours = self.d.depot.late - self.d.depot.early
        
        while unrouted_stops:
            # Quick stop count check
            current_customer_count = sum(1 for n in seq if self.d.nodes[n].type == 1)
            if current_customer_count + 1 > self.d.max_stops:
                break
                
            # Precompute current route load
            route_load = sum(self.d.nodes[n].demand for n in seq if self.d.nodes[n].type == 1)
            
            # Precompute prefix states for seq
            # prefix_states[idx] will store the state AFTER serving node at seq[idx].
            prefix_states = []
            curr_time = self.d.start_time
            curr_pos = 0
            vehicle_load = 0.0
            r_load = 0.0
            lunch_check = False
            
            for idx, node_id in enumerate(seq):
                if idx == 0:
                    prefix_states.append((curr_time, curr_pos, vehicle_load, r_load, lunch_check, curr_time))
                    continue
                    
                node = self.d.nodes[node_id]
                if node.type == 2:
                    tv = self.d.travel_time(curr_pos, node_id)
                    if not lunch_check and curr_time >= 11.0:
                        lunch_start = max(11.0, curr_time)
                        if lunch_start <= 12.0:
                            curr_time = lunch_start + self.d.lunch_duration
                            lunch_check = True
                    curr_time += tv + node.service
                    curr_pos = node_id
                    vehicle_load = 0.0
                    arr_time = curr_time
                else:
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
                    vehicle_load += node.demand
                    r_load += node.demand
                    arr_time = arr
                    
                prefix_states.append((curr_time, curr_pos, vehicle_load, r_load, lunch_check, arr_time))
            # Compute latest arrival times backwards (conservative filter)
            n_seq = len(seq)
            latest_arrival = [0.0] * n_seq
            latest_arrival[n_seq-1] = min(self.d.depot.late, self.d.start_time + max_hours)
            for j in range(n_seq-2, -1, -1):
                next_node = seq[j+1]
                curr_node = seq[j]
                tv = self.d.travel_time(curr_node, next_node)
                service = self.d.nodes[curr_node].service
                latest_dep = latest_arrival[j+1] - tv
                latest_arrival[j] = min(self.d.nodes[curr_node].late, latest_dep - service)

            best_node = None
            best_pos = -1
            best_score = float('inf')
            
            # Parameters for Solomon I1
            mu = 1.0
            
            for u in unrouted_stops:
                u_node = self.d.nodes[u]
                # Quick capacity check
                if route_load + u_node.demand > self.d.route_capacity:
                    continue
                    
                for i in range(1, len(seq) - 1):
                    # Fast check: prefix state up to i-1
                    c_time, c_pos, v_load, r_ld, l_check = prefix_states[i-1][:5]
                    
                    # 1. Insert u
                    if v_load + u_node.demand > self.d.vehicle_capacity:
                        continue
                    
                    tv = self.d.travel_time(c_pos, u)
                    arr = c_time + tv
                    
                    # Lunch break propagation
                    u_l_check = l_check
                    if not u_l_check:
                        if c_time >= 11.0:
                            lunch_start = max(11.0, c_time)
                            if lunch_start <= 12.0:
                                c_time = lunch_start + self.d.lunch_duration
                                u_l_check = True
                                arr = c_time + tv
                        elif arr >= 11.0:
                            lunch_start = max(11.0, arr)
                            if lunch_start <= 12.0:
                                arr = lunch_start + self.d.lunch_duration
                                u_l_check = True
                                
                    if arr > u_node.late:
                        continue
                        
                    u_time = max(arr, u_node.early) + u_node.service
                    u_pos = u
                    u_v_load = v_load + u_node.demand
                    u_r_load = r_ld + u_node.demand
                    
                    # Estimate arrival time at seq[i] after visiting u
                    arr_i_new = u_time + self.d.travel_time(u, seq[i])
                    # O(1) filter check
                    if arr_i_new > latest_arrival[i]:
                        continue
                    
                    # 2. Propagate through the rest of the sequence
                    feasible = True
                    curr_t, curr_p, veh_l, rt_l, lun_c = u_time, u_pos, u_v_load, u_r_load, u_l_check
                    
                    for idx_in_seq in range(i, len(seq)):
                        node_id = seq[idx_in_seq]
                        node = self.d.nodes[node_id]
                        orig_arr = prefix_states[idx_in_seq][5]
                        
                        if node.type == 2:
                            tv = self.d.travel_time(curr_p, node_id)
                            if not lun_c and curr_t >= 11.0:
                                lunch_start = max(11.0, curr_t)
                                if lunch_start <= 12.0:
                                    curr_t = lunch_start + self.d.lunch_duration
                                    lun_c = True
                            curr_t += tv + node.service
                            curr_p = node_id
                            veh_l = 0.0
                            arr_time = curr_t
                        else:
                            if veh_l + node.demand > self.d.vehicle_capacity:
                                feasible = False
                                break
                            tv = self.d.travel_time(curr_p, node_id)
                            arr = curr_t + tv
                            if not lun_c:
                                if curr_t >= 11.0:
                                    lunch_start = max(11.0, curr_t)
                                    if lunch_start <= 12.0:
                                        curr_t = lunch_start + self.d.lunch_duration
                                        lun_c = True
                                        arr = curr_t + tv
                                elif arr >= 11.0:
                                    lunch_start = max(11.0, arr)
                                    if lunch_start <= 12.0:
                                        arr = lunch_start + self.d.lunch_duration
                                        lun_c = True
                            if arr > node.late:
                                feasible = False
                                break
                            curr_t = max(arr, node.early) + node.service
                            curr_p = node_id
                            veh_l += node.demand
                            rt_l += node.demand
                            arr_time = arr
                            
                        # If delay is absorbed, we can break early!
                        if arr_time <= orig_arr + 1e-9:
                            break
                            
                    if not feasible:
                        continue
                        
                    # Return to depot check
                    if curr_p != 0:
                        if not lun_c and curr_t >= 11.0:
                            lunch_start = max(11.0, curr_t)
                            if lunch_start <= 12.0:
                                curr_t = lunch_start + self.d.lunch_duration
                                lun_c = True
                        disp_loc = self.d.get_closest_landfill(curr_p)
                        curr_t += self.d.travel_time(curr_p, disp_loc.id) + disp_loc.service
                        curr_t += self.d.travel_time(disp_loc.id, 0)
                        
                    if (curr_t - self.d.start_time) > max_hours:
                        continue
                        
                    # If we reach here, insertion is feasible!
                    d_iu = self.d.distance_matrix[seq[i-1]][u]
                    d_uj = self.d.distance_matrix[u][seq[i]]
                    d_ij = self.d.distance_matrix[seq[i-1]][seq[i]]
                    c1 = d_iu + d_uj - mu * d_ij
                    
                    if c1 < best_score:
                        best_score = c1
                        best_node = u
                        best_pos = i
                        
            if best_node is not None:
                seq = seq[:best_pos] + [best_node] + seq[best_pos:]
                unrouted_stops.remove(best_node)
            else:
                # Can we add a new sub-route?
                last_cust_idx = -1
                for idx in range(len(seq)-1, -1, -1):
                    if self.d.nodes[seq[idx]].type == 1:
                        last_cust_idx = idx
                        break
                if last_cust_idx == -1:
                    break
                    
                last_cust = seq[last_cust_idx]
                disp_facility = self.d.get_closest_landfill(last_cust).id
                
                feasible_next_seeds = []
                for n in unrouted_stops:
                    trial_seq = seq[:last_cust_idx+1] + [disp_facility, n, self.d.get_closest_landfill(n).id, 0]
                    feasible, _ = self.check_sequence_feasible(trial_seq)
                    if feasible:
                        feasible_next_seeds.append(n)
                        
                if feasible_next_seeds:
                    next_seed = min(feasible_next_seeds, key=lambda n: self.d.distance_matrix[disp_facility][n])
                    unrouted_stops.remove(next_seed)
                    seq = seq[:last_cust_idx+1] + [disp_facility, next_seed, self.d.get_closest_landfill(next_seed).id, 0]
                else:
                    break
                    
        route_stops = [x for x in seq if self.d.nodes[x].type == 1]
        return Route(route_stops)
