import streamlit as st
import plotly.graph_objects as go
import os
import time

# Import classes and logic from main.py
from parser import load_benchmark
from main import VRPTWSolver, benchmarks

st.set_page_config(page_title="WCVRPTW Benchmark Solver", layout="wide", initial_sidebar_state="expanded")

# Thêm một chút CSS custom để giao diện đẹp hơn
st.markdown("""
    <style>
    .main {
        background-color: #0E1117;
    }
    .stMetric {
        background-color: #1E2130;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚛 Waste Collection Vehicle Routing Problem (WCVRPTW)")
st.markdown("Hệ thống giải quyết bài toán định tuyến xe thu gom rác đa chuyến dựa trên Kim et al. (2006).")

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
    sa_iterations = st.slider(
        "Số vòng lặp SA (Simulated Annealing)", min_value=100, max_value=5000, value=500, step=100,
        help="Tăng số vòng lặp giúp thuật toán dò tìm lộ trình siêu cấp. Ở mức cao (1000+), thuật toán sẽ đánh bại (vượt qua) thông số Benchmark cũ."
    )
    
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
    
    run_key = f"{selected_file}_{algo_type}_{sa_iterations}"
    
    # Luôn tải dữ liệu vì cần dùng để vẽ bản đồ
    data = load_benchmark(file_path)
    
    if st.session_state.get('last_run_key') != run_key:
        with st.spinner("Đang tính toán tối ưu... Vui lòng chờ!"):
            solver = VRPTWSolver(data)
            
            # Chạy thuật toán
            start_time = time.time()
            vn, sm, nh, td, rtd, best_routes = solver.solve(algo_type=algo_type, sa_iterations=sa_iterations)
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
        <h3 style='color: #FF4B4B; margin-bottom: 20px;'>📊 Bảng Kết quả Tính toán Thực tế</h3>
        <div style="display: flex; gap: 15px; margin-bottom: 30px;">
            <div style="flex: 1; background: linear-gradient(135deg, #FF4B4B, #FF7676); padding: 20px; border-radius: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; opacity: 0.9;">Vn (Số xe)</div>
                <div style="font-size: 32px; font-weight: bold; margin-top: 5px;">{vn}</div>
            </div>
            <div style="flex: 1; background: linear-gradient(135deg, #1f77b4, #52a3d9); padding: 20px; border-radius: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; opacity: 0.9;">Sm (Shape Metric)</div>
                <div style="font-size: 32px; font-weight: bold; margin-top: 5px;">{sm:.1f}</div>
            </div>
            <div style="flex: 1; background: linear-gradient(135deg, #2ca02c, #5cd65c); padding: 20px; border-radius: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; opacity: 0.9;">Nh (Overlap)</div>
                <div style="font-size: 32px; font-weight: bold; margin-top: 5px;">{nh}</div>
            </div>
            <div style="flex: 1; background: linear-gradient(135deg, #ff7f0e, #ffb366); padding: 20px; border-radius: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; opacity: 0.9;">TD (Dặm - Tổng quãng đường)</div>
                <div style="font-size: 32px; font-weight: bold; margin-top: 5px;">{td:.1f}</div>
            </div>
            <div style="flex: 1; background: linear-gradient(135deg, #9467bd, #c299e8); padding: 20px; border-radius: 10px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="font-size: 14px; opacity: 0.9;">RTD (Giây)</div>
                <div style="font-size: 32px; font-weight: bold; margin-top: 5px;">{int(rtd)}</div>
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
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor='rgba(255,255,255,0.1)'),
        height=700
    )
    
    # Cấu hình grid lines
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')
    
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
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
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
