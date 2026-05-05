from models import Node, VRPData

def parse_hhmm(hhmm_str):
    try: val = int(hhmm_str)
    except: val = int(float(hhmm_str))
    h, m = val // 100, val % 100
    return h + m/100.0 if m > 59 else h + m/60.0

def load_benchmark(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
        
    def get_val(line): return float(line.split('//')[0].strip())
    
    vc = get_val(lines[0])
    rc = get_val(lines[1])
    ms = int(get_val(lines[2]))
    ld = get_val(lines[3]) / 3600.0  # seconds to hours
    sp = get_val(lines[4])
    
    nodes = []
    for line_idx in range(6, len(lines)):
        p = lines[line_idx].split()
        if len(p) < 8: continue
        try:
            node_id = len(nodes)
            x = float(p[1]) / 5280.0
            y = float(p[2]) / 5280.0
            early = parse_hhmm(p[3])
            late = parse_hhmm(p[4])
            service = float(p[5]) / 3600.0
            demand = float(p[6])
            node_type = int(p[7])
            
            if node_type in (0, 2):
                demand = 0.0
                
            nodes.append(Node(node_id, x, y, early, late, service, demand, node_type))
        except (ValueError, IndexError):
            pass
            
    return VRPData(vc, rc, ms, ld, sp, nodes)
