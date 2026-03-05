import streamlit as st # type: ignore
import pandas as pd # type: ignore
import plotly.express as px # type: ignore
import pydeck as pdk # type: ignore
import json # type: ignore
import folium # type: ignore
from streamlit_folium import st_folium # type: ignore

# # --- 页面基础设置 ---
st.set_page_config(layout="wide", page_title="Daily Review")

st.title("Daily Review")
# st.markdown("Perform data analysis and visualize the results of completed road test tasks.")

# --- 数据加载函数 ---
@st.cache_data
def load_log_data():
    """加载路测日志数据"""
    try:
        log_df = pd.read_excel("log_book_final.xlsx")
        log_df.columns = log_df.columns.str.strip()

        # --- 新增：兼容中文列名 ---
        if '日期' in log_df.columns:
            log_df.rename(columns={'日期': 'Date'}, inplace=True)
        # --- 结束新增部分 ---

        # 标准化列，处理可能存在的空格
        for col in ['測試結果', '狀態', '站點', 'CPO Name', '备注', 'Loacation']:
            if col in log_df.columns:
                log_df[col] = log_df[col].astype(str).str.strip()
        
        if 'Date' in log_df.columns:
            log_df['Date'] = pd.to_datetime(log_df['Date'], errors='coerce')

        # --- 新增：处理 Loacation 列 ---
        # --- 新增：处理 Loacation 列 ---
        if 'Loacation' in log_df.columns:
            # 替换中文逗号为英文逗号，并分割
            split_loc = log_df['Loacation'].str.replace('，', ',').str.split(',', expand=True)
            if split_loc.shape[1] >= 2:
                # 注意：根据您的描述，第一个是经度，第二个是纬度
                log_df['longitude'] = pd.to_numeric(split_loc[0], errors='coerce')
                log_df['latitude'] = pd.to_numeric(split_loc[1], errors='coerce')

        # --- 【关键步骤】保存处理好的数据 ---
        PROCESSED_FILE = "processed_records.csv"
        try:
            log_df.to_csv(PROCESSED_FILE, index=False, encoding='utf-8-sig')
            # st.sidebar.success(f"数据已处理并保存至 '{PROCESSED_FILE}'")
        except Exception as e:
            st.sidebar.error(f"保存处理后文件失败: {e}")

        # --- 结束新增部分 ---

        if 'latitude' in log_df.columns and 'longitude' in log_df.columns:
            log_df['latitude'] = pd.to_numeric(log_df['latitude'], errors='coerce')
            log_df['longitude'] = pd.to_numeric(log_df['longitude'], errors='coerce')
            log_df.dropna(subset=['latitude', 'longitude'], inplace=True)
        
        # # --- 调试代码 ---
        # st.write("### 调试信息：处理后的数据预览")
        # st.write(log_df.head())
        # st.info("请检查上方表格中 `latitude` 和 `longitude` 列是否包含有效数值。")
        # # --- 调试代码结束 ---

        return log_df
    except FileNotFoundError:
        st.error("错误：找不到 `log_book_final.xlsx` 文件。请确保该文件位于项目根目录。")

# 定义品牌分类
EMO_CPO = ['比亚迪', '小米', '蔚来', 'NIO', '理想', '特斯拉', '小鹏', '广汽能源', '路特斯', "ZEEKR"]
PRIMARY_CPO = ['国家电网', '小桔充电', '南方电网', '蔚景云', '星星充电', '云快充', '依偎能源', '特来电']
IN_HOUSE_BRAND = ['逸安启', 'IONCHI']

def get_cpo_label(cpo_name):
    """根据CPO名称分配标签"""
    if cpo_name in EMO_CPO:
        return '友商'
    elif cpo_name in PRIMARY_CPO:
        return '主要品牌'
    elif cpo_name in IN_HOUSE_BRAND:
        return '自家品牌'
    else:
        return '当地品牌'

# --- 加载数据 ---
log_df = load_log_data()
log_df['CPO LABEL'] = log_df['CPO Name'].apply(get_cpo_label)

# --- 【新增】日期筛选器 ---
if 'Date' in log_df.columns and not log_df['Date'].isnull().all():
    # 确保Date列是日期对象，以便排序
    log_df['Date'] = pd.to_datetime(log_df['Date']).dt.date
    available_dates = sorted(log_df['Date'].unique(), reverse=True)
    
    # 在侧边栏创建筛选器
    selected_date = st.sidebar.selectbox(
        "Select Review Date", 
        options=["All Days"] + available_dates,
        format_func=lambda date: "All Days" if date == "All Days" else date.strftime('%Y-%m-%d') # 格式化日期显示
    )
    
    # 根据选择过滤数据
    if selected_date != "All Days":
        log_df = log_df[log_df['Date'] == selected_date]
        st.info(f"Displaying data for: **{selected_date.strftime('%Y-%m-%d')}**") # 提示当前筛选的日期
else:
    st.sidebar.warning("Date column not found or is empty. \nCannot filter by date.")


