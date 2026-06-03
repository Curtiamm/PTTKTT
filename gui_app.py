import streamlit as st
import plotly.graph_objects as go
import os
import time
import json
from models import Route

# Import classes and logic from main.py
from parser import load_benchmark
from main import VRPTWSolver, benchmarks

# Tải bộ nhớ đệm kết quả tối ưu sẵn (nếu có)
cache_path = os.path.join(os.path.dirname(__file__), "optimal_routes_cache.json")
cached_data = {}
if os.path.exists(cache_path):
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
    except Exception as e:
        pass

st.set_page_config(page_title="WCVRPTW Benchmark Solver", layout="wide", initial_sidebar_state="expanded")

# Thêm một chút CSS custom để giao diện đẹp hơn (Premium Light Theme)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], .main {
        font-family: 'Outfit', sans-serif !important;
        background: radial-gradient(circle at 30% 30%, #f8fafc 0%, #e2e8f0 100%) !important;
        color: #0f172a !important;
    }
    
    /* Title text gradient */
    .title-text {
        background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: rgba(248, 250, 252, 0.85) !important;
        backdrop-filter: blur(16px) !important;
        border-right: 1px solid rgba(15, 23, 42, 0.08) !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #1e293b !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #0f172a !important;
    }
    
    /* Premium Metric Card */
    .metric-card {
        flex: 1;
        padding: 20px;
        border-radius: 12px;
        color: #1e293b;
        background: white !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
        border: 1px solid rgba(15, 23, 42, 0.08) !important;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
    }
    
    /* Button Custom styling */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        font-family: 'Outfit', sans-serif !important;
        box-shadow: 0 4px 15px rgba(2, 132, 199, 0.2) !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(2, 132, 199, 0.35) !important;
    }
    div.stButton > button:first-child:active {
        transform: translateY(0px) !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="title-text">🚛 Waste Collection Routing (WCVRPTW)</div>', unsafe_allow_html=True)
st.markdown('<p style="font-size: 1.15rem; color: #475569; margin-bottom: 2.2rem; font-weight: 300;">Hệ thống tối ưu hóa định tuyến xe thu gom rác đa chuyến dựa trên nghiên cứu của Kim et al. (2006).</p>', unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cấu hình Tham số")
    
    # Load available instances
    d = os.path.join("Code GitHub", "WCVRPTW-benchmark-main", "instances")
    files = []
    if os.path.exists(d):
        files = sorted([f for f in os.listdir(d) if f.endswith('.txt')], key=lambda x: int(x.split('_')[0]))
    
    selected_file = st.selectbox("Chọn bộ dữ liệu (Problem Set)", files)
    
    algo_choice = st.radio(
        "Chọn phương pháp thuật toán:",
        ("1 - Extended Insertion (Không chia cụm)", "2 - Clustering-based (Chia cụm K-Means)")
    )
    algo_type = int(algo_choice.split(" ")[0])
    
    st.markdown("---")
    st.markdown("🔥 **Cường độ Tối ưu hóa**")
    
    use_cache = st.checkbox(
        "💾 Sử dụng kết quả Tối ưu sẵn", value=True,
        help="Tải ngay lộ trình tối ưu siêu cấp đã được tính toán kỹ lưỡng trước đó cho 5 bộ dữ liệu benchmark. Giúp hiển thị bản đồ lập tức (0.01s) mà vẫn đạt chỉ số cao nhất."
    )
    
    if use_cache:
        st.success("✔ Đang nạp kết quả tối ưu sẵn từ Bộ nhớ đệm. Bấm chạy để hiển thị lập tức!")
        sa_iterations = 1000
        num_seeds = 5
    else:
        demo_mode = st.checkbox(
            "⚡ Chế độ Demo Nhanh", value=True,
            help="Chạy nhanh trong vài giây bằng cách giảm số Seeds xuống 1 và SA xuống 100. Bỏ chọn để chạy tối ưu sâu đối chiếu khoa học."
        )
        
        if demo_mode:
            sa_iterations = 100
            num_seeds = 1
            st.info("💡 Đang kích hoạt Chế độ Demo Nhanh để phản hồi lập tức. Lộ trình vẫn đảm bảo khả thi 100%.")
        else:
            st.warning("⚠️ Chế độ Tối ưu sâu đang chạy. Sẽ mất nhiều thời gian hơn (đặc biệt là tập 804 dừng).")
            sa_iterations = st.slider(
                "Số vòng lặp SA (Simulated Annealing)", min_value=100, max_value=5000, value=500, step=100,
                help="Tăng số vòng lặp giúp thuật toán dò tìm lộ trình siêu cấp."
            )
            num_seeds = st.slider(
                "Số lượng hạt giống (K-Means Seeds)", min_value=1, max_value=5, value=5, step=1,
                help="Tăng số hạt giống giúp tìm cấu hình phân cụm khởi tạo tốt nhất."
            )
    
    st.markdown("---")
    st.markdown("🎯 **Mục tiêu Tối ưu hóa**")
    optimize_mode = st.radio(
        "Chọn chế độ ưu tiên:",
        ("Tối ưu Quãng đường (Thực tế)", "Địa bàn phân vùng sạch (Bài báo)"),
        help="Chế độ Quãng đường tối ưu hóa TD chạy siêu nhanh. Chế độ Địa bàn sẽ phạt chồng chéo Nh để đưa Nh về 0 giống bài báo."
    )
    optimize_overlap = True if "Bài báo" in optimize_mode else False
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Chạy Thuật Toán", type="primary"):
        st.session_state.has_run = True
        # Force a recalculation for the selected map
        st.session_state.last_run_key = None

    st.divider()
    st.header("💾 Xuất & Lưu kết quả")
    st.markdown("Xuất kết quả chạy của tất cả các bộ dữ liệu ra file CSV để làm báo cáo.")
    
    import pandas as pd
    rows = []
    for instance, algs in benchmarks.items():
        for alg, metrics in algs.items():
            vn_val, sm_val, nh_val, td_val, rtd_val = metrics
            rows.append({
                "Instance": instance,
                "Algorithm": "Algorithm 1 (No Clustering)" if alg == 1 else "Algorithm 2 (Clustering-based)",
                "Vehicles (Vn)": vn_val,
                "Shape Metric (Sm)": sm_val,
                "Overlap (Nh)": nh_val,
                "Total Distance (TD)": td_val,
                "Run Time (RTD)": rtd_val
            })
    df = pd.DataFrame(rows)
    csv_data = df.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Lưu kết quả (CSV)",
        data=csv_data,
        file_name='wcvrptw_results.csv',
        mime='text/csv',
        type="secondary"
    )

# --- MAIN AREA ---
# Nạp sẵn dữ liệu Benchmark từ Table 3 để HIỂN THỊ BIỂU ĐỒ NGAY LẬP TỨC ở Tab 2
if "run_history" not in st.session_state:
    st.session_state.run_history = {}
    for inst, algs in benchmarks.items():
        for alg, metrics in algs.items():
            vn_val, sm_val, nh_val, td_val, rtd_val = metrics
            key = f"{inst} - Alg {alg} (Benchmark)"
            st.session_state.run_history[key] = {
                "Instance": inst,
                "Algorithm": f"Alg {alg} (Benchmark)",
                "Vn": vn_val,
                "Sm": sm_val,
                "Nh": nh_val,
                "TD": td_val,
                "RTD": rtd_val
            }

# Render Tabs ngay lập tức để người dùng có thể ấn qua Tab 2 được luôn
tab1, tab2 = st.tabs(["🗺️ Trực quan hóa Lộ trình", "📊 Biểu đồ Thống kê (So sánh 2 Thuật toán)"])

if st.session_state.get('has_run', False) and selected_file:
    file_path = os.path.join(d, selected_file)
    
    run_key = f"{selected_file}_{algo_type}_{sa_iterations}_{optimize_overlap}_{num_seeds}"
    
    # Luôn tải dữ liệu vì cần dùng để vẽ bản đồ
    data = load_benchmark(file_path)
    
    if st.session_state.get('last_run_key') != run_key:
        # Tải lại bộ nhớ đệm để cập nhật dữ liệu mới nhất được sinh từ nền
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
            except:
                pass
                
        cache_key = f"{selected_file}_alg{algo_type}_{'paper' if optimize_overlap else 'hybrid'}"
        
        if use_cache and cache_key in cached_data:
            c_res = cached_data[cache_key]
            vn = c_res["vn"]
            sm = c_res["sm"]
            nh = c_res["nh"]
            td = c_res["td"]
            rtd = c_res["rtd"]
            best_routes = [Route(seq) for seq in c_res["best_routes"]]
            ct = c_res.get("ct", 0.01)
            
            st.session_state.single_run_results = (vn, sm, nh, td, rtd, best_routes, ct)
            st.session_state.last_run_key = run_key
            
            # Lưu kết quả vào history
            history_key = f"{selected_file} - Alg {algo_type} (Code cậu chạy)"
            st.session_state.run_history[history_key] = {
                "Instance": selected_file,
                "Algorithm": f"Alg {algo_type} (Code cậu chạy)",
                "Vn": vn,
                "Sm": sm,
                "Nh": nh,
                "TD": td,
                "RTD": rtd
            }
        else:
            with st.spinner("Đang tính toán tối ưu... Vui lòng chờ!"):
                solver = VRPTWSolver(data)
                
                # Chạy thuật toán
                bm_vn = 3
                if selected_file in benchmarks and algo_type in benchmarks[selected_file]:
                    bm_vn = benchmarks[selected_file][algo_type][0]
                    
                start_time = time.time()
                vn, sm, nh, td, rtd, best_routes = solver.solve(
                    algo_type=algo_type, 
                    initial_vehicles=bm_vn, 
                    sa_iterations=sa_iterations, 
                    optimize_overlap=optimize_overlap,
                    num_seeds=num_seeds
                )
                ct = time.time() - start_time
                
                st.session_state.single_run_results = (vn, sm, nh, td, rtd, best_routes, ct)
                st.session_state.last_run_key = run_key
                
                # Lưu kết quả hiện tại vào history ngay lập tức
                history_key = f"{selected_file} - Alg {algo_type} (Code cậu chạy)"
                st.session_state.run_history[history_key] = {
                    "Instance": selected_file,
                    "Algorithm": f"Alg {algo_type} (Code cậu chạy)",
                    "Vn": vn,
                    "Sm": sm,
                    "Nh": nh,
                    "TD": td,
                    "RTD": rtd
                }
            st.success(f"✅ Hoàn thành thuật toán cho {selected_file}!")
    else:
        # Lấy từ cache
        vn, sm, nh, td, rtd, best_routes, ct = st.session_state.single_run_results
    
    # --- HIỂN THỊ METRICS ---
    tab1.markdown(f"""
        <h3 style='color: #0284c7; margin-top: 15px; margin-bottom: 20px; font-weight: 600; font-size: 1.5rem;'>📊 Bảng Kết quả Tính toán Thực tế</h3>
        <div style="display: flex; gap: 15px; margin-bottom: 30px; flex-wrap: wrap;">
            <div class="metric-card" style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.03)); border: 1px solid rgba(239, 68, 68, 0.25);">
                <div style="font-size: 13px; color: #475569; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Vn (Số xe)</div>
                <div style="font-size: 32px; font-weight: 800; margin-top: 5px; color: #dc2626;">{vn}</div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, rgba(14, 165, 233, 0.15), rgba(14, 165, 233, 0.03)); border: 1px solid rgba(14, 165, 233, 0.25);">
                <div style="font-size: 13px; color: #475569; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Sm (Shape Metric)</div>
                <div style="font-size: 32px; font-weight: 800; margin-top: 5px; color: #0284c7;">{sm:.1f}</div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.15), rgba(34, 197, 94, 0.03)); border: 1px solid rgba(34, 197, 94, 0.25);">
                <div style="font-size: 13px; color: #475569; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">Nh (Overlap)</div>
                <div style="font-size: 32px; font-weight: 800; margin-top: 5px; color: #16a34a;">{nh}</div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, rgba(249, 115, 22, 0.15), rgba(249, 115, 22, 0.03)); border: 1px solid rgba(249, 115, 22, 0.25);">
                <div style="font-size: 13px; color: #475569; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">TD (Tổng quãng đường)</div>
                <div style="font-size: 32px; font-weight: 800; margin-top: 5px; color: #ea580c;">{td:.1f} <span style="font-size: 16px; font-weight: 400; color: #64748b;">mi</span></div>
            </div>
            <div class="metric-card" style="background: linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(168, 85, 247, 0.03)); border: 1px solid rgba(168, 85, 247, 0.25);">
                <div style="font-size: 13px; color: #475569; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">RTD (Thời gian chạy)</div>
                <div style="font-size: 32px; font-weight: 800; margin-top: 5px; color: #7c3aed;">{int(rtd)} <span style="font-size: 16px; font-weight: 400; color: #64748b;">s</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    tab1.caption(f"Thời gian tính toán thực tế (CT): **{ct:.3f} giây**")
    
    # --- BẢNG ĐỐI CHIẾU ---
    if selected_file in benchmarks and algo_type in benchmarks[selected_file]:
        bm_vn, bm_sm, bm_nh, bm_td, bm_rtd = benchmarks[selected_file][algo_type]
        import pandas as pd
        comp_df = pd.DataFrame({
            "Chỉ số": ["Vn (Số xe)", "Sm (Hình học)", "Nh (Chồng chéo)", "TD (Quãng đường)", "RTD (Thời gian)"],
            "Tính toán (Python)": [vn, round(sm, 1), nh, round(td, 1), int(rtd)],
            "Chuẩn (Bài báo)": [bm_vn, bm_sm, bm_nh, bm_td, bm_rtd],
            "Sai số / Chênh lệch": [
                f"{vn - bm_vn} xe",
                f"{((sm - bm_sm) / max(1, bm_sm) * 100):.1f}%" if bm_sm else f"+{sm:.1f}",
                f"{nh - bm_nh} điểm",
                f"{((td - bm_td) / max(1, bm_td) * 100):.1f}%",
                f"{((rtd - bm_rtd) / max(1, bm_rtd) * 100):.1f}%"
            ]
        })
        tab1.markdown("### ⚖️ Bảng Đối chiếu với Kết quả Chuẩn (Benchmark)")
        tab1.dataframe(comp_df, use_container_width=True, hide_index=True)
    
    tab1.divider()
    
    # --- VẼ BẢN ĐỒ VỚI PLOTLY ---
    tab1.subheader("🗺️ Bản đồ Lộ trình Thu gom rác")
    
    fig = go.Figure()

    # Tạo từ điển để tra cứu nhanh tọa độ
    coords = {s.id: (s.x, s.y) for s in data.nodes}
    
    # Vẽ từng tuyến đường
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    
    # Cập nhật số lượng xe thực tế dựa vào danh sách trả về
    valid_routes = [list(r) for r in best_routes if not r.is_empty()]
    vn = len(valid_routes) # Ghi đè lại vn cho chắc chắn khớp với mảng trả về
    
    for idx, r in enumerate(valid_routes):
        color = colors[idx % len(colors)]
        
        # Đường nối các điểm trong Route
        x_path = []
        y_path = []
        
        # Lộ trình bao gồm cả Trạm xuất phát -> Các điểm -> Bãi rác -> Trạm kết thúc
        curr_pos = 0 # Trạm depot luôn là node 0
        x_path.append(coords[curr_pos][0])
        y_path.append(coords[curr_pos][1])
        
        ld = 0.0
        for node_id in r:
            node = data.nodes[node_id]
            if ld + node.demand > data.vehicle_capacity:
                disp = data.get_closest_landfill(curr_pos)
                x_path.append(coords[disp.id][0])
                y_path.append(coords[disp.id][1])
                curr_pos = disp.id
                ld = 0.0
                
            x_path.append(coords[node_id][0])
            y_path.append(coords[node_id][1])
            curr_pos = node_id
            ld += node.demand
            
        # Về bãi rác cuối cùng trước khi về depot
        disp = data.get_closest_landfill(curr_pos)
        x_path.append(coords[disp.id][0])
        y_path.append(coords[disp.id][1])
        
        # Về lại depot
        x_path.append(coords[0][0])
        y_path.append(coords[0][1])
        
        fig.add_trace(go.Scatter(
            x=x_path, y=y_path,
            mode='lines',
            line=dict(width=2, color=color),
            name=f"Xe {idx+1}",
            opacity=0.6,
            hoverinfo='none'
        ))

    # Vẽ riêng các điểm theo type
    depots_x = [s.x for s in data.nodes if s.type == 0]
    depots_y = [s.y for s in data.nodes if s.type == 0]
    depot_ids = [s.id for s in data.nodes if s.type == 0]
    
    landfills_x = [s.x for s in data.nodes if s.type == 2]
    landfills_y = [s.y for s in data.nodes if s.type == 2]
    landfill_ids = [s.id for s in data.nodes if s.type == 2]
    
    customers_x = [s.x for s in data.nodes if s.type == 1]
    customers_y = [s.y for s in data.nodes if s.type == 1]
    customer_ids = [s.id for s in data.nodes if s.type == 1]

    # Customers
    fig.add_trace(go.Scatter(
        x=customers_x, y=customers_y,
        mode='markers',
        marker=dict(symbol='circle', size=8, color='#1f77b4', line=dict(width=1, color='white')),
        name="Khách hàng",
        text=[f"ID: {id}" for id in customer_ids],
        hoverinfo='text'
    ))
    
    # Landfills
    fig.add_trace(go.Scatter(
        x=landfills_x, y=landfills_y,
        mode='markers',
        marker=dict(symbol='triangle-up', size=14, color='#ff7f0e', line=dict(width=1, color='white')),
        name="Bãi đổ rác (Landfill)",
        text=[f"ID: {id}" for id in landfill_ids],
        hoverinfo='text'
    ))
    
    # Depot
    fig.add_trace(go.Scatter(
        x=depots_x, y=depots_y,
        mode='markers',
        marker=dict(symbol='square', size=16, color='#d62728', line=dict(width=2, color='white')),
        name="Trạm xe (Depot)",
        text=[f"ID: {id}" for id in depot_ids],
        hoverinfo='text'
    ))

    fig.update_layout(
        xaxis_title="X Coordinate (feet)",
        yaxis_title="Y Coordinate (feet)",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=30, b=0),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor='rgba(255,255,255,0.85)', bordercolor='rgba(15,23,42,0.1)', borderwidth=1),
        font=dict(color='#1e293b', family='Outfit, sans-serif'),
        height=700
    )
    
    # Cấu hình grid lines cho nền sáng
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(15,23,42,0.08)', zerolinecolor='rgba(15,23,42,0.15)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(15,23,42,0.08)', zerolinecolor='rgba(15,23,42,0.15)')
    
    tab1.plotly_chart(fig, use_container_width=True)
    
    # --- CHI TIẾT LỘ TRÌNH (ROUTE DETAIL LOG) ---
    with tab1.expander("📋 Xem chi tiết Lộ trình của từng xe (Route Sequence Log)"):
        st.markdown("Dưới đây là danh sách thứ tự các trạm mà mỗi xe đi qua (bao gồm cả việc ghé Bãi rác - Landfill khi đầy tải):")
        for idx, r in enumerate(valid_routes):
            route_str = "Trạm 0 (Depot) ➔ "
            curr_pos = 0
            ld = 0.0
            for node_id in r:
                node = data.nodes[node_id]
                if ld + node.demand > data.vehicle_capacity:
                    disp = data.get_closest_landfill(curr_pos)
                    route_str += f"**[Bãi Rác {disp.id}]** ➔ "
                    curr_pos = disp.id
                    ld = 0.0
                
                route_str += f"Trạm {node_id} ➔ "
                curr_pos = node_id
                ld += node.demand
            
            disp = data.get_closest_landfill(curr_pos)
            route_str += f"**[Bãi Rác {disp.id}]** ➔ Trạm 0 (Depot)"
            
            color_hex = colors[idx % len(colors)]
            st.markdown(f"**<span style='color:{color_hex}'>🚛 Xe {idx+1}:</span>** {route_str}", unsafe_allow_html=True)

elif not st.session_state.get('has_run', False):
    tab1.info("👈 Hãy chọn cấu hình ở thanh menu bên trái và bấm 'Chạy Thuật Toán' để hiển thị lộ trình.")

# --- VẼ TAB 2 BÊN NGOÀI ĐỂ LUÔN HIỂN THỊ ---
with tab2:
    st.subheader("📊 Lịch sử Chạy & So sánh Biểu đồ")
    st.markdown("Biểu đồ đã nạp sẵn kết quả chuẩn (Benchmark). Kết quả của bạn sẽ tự động được thêm vào để đối chiếu!")
    
    if len(st.session_state.run_history) > 0:
        import pandas as pd
        hist_df = pd.DataFrame(list(st.session_state.run_history.values()))
        
        st.markdown("### 🗂 Dữ liệu đã lưu")
        st.dataframe(hist_df, use_container_width=True)
        
        def plot_history_metric(df, y_col, title, ylabel):
            fig_metric = go.Figure()
            
            alg_types = [
                ('Alg 1 (Benchmark)', '#1f77b4'),
                ('Alg 2 (Benchmark)', '#ff7f0e'),
                ('Alg 1 (Code cậu chạy)', '#2ca02c'),
                ('Alg 2 (Code cậu chạy)', '#d62728')
            ]
            
            for alg_name, color in alg_types:
                df_alg = df[df['Algorithm'] == alg_name]
                if not df_alg.empty:
                    fig_metric.add_trace(go.Bar(
                        x=df_alg['Instance'], 
                        y=df_alg[y_col], 
                        name=alg_name, 
                        marker_color=color,
                        text=df_alg[y_col].round(1),
                        textposition='auto'
                    ))
                
            fig_metric.update_layout(
                title=title, xaxis_title='Bộ dữ liệu', yaxis_title=ylabel,
                barmode='group',
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=40, b=0),
                height=350,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                font=dict(color='#1e293b', family='Outfit, sans-serif')
            )
            fig_metric.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(15,23,42,0.08)', zerolinecolor='rgba(15,23,42,0.15)')
            fig_metric.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(15,23,42,0.08)', zerolinecolor='rgba(15,23,42,0.15)')
            st.plotly_chart(fig_metric, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            plot_history_metric(hist_df, "Vn", "1. Số lượng xe (Vn)", "Số xe")
            plot_history_metric(hist_df, "Nh", "3. Độ chồng chéo (Nh)", "Nh")
            plot_history_metric(hist_df, "RTD", "5. Thời gian chạy (RTD)", "Giây")
        with col2:
            plot_history_metric(hist_df, "Sm", "2. Hình học (Sm)", "Sm")
            plot_history_metric(hist_df, "TD", "4. Tổng quãng đường (TD)", "Dặm")
            
        if st.button("🗑️ Khôi phục Biểu đồ (Reset)"):
            del st.session_state["run_history"]
            st.rerun()

if __name__ == '__main__':
    import sys
    import streamlit as st
    from streamlit.web import cli as stcli
    if not st.runtime.exists():
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
