import math

class Node:
    def __init__(self, node_id, x, y, early, late, service, demand, node_type):
        self.id = node_id
        self.x = x
        self.y = y
        self.early = early
        self.late = late
        self.service = service
        self.demand = demand
        self.type = node_type  # 0: Depot, 1: Stop, 2: Landfill

class VRPData:
    def __init__(self, vehicle_capacity, route_capacity, max_stops, lunch_duration, speed, nodes):
        self.vehicle_capacity = vehicle_capacity
        self.route_capacity = route_capacity
        self.max_stops = max_stops
        self.lunch_duration = lunch_duration
        self.speed = speed
        self.nodes = nodes
        self.num_nodes = len(nodes)
        
        self.depot = next(n for n in nodes if n.type == 0)
        self.landfills = [n for n in nodes if n.type == 2]
        self.stops = [n for n in nodes if n.type == 1]
        
        self.start_time = self.depot.early
        
        self.distance_matrix = [[0.0] * self.num_nodes for _ in range(self.num_nodes)]
        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                self.distance_matrix[i][j] = abs(nodes[i].x - nodes[j].x) + abs(nodes[i].y - nodes[j].y)
                
    def travel_time(self, i, j):
        return self.distance_matrix[i][j] / self.speed
        
    def get_closest_landfill(self, from_node_id):
        return min(self.landfills, key=lambda l: self.distance_matrix[from_node_id][l.id])

class Route:
    def __init__(self, sequence=None):
        self.sequence = sequence or []
        
    def add(self, node_id):
        self.sequence.append(node_id)
        
    def __iter__(self):
        return iter(self.sequence)
        
    def __len__(self):
        return len(self.sequence)
        
    def __getitem__(self, index):
        return self.sequence[index]
        
    def is_empty(self):
        return len(self.sequence) == 0