if log_df is None or '站點' not in log_df.columns or '狀態' not in log_df.columns or 'CPO Name' not in log_df.columns:
    st.error("数据加载失败，或缺少 '站點' / '狀態' / 'CPO Name' 关键列，无法继续分析。")
    st.stop()

# --- 数据准备 (基于新逻辑) ---
# 1. 总站点数 & 总品牌数
total_unique_stations = log_df['站點'].nunique()
total_unique_cpos = log_df['CPO Name'].nunique()

# 2. 测试次数 (Charge Sessions) 相关统计
testable_records_df = log_df[log_df['狀態'] == '正常測試']
charge_session_counts = log_df['站點'].shape[0]
success_records_count = (testable_records_df['測試結果'] == 'Pass').sum()
failed_records_count = (testable_records_df['測試結果'] == 'Failed').sum()

# 3. 无法测试相关统计
untestable_df = log_df[log_df['狀態'] != '正常測試']
untestable_records_count = untestable_df.shape[0] # 新增：无法测试的记录数
untestable_station_count = untestable_df['站點'].nunique()

# 4. 失败案例相关统计
failed_df = testable_records_df[testable_records_df['測試結果'] == 'Failed']

# --- 1. 顶层核心指标 (KPIs) ---
st.header("Key Indicators")
# st.info("`总站点/品牌数`基于去重统计，`总测试次数`指日志中的记录总数。")

# --- 设定计划目标 ---
PLANNED_CPO_COUNT = 42 # 在这里设置您计划测试的品牌数量

# 第一行指标
kpi_cols_1 = st.columns(3)
kpi_cols_1[0].metric("Total Station Counts", f"{total_unique_stations}")

# 修改“总品牌数”的显示方式
if selected_date == "All Days":
    brand_count_delta = total_unique_cpos - PLANNED_CPO_COUNT
    kpi_cols_1[1].metric(
        label="Total CPO Counts (Plan: 42)", 
        value=f"{total_unique_cpos}",
        delta=f"{brand_count_delta}"
    )
else:
    kpi_cols_1[1].metric(
        label="Daily CPO Counts", 
        value=f"{total_unique_cpos}"
    )

kpi_cols_1[2].metric("Total Charge Sessions Counts", f"{charge_session_counts}")

# 第二行指标
kpi_cols_2 = st.columns(3)
kpi_cols_2[0].metric("✅ Pass", f"{success_records_count}")
kpi_cols_2[1].metric("❌ Failed", f"{failed_records_count}")
kpi_cols_2[2].metric("⚠️ Can't Be Test", f"{untestable_records_count}")

# --- 2. 测试结果详情 ---
st.header("Detail")

if testable_records_df.empty:
    st.warning("没有“正常测试”的记录可供分析。")
else:
    # 改为三列布局
    col1, col2, col3 = st.columns([1, 1, 1.618]) 

    with col1:
        if 'Use Case' in log_df.columns and not log_df['Use Case'].dropna().empty:
            st.subheader("Use Case Describe")
            use_case_counts = log_df['Use Case'].value_counts()
            blue_color_sequence = px.colors.sequential.Blues_r # 使用 Plotly 内置的反向蓝色序列
            fig_use_case = px.pie(
                use_case_counts,
                names=use_case_counts.index,
                values=use_case_counts.values,
                hole=0.5, # 稍微增大圆环
                color_discrete_sequence=blue_color_sequence # 应用蓝色系
            )
            fig_use_case.update_traces(textinfo='percent+label')
            # 移除 title_x=0.5
            fig_use_case.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0)) 
            st.plotly_chart(fig_use_case, use_container_width=True)
        else:
            st.info("无 'Use Case' 数据。")

    with col2:
        # --- 成功/失败比例图 ---
        st.subheader("Pass Rate")
        result_counts = testable_records_df['測試結果'].value_counts()
        fig_result = px.pie(
            result_counts, 
            names=result_counts.index, 
            values=result_counts.values, 
            hole=0.5, # 稍微增大圆环，更美观
            color=result_counts.index,
            color_discrete_map={'Pass':'#87CEFA', 'Failed':'#808080'}
        )
        fig_result.update_traces(textinfo='percent+label', pull=[0.05, 0])
        # 移除 title_x=0.5
        fig_result.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_result, use_container_width=True)

    with col3:
        st.subheader("CPO Test Result")
        cpo_summary = testable_records_df.groupby(['CPO Name', 'CPO LABEL']).agg(
            测试次数=('測試結果', 'count'),
            成功次数=('測試結果', lambda x: (x == 'Pass').sum())
        ).reset_index()
        cpo_summary['失败次数'] = cpo_summary['测试次数'] - cpo_summary['成功次数']
        cpo_summary['成功率(%)'] = (cpo_summary['成功次数'] / cpo_summary['测试次数']) * 100

        # 筛选器
        all_labels = ['所有分类'] + sorted(cpo_summary['CPO LABEL'].unique())
        selected_label = st.selectbox(
            "按分类筛选:",
            options=all_labels,
            label_visibility="collapsed" # 隐藏标签，让界面更紧凑
        )

        if selected_label != '所有分类':
            filtered_summary = cpo_summary[cpo_summary['CPO LABEL'] == selected_label]
        else:
            filtered_summary = cpo_summary

        st.dataframe(
            filtered_summary.sort_values('成功率(%)', ascending=True),
            use_container_width=True,
            hide_index=True,
            height=350, # 可以设置一个固定高度来对齐
            column_config={
                "CPO LABEL": "品牌分类",
                "成功率(%)": st.column_config.ProgressColumn(
                    "成功率(%)",
                    # color="#87CEFA",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
            }
        )

# --- 3. 详细分析 (异常情况) ---
st.header("Abnormal Analysis")

# --- 无法测试的场站分析 ---
with st.expander(f"【Can't Be Test】 {untestable_station_count} Station Could NOT be Tested", expanded=False):
    if untestable_df.empty:
        st.success("所有场站均可进行测试。")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Distribution of reasons for failure to test")
            untestable_reasons = untestable_df['狀態'].value_counts()
            st.dataframe(untestable_reasons)

        with col2:
            st.markdown("##### Base CPO")
            untestable_cpo = untestable_df.groupby('CPO Name')['站點'].nunique().sort_values(ascending=False)
            st.dataframe(untestable_cpo)

# --- 失败案例分析 ---
with st.expander(f"Failed Test Analysis {failed_records_count} Times", expanded=False):
    if failed_df.empty:
        st.success("所有“正常测试”的记录均成功！")
    else:
        st.markdown("###### Distribution of reasons for failure (Base Remarks column)")
        fail_reasons = failed_df['備註'].value_counts()
        if not fail_reasons.empty:
            st.dataframe(fail_reasons)
        else:
            st.info("“备注”列中未提供具体失败原因。")


# --- 4. 地理复盘地图 (新版突出显示效果) ---
st.header("Location")
# st.info("地图已更新：使用不同大小和样式的圆点来突出“失败”与“无法测试”的站点。")

if not log_df.empty and 'latitude' in log_df.columns:
    gaode_tiles = "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
    gaode_attribution = "Amap"
    map_center = [log_df['latitude'].mean(), log_df['longitude'].mean()]

    m = folium.Map(location=map_center, zoom_start=10, tiles=None)
    folium.TileLayer(tiles=gaode_tiles, attr=gaode_attribution, name="高德地图").add_to(m)

    # 创建图层
    layer_success = folium.FeatureGroup(name="✅ Pass", show=True).add_to(m)
    layer_fail = folium.FeatureGroup(name="❌ Failed", show=True).add_to(m)
    layer_untestable = folium.FeatureGroup(name="⚠️ Can't Be Tested", show=True).add_to(m)

    # 遍历数据并添加 CircleMarker
    for _, row in log_df.iterrows():
        popup_html = f"""
        <b>Station Name:</b> {row.get('站點', 'N/A')}<br>
        <b>CPO:</b> {row.get('CPO Name', 'N/A')}<br>
        <b>Status:</b> {row.get('狀態', 'N/A')}<br>
        <b>Use Case:</b> {row.get('Use Case', 'N/A')}<br>
        <b>Test Result:</b> {row.get('測試結果', 'N/A')}<br>
        <b>Remark:</b> {row.get('備註', 'N/A')}
        """
        popup = folium.Popup(popup_html, max_width=300)
        
        # 根据状态和结果定义样式
        if row['狀態'] != '正常測試':
            # 无法测试的点: 橙色，中等大小，带白色边框
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=8,
                popup=popup,
                color='#FFA500', # 橙色
                fill=True,
                fill_color='#FFA500',
                fill_opacity=0.9,
                weight=2, # 边框宽度
                stroke=True,
                line_color='#FFFFFF' # 白色边框
            ).add_to(layer_untestable)
        elif row['測試結果'] == 'Pass':
            # 成功的点: 绿色，较小，半透明
        # 成功的点: 改为蓝色，较小，半透明
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=8,
                popup=popup,
                color="#0c5b13", # 改为蓝色
                fill=True,
                fill_color='#0c5b13', # 改为蓝色
                fill_opacity=0.7
            ).add_to(layer_success)
        elif row['測試結果'] == 'Failed':
            # 失败的点: 红色，最大，带白色边框，最突出
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=10,
                popup=popup,
                color='#dc3545', # 红色
                fill=True,
                fill_color='#dc3545',
                fill_opacity=1.0,
                weight=2, # 边框宽度
                stroke=True,
                line_color='#FFFFFF' # 白色边框
            ).add_to(layer_fail)

    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, width='100%', height=800)
else:
    st.warning("没有可供显示的地理数据。")

# --- 5. 详细数据列表 ---
with st.expander("Total Log Book"):
    st.dataframe(log_df)
