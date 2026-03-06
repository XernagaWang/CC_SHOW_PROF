import streamlit as st 
import numpy as np
import pandas as pd
import json
import streamlit.components.v1 as components 
import urllib.parse
import qrcode 
from io import BytesIO
import datetime
from datetime import timezone, timedelta
import os
import shutil
import zipfile
UTC8 = timezone(timedelta(hours=8))

# --- Version compatibility for rerun ---
def rerun():
    """A compatibility function for st.rerun(), which was introduced in Streamlit 1.13.0"""
    try:
        st.rerun()
    except AttributeError:
        # Fallback to the old experimental API for older Streamlit versions
        st.experimental_rerun()

# --- Global Option Constants (Translated) ---
USE_CASE_OPTIONS = ["UC01_CC_DC_AC_Sessions", "UC02_DC_eRoute_vWM", "UC03_TBD"]
TEST_STATUS_OPTIONS = ["Normal Test", "Station Inaccessible (Access Control, Construction, etc.)", "Charger Damaged", "Map Navigation Inaccurate", "Other"]
START_METHOD_OPTIONS = ["Scan QR Code", "Insert Card", "APP Operation", "Other"]
HAS_12A_24A_OPTIONS = ["True", "False"]
END_METHOD_OPTIONS = ["Target SOC", "LAT", "CID", "RFID", "APP", "Other"]
END_REASON_OPTIONS = ["Manual Stop", "Target SOC", "Other"]
TEST_RESULT_OPTIONS = ["None", "Pass", "Failed"]
ERROR_DESCRIBE_OPTIONS = ["None","GBT", "Charger", "ABK", "HVS", "CCU", "LAT", "CID", "PHUD", "Other"]

CITIES = {
    "成都": "CD",
    "重庆": "CQ",
    "贵阳": "GY", 
}

# --- Parameters ---
UC02_POWER_THRESHOLD = 151.2

# --- Page Setup ---
st.set_page_config(layout="wide", page_title="On Mission")

def clear_form():
    """Clear all form input fields and select boxes."""
    text_keys = [
        "cpo_name", "charger_manufacturer", "charger_model", "charger_voltage",
        "charger_current", "charger_power", "start_method_other", "start_soc",
        "end_soc", "end_method_other", "end_reason_other", "error_describe_other", "remark"
    ]
    for key in text_keys:
        if key in st.session_state:
            st.session_state[key] = ""
    
    st.session_state["start_time"] = ""
    st.session_state["end_time"] = ""

    st.session_state["selected_use_case"] = USE_CASE_OPTIONS[0]
    st.session_state["test_status"] = TEST_STATUS_OPTIONS[0]
    st.session_state["selected_start_method"] = START_METHOD_OPTIONS[0]
    st.session_state["has_12A_24A"] = HAS_12A_24A_OPTIONS[0]
    st.session_state["selected_end_method"] = END_METHOD_OPTIONS[0]
    st.session_state["selected_end_reason"] = END_REASON_OPTIONS[0]
    st.session_state["test_result"] = TEST_RESULT_OPTIONS[0]
    st.session_state["selected_error_describe"] = ERROR_DESCRIBE_OPTIONS[0]
    st.session_state["charger_model"] = None # <-- Reset the new selectbox
    
    # Clear photo state as well
    st.session_state.photo_step = 0
    st.session_state.photo_data = {}


def is_form_empty():
    """Check if all form fields are in their initial/empty state."""
    text_keys = [
        "cpo_name", "charger_manufacturer", "charger_model", "charger_voltage",
        "charger_current", "charger_power", "start_method_other", "start_soc",
        "end_soc", "end_method_other", "end_reason_other", "error_describe_other", "remark"
    ]
    for key in text_keys:
        if st.session_state.get(key, "") != "":
            return False

    if st.session_state.get("selected_use_case") != USE_CASE_OPTIONS[0]: return False
    if st.session_state.get("test_status") != TEST_STATUS_OPTIONS[0]: return False
    if st.session_state.get("selected_start_method") != START_METHOD_OPTIONS[0]: return False
    if st.session_state.get("has_12A_24A") != HAS_12A_24A_OPTIONS[0]: return False
    if st.session_state.get("selected_end_method") != END_METHOD_OPTIONS[0]: return False
    if st.session_state.get("selected_end_reason") != END_REASON_OPTIONS[0]: return False
    if st.session_state.get("test_result") != TEST_RESULT_OPTIONS[0]: return False
    if st.session_state.get("selected_error_describe") != ERROR_DESCRIBE_OPTIONS[0]: return False

    return True

def submit_callback():
    """Temporarily store all current form values before the script reruns."""
    # --- Photo Saving Logic ---
    if 'photo_data' in st.session_state and st.session_state.photo_data:
        
        # --- New Station ID Generation Logic ---
        base_path = os.path.join("images", "structured")
        os.makedirs(base_path, exist_ok=True)

        # 1. Get city and CPO info
        city_code = CITIES.get(selected_city_name, "XX")
        cpo_name = "".join(c for c in st.session_state.get("cpo_name", "unknown_cpo") if c.isalnum() and c.isascii()).upper()
        if not cpo_name: cpo_name = "CPO"

        # 2. Scan existing directories to find the next available index
        prefix = f"{city_code}_{cpo_name}_"
        max_index = 0
        for dirname in os.listdir(base_path):
            if dirname.startswith(prefix):
                try:
                    index_str = dirname.replace(prefix, "")
                    if index_str.isdigit():
                        max_index = max(max_index, int(index_str))
                except ValueError:
                    continue # Ignore directories that don't have a valid number at the end
        
        next_index = max_index + 1
        
        # 3. Create the new station ID and directory
        station_id = f"{prefix}{next_index:03d}"
        station_dir = os.path.join(base_path, station_id)
        os.makedirs(station_dir, exist_ok=True)

        # --- End of New Logic ---

        # Save photos
        for key, photo_info in st.session_state.photo_data.items():
            file_path = os.path.join(station_dir, photo_info['filename'])
            with open(file_path, "wb") as f:
                f.write(photo_info['data'].getbuffer())
        
        # Create meta.json
        meta_data = {
            "station_id": station_id,
            "station_name_original": st.session_state.selected_station_for_submit,
            "photos": {key: info['filename'] for key, info in st.session_state.photo_data.items()},
            "last_updated": datetime.datetime.now(UTC8).isoformat() # <--- 修改点
        }
        with open(os.path.join(station_dir, 'meta.json'), 'w') as f:
            json.dump(meta_data, f, indent=2)

    # --- Form Data Saving Logic ---
    st.session_state.submitted_record = {
        "City": selected_city_name, # Add city information
        "Day": st.session_state.selected_day_for_submit,
        "Date": datetime.datetime.now(UTC8).strftime("%Y-%m-%d"), 
        "Station": st.session_state.selected_station_for_submit,
        "Use Case": st.session_state.selected_use_case,
        "Status": st.session_state.test_status,
        "CPO Name": st.session_state.cpo_name,
        "Manufacturer": st.session_state.charger_manufacturer,
        "MODEL": st.session_state.charger_model,
        "Voltage(V)": st.session_state.charger_voltage,
        "Current(A)": st.session_state.charger_current,
        "Power(kW)": st.session_state.charger_power,
        "Start Method": st.session_state.selected_start_method,
        "Start Method_Other": st.session_state.get("start_method_other", ""),
        "Has_12A_24A": st.session_state.has_12A_24A,
        "Start Time": st.session_state.get("start_time", ""),
        "Start SoC(%)": st.session_state.start_soc,
        "End Time": st.session_state.get("end_time", ""),
        "End SoC(%)": st.session_state.end_soc,
        "End Method": st.session_state.selected_end_method,
        "End Method_Other": st.session_state.get("end_method_other", ""),
        "End Reason": st.session_state.selected_end_reason,
        "End Reason_Other": st.session_state.get("end_reason_other", ""),
        "Test Result": st.session_state.test_result,
        "Error Describe": st.session_state.selected_error_describe,
        "Error Describe_Other": st.session_state.get("error_describe_other", ""),
        "Remark": st.session_state.remark
    }
    clear_form()

def load_data(city_prefix):
    """
    Loads all necessary data files based on the selected city.
    - report_{city_prefix}_enriched.csv: The daily plan.
    - all_map_stations_{city_prefix}.csv: Master list of all stations.
    - mission_test_records.csv: The log of tests already performed.
    """
    try:
        report_path = os.path.join('output', f'report_{city_prefix}_enriched.csv')
        stations_path = os.path.join('output', f'all_map_stations_{city_prefix}.csv')
        
        report_df = pd.read_csv(report_path)
        all_stations_df = pd.read_csv(stations_path)
        
        # --- UC2 Column Logic ---
        # Check if 'UC2' column exists. If not, create it.
        if 'UC2' not in all_stations_df.columns:
            print(f"'UC2' column not found in '{stations_path}'. Processing file...")
            # Clean the power column
            all_stations_df['max_dc_power'] = pd.to_numeric(all_stations_df['max_dc_power'], errors='coerce').fillna(0)
            # Create the 'UC2' column and convert boolean to integer (1 or 0)
            all_stations_df['UC2'] = (all_stations_df['max_dc_power'] > UC02_POWER_THRESHOLD).astype(int)
            # Save the modified DataFrame back to the CSV
            all_stations_df.to_csv(stations_path, index=False, encoding='utf-8-sig')
            print(f"Successfully processed and updated {stations_path}")
        # --- End UC2 Logic ---

        if os.path.exists('mission_test_records.csv'):
            records_df = pd.read_csv('mission_test_records.csv')
        else:
            records_df = pd.DataFrame(columns=['Date', 'City', 'Station Name', 'MODEL', 'Result', 'User'])
    except FileNotFoundError as e:
        st.error(f"Data file not found for city {city_prefix}. Please check the 'output' directory. Missing file: {e.filename}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    return report_df, all_stations_df, records_df

def create_zip_archive():
    """Create a zip archive of all recorded data."""
    zip_buffer = BytesIO()
    
    img_source_dir = "images/structured"
    csv_source_file = "mission_test_records.csv"

    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        # Add all images
        if os.path.isdir(img_source_dir):
            for root, _, files in os.walk(img_source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    archive_path = os.path.relpath(file_path, "images") # Keep 'structured/...' path
                    zip_file.write(file_path, archive_path)
        
        # Add the CSV record file
        if os.path.isfile(csv_source_file):
            zip_file.write(csv_source_file)

    zip_buffer.seek(0)
    return zip_buffer

# --- UI Layout ---

st.sidebar.header("Select City")
selected_city_name = st.sidebar.selectbox("Current City:", list(CITIES.keys()), key="city_selector")
city_prefix = CITIES[selected_city_name]

# For now, strategy is hardcoded, can be a selectbox later if needed.
strategy_prefix = "A" 

# Load data based on selected city
report_df, all_stations_df, records_df = load_data(city_prefix)

if report_df is None:
    st.stop()

st.title("Test Log Book")
st.subheader(f"Hotel: {records_df.get('Hotel Name', 'N/A')}")

st.sidebar.header("Select Day")
selected_day = st.sidebar.selectbox(
    'Filter by day:',
    options=['All'] + sorted(report_df['第幾天'].unique().tolist()),
    index=0
)

if selected_day == 'All':
    filtered_report_df = report_df
else:
    filtered_report_df = report_df[report_df['第幾天'] == selected_day]

total_days = report_df['第幾天'].max()
total_targets = report_df['累積目標數'].max()

if selected_day == 'All':
    today_targets = total_targets
else:
    today_targets = filtered_report_df.shape[0]

tested_targets = filtered_report_df['累積目標數'].max() if not filtered_report_df.empty else 0

st.header("Mission Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Days:", f"{total_days}")
col2.metric("Today's Test Plan", f"{today_targets}")
col3.metric("Tested Targets", f"{tested_targets}")

progress_percent = int((tested_targets / total_targets) * 100) if total_targets > 0 else 0
st.progress(progress_percent, text=f"Task Completion Rate: {progress_percent}%")

# --- Data Export Section ---
st.sidebar.header("Data Export")
st.sidebar.info("Download all recorded data as a single zip file.")

# CSV Download (existing)
if os.path.isfile("mission_test_records.csv"):
    with open("mission_test_records.csv", "rb") as f:
        st.sidebar.download_button(
            "Download Records Only (CSV)",
            f,
            file_name="mission_test_records.csv",
            mime="text/csv"
        )

# ZIP Archive Download (new)
if st.sidebar.button("Prepare Full Archive for Download"):
    # Check if there is anything to archive
    if not os.path.isdir("images/structured") and not os.path.isfile("mission_test_records.csv"):
        st.sidebar.warning("No data recorded yet. Nothing to archive.")
    else:
        with st.spinner("Generating archive... Please wait."):
            zip_buffer = create_zip_archive()
            st.session_state['zip_buffer_for_download'] = zip_buffer
            st.session_state['zip_filename'] = f"road_test_archive_{datetime.datetime.now(UTC8).strftime('%Y%m%d_%H%M%S')}.zip" # <--- 修改点

if 'zip_buffer_for_download' in st.session_state:
    st.sidebar.download_button(
        label="📥 Download Full Archive (ZIP)",
        data=st.session_state['zip_buffer_for_download'],
        file_name=st.session_state['zip_filename'],
        mime="application/zip",
        on_click=lambda: st.session_state.pop('zip_buffer_for_download', None) # Clear after download
    )
st.markdown("---") # Add a separator

st.header("Detail of Each Day")

with st.expander("On-site Test Log Input", expanded=True):
    # --- Logic for Manual Station Input ---
    MANUAL_STATION_INPUT = "--- 手动输入新站点 (列表中未找到) ---"
    
    # Define plan_to_display here to be used in this expander
    plan_to_display = filtered_report_df[~filtered_report_df['目的地'].astype(str).str.contains('完成測試')]
    
    station_options = plan_to_display['目的地'].unique().tolist()
    full_station_options = [MANUAL_STATION_INPUT] + station_options

    # Display the selectbox with simplified options
    selected_station = st.selectbox("Select Test Station", full_station_options)

    # Handle the selection
    if selected_station == MANUAL_STATION_INPUT:
        manual_station_name = st.text_input("请输入新站点名称:", key="manual_station_name")
        st.session_state.selected_station_for_submit = manual_station_name
    else:
        st.session_state.selected_station_for_submit = selected_station
    
    # We still need to set the day
    st.session_state.selected_day_for_submit = selected_day
    # Only proceed to show the rest of the form if a station has been selected or entered
    if st.session_state.get("selected_station_for_submit"):
        
        # --- Use Case Steps Definition (with partial translation) ---

        UC01_STEPS = [
            {"title": "执行 5 次直流快充 (DC)", "details": "在今天内完成 5 次直流快充测试。", "location": "车外 (Out-of-Car)", "icon": "🚶"},
            {"title": "执行 2 次交流慢充 (AC)", "details": "在今天内完成 2 次交流慢充测试。", "location": "车外 (Out-of-Car)", "icon": "🚶"},
            {"title": "使用不同方式结束充电", "details": "确保每次充电都尝试用不同的方式结束，例如：车机屏幕(HMI)、充电口按钮(LAT)、充电桩(EVSE stop)、达到目标电量(Target SOC)等。", "location": "车内/车外", "icon": "🔄"}
        ]

        UC02_STEPS = [
            {"title": "规划导航", "details": "在车机上设置一个包含大功率快充站的长途导航。", "location": "车内 (In-Car)", "icon": "🚗"},
            {"title": "开启电池预热", "details": "进入车辆‘充电设置’菜单，确保‘电池自动预热’功能已开启。", "location": "车内 (In-Car)", "icon": "🚗"},
            {"title": "确认预热状态", "details": "观察仪表盘或中控屏，检查是否有预热图标（如带风扇的蓝色电池）。", "location": "车内 (In-Car)", "icon": "🚗"},
            {"title": "检查预处理结果", "details": "抵达充电站后，在‘充电设置’中查看高压电池状态，确认‘预处理’为‘OK’。", "location": "车内 (In-Car)", "icon": "🚗"},
            {"title": "核对建议时间", "details": "查看屏幕显示的‘建议充电时长’，判断其是否合理。", "location": "车内 (In-Car)", "icon": "🚗"},
            {"title": "连接充电枪", "details": "打开充电口盖，并将充电枪插入车辆。", "location": "车外 (Out-of-Car)", "icon": "🚶"},
            {"title": "启动充电", "details": "在充电桩上完成扫码/刷卡等认证操作。", "location": "车外 (Out-of-Car)", "icon": "🚶"},
            {"title": "确认充电开始", "details": "观察车辆和充电桩，确认充电已成功激活。", "location": "车内/车外", "icon": "🔄"},
            {"title": "完成充电", "details": "等待达到建议的充电时长后，停止充电。", "location": "车内/车外", "icon": "🔄"}
        ]

        use_case_steps = {
            "UC01_CC_DC_AC_Sessions": {
                "tip": "每日任务：完成 5 次直流快充和 2 次交流慢充，并尝试用不同方式结束充电。", 
                "steps": UC01_STEPS
            },
            "UC02_DC_eRoute_vWM": {
                "tip": "导航到快充站，验证电池自动预热（vWM）功能。", 
                "steps": UC02_STEPS
            },
            "UC03_TBD": {
                "tip": "这是一个待定的 Use Case，具体测试步骤尚未提供。", 
                "steps": [{"title": "等待任务详情", "details": "请等待项目经理提供此 Use Case 的具体测试步骤。", "location": "N/A", "icon": "❓"}]
            },
        }
        
        selected_use_case = st.selectbox("Select Use Case", USE_CASE_OPTIONS, key="selected_use_case")
        
        if selected_use_case in use_case_steps:
            case_info = use_case_steps[selected_use_case]
            st.info(case_info["tip"])
            # if case_info["steps"] and isinstance(case_info["steps"][0], dict):
            #     with st.expander("Show/Hide Test Steps"): # <--- 修改点：使用 expander 包裹
            #         st.markdown("##### Test Steps")
            if case_info["steps"] and isinstance(case_info["steps"][0], dict):
                if st.checkbox("显示/隐藏详细测试步骤", key=f"show_steps_{selected_use_case}"): # <--- 使用 checkbox 替代
                    st.markdown("##### Test Steps")
                    steps_text = ""
                    for i, step in enumerate(case_info["steps"]):
                        steps_text += f"**{i+1}. {step['title']}**\n"
                        steps_text += f"   - {step['details']}\n\n"
                    
                    st.markdown(steps_text)
                    st.button("Confirm All Steps Completed", key=f"confirm_steps_{selected_use_case}")
                st.markdown("---") # 保留分割线
            else:
                for step in case_info["steps"]:
                    st.markdown(step)
        else:
            st.info("Please test according to the actual operation.")

        test_status = st.selectbox("Test Status", TEST_STATUS_OPTIONS, key="test_status")
        if test_status == "Station Inaccessible (Access Control, Construction, etc.)":
            st.info("Please take photos of the site and note the reason in the remarks.")
        elif test_status == "Charger Damaged":
            st.info("Please record the ID of the damaged charger and take photos.")
        elif test_status == "Map Navigation Inaccurate":
            st.info("Please note the actual location and the navigation deviation in the remarks.")
        elif test_status == "Other":
            st.info("Please provide a detailed explanation in the remarks.")

        st.markdown("#### Charger Information")
        st.info("Please take photos of: both sides of the charger, charging gun label, nameplate. If there is a display, record its content as well.")

        cpo_name = st.text_input("CPO Name", "", key="cpo_name")
        charger_manufacturer = st.text_input("Manufacturer", "", key="charger_manufacturer")
        # charger_model = st.text_input("MODEL", "", key="charger_model") # <-- Replaced
        charger_model = st.selectbox("Charge Type (MODEL)", ["AC", "DC"], key="charger_model", index=None, placeholder="Select charge type...") # <-- New
        charger_voltage = st.text_input("Rated Voltage (V)", "", key="charger_voltage")
        charger_current = st.text_input("Rated Current (A)", "", key="charger_current")
        charger_power = st.text_input("Rated Power (kW)", "", key="charger_power")

        # --- 拍照功能实现 ---
                # --- 拍照功能实现 ---
        PHOTO_SEQUENCE = [
            {"key": "pile_left", "prompt": "第 1/4 步: 充电桩左侧全景", "filename": "pile_left.png"},
            {"key": "pile_right", "prompt": "第 2/4 步: 充电桩右侧全景", "filename": "pile_right.png"},
            {"key": "gun", "prompt": "第 3/4 步: 充电枪接口", "filename": "gun.png"},
            {"key": "plate", "prompt": "第 4/4 步: 充电桩铭牌", "filename": "plate.png"},
        ]

        if 'photo_step' not in st.session_state:
            st.session_state.photo_step = 0
        if 'photo_data' not in st.session_state:
            st.session_state.photo_data = {}
        if 'camera_ready' not in st.session_state:
            st.session_state.camera_ready = False

        current_step_index = st.session_state.photo_step
        if current_step_index < len(PHOTO_SEQUENCE):
            current_step_info = PHOTO_SEQUENCE[current_step_index]
            st.info("📷 **拍照提示**: 请将手机横置拍摄，确保画面清晰、完整。")
            st.write(f"**{current_step_info['prompt']}**")

            # Checkbox to activate the camera
            st.session_state.camera_ready = st.checkbox("📷 准备拍照", key=f"cam_ready_{current_step_info['key']}")

            if st.session_state.camera_ready:
                uploaded_photo = st.camera_input(
                    label=f"拍摄 {current_step_info['prompt']}", 
                    key=f"camera_{current_step_info['key']}"
                )
                if uploaded_photo is not None:
                    st.session_state.photo_data[current_step_info['key']] = {
                        "data": uploaded_photo,
                        "filename": current_step_info['filename']
                    }
                    st.session_state.photo_step += 1
                    # Reset the checkbox state before rerunning
                    st.session_state.camera_ready = False
                    rerun()

        if len(st.session_state.photo_data) > 0:
            st.write("---")
            st.write("🖼️ **照片预览**")
            cols = st.columns(len(PHOTO_SEQUENCE))
            for i, photo_info in enumerate(PHOTO_SEQUENCE):
                with cols[i]:
                    st.caption(photo_info['prompt'].split(':')[1].strip())
                    if photo_info['key'] in st.session_state.photo_data:
                        st.image(st.session_state.photo_data[photo_info['key']]['data'], width=150)
                    else:
                        st.image("https://via.placeholder.com/150x100.png?text=尚未拍摄", width=150)

        if st.session_state.photo_step == len(PHOTO_SEQUENCE):
            st.success("✅ 所有照片均已拍摄完成！")
            if st.button("重新拍摄所有照片"):
                st.session_state.photo_step = 0
                st.session_state.photo_data = {}
                rerun()
        # --- 拍照功能结束 ---
        
        selected_start_method = st.selectbox("Start Method", START_METHOD_OPTIONS, key="selected_start_method")
        if selected_start_method == "Other":
            st.text_input("Please specify other start method", "", key="start_method_other")
        
        has_12A_24A = st.selectbox("Has 12A, 24A options?", HAS_12A_24A_OPTIONS, key="has_12A_24A")
        
        if "start_time" not in st.session_state: st.session_state["start_time"] = ""
        if st.button("Record Start Time", key="record_start_time_main"):
            st.session_state["start_time"] = datetime.datetime.now(UTC8).strftime("%Y-%m-%d %H:%M:%S") # <--- 修改点
        st.text_input("Start Time", value=st.session_state.get("start_time", ""), disabled=True)
        start_soc = st.text_input("Start SoC (%)", "", key="start_soc")
        
        if "end_time" not in st.session_state: st.session_state["end_time"] = ""
        if st.button("Record End Time", key="record_end_time_main"):
            st.session_state["end_time"] = datetime.datetime.now(UTC8).strftime("%Y-%m-%d %H:%M:%S") # <--- 修改点
        st.text_input("End Time", value=st.session_state.get("end_time", ""), disabled=True)
        end_soc = st.text_input("End SoC (%)", "", key="end_soc")
            
        selected_end_method = st.selectbox("End Method", END_METHOD_OPTIONS, key="selected_end_method")
        if selected_end_method == "Other":
            st.text_input("Please specify other end method", "", key="end_method_other")
        
        selected_end_reason = st.selectbox("Reason for Ending Charge", END_REASON_OPTIONS, key="selected_end_reason")
        if selected_end_reason == "Other":
            st.text_input("Please specify other reason for ending", "", key="end_reason_other")
        
        test_result = st.selectbox("Test Result", TEST_RESULT_OPTIONS, key="test_result")
        selected_error_describe = st.selectbox("Error Describe", ERROR_DESCRIBE_OPTIONS, key="selected_error_describe")
        if selected_error_describe == "Other":
            st.text_input("Please specify other Error Describe", "", key="error_describe_other")
        
        remark = st.text_area("Remark", "", key="remark")

        form_is_empty = is_form_empty()
        st.button("Submit Record", on_click=submit_callback, disabled=form_is_empty)

        if 'submitted_record' in st.session_state and st.session_state.submitted_record:
            record = st.session_state.submitted_record
            save_file = "mission_test_records.csv"
            file_exists = os.path.isfile(save_file)
            
            df = pd.DataFrame([record])
            df.to_csv(save_file, mode='a', header=not file_exists, index=False, encoding='utf-8-sig')
            st.success("Record saved successfully!")
            st.session_state.submitted_record = None
            rerun()
            # st.rerun()
            rerun()
    else:
        st.info("No test stations available for the current selection.")

def generate_ditu_navi_link(row):
    to_name = urllib.parse.quote(str(row['目的地']))
    to_lnglat = f"{row['目的地經度']},{row['目的地緯度']}"
    url = (f"https://ditu.amap.com/dir?type=car&policy=2&to%5Bname%5D={to_name}&to%5Blnglat%5D={to_lnglat}&src=yourAppName")
    return url

# This dataframe for the navi list must be defined *before* the expander
# to ensure it's correctly filtered when the page reruns on day selection.
filtered_navi_df = filtered_report_df[
    ~filtered_report_df['目的地'].astype(str).str.contains('完成測試')
]

with st.expander("Daily Target List (Click to expand)", expanded=False):
    # Adjust column ratios for the new "Features" column
    header_cols = st.columns([1, 1, 4, 2])
    header_cols[0].markdown("**Day**")
    header_cols[1].markdown("**Features**")
    header_cols[2].markdown("**Target Station**")
    header_cols[3].markdown("**Navi QR Code**")
    st.markdown("---")

    for idx, row in filtered_navi_df.iterrows():
        navi_url = generate_ditu_navi_link(row)
        # Adjust column ratios for the new "Features" column
        cols = st.columns([1, 1, 4, 2])
        cols[0].write(row['第幾天'])
        
        station_name = row['目的地']
        
        # Check if the station is a UC2 candidate and display an icon in the new column
        is_uc2 = all_stations_df.loc[all_stations_df['station_name'] == station_name, 'UC2'].values
        if len(is_uc2) > 0 and int(is_uc2[0]) == 1:
            cols[1].write("🌡️🔋 vWM") # Display icon in the "Features" column
        else:
            cols[1].write("") # Leave it empty if not a UC2 station
            
        cols[2].write(station_name) # Display only the station name in its column

        if cols[3].button("Generate QR Code", key=f"qr_btn_{idx}"):
            st.session_state['current_qr_url'] = navi_url
            st.session_state['current_station_name'] = station_name # Store name for display
            
st.sidebar.header("Navigation QR Code")

if 'current_qr_url' in st.session_state:
    # Display the station name and the QR code
    st.sidebar.info(f"**Navigating to: {st.session_state.get('current_station_name', 'N/A')}**")
    
    # Generate QR code image from the URL stored in session state
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(st.session_state['current_qr_url'])
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert image to bytes and display
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.sidebar.image(buf.getvalue(), caption="Scan to navigate with Google Maps", use_column_width=True)
else:
    # Default display when no QR code has been generated yet
    st.sidebar.info("Click '生成导航二维码' next to a station to generate its navigation QR code here.")
    st.sidebar.image("images/qrcode/qrcode_ex.jpg", caption="QR code will appear here")

def get_uc01_status_today(selected_day):
    """
    Analyzes records for a given day to track UC01 progress.
    Returns a dictionary with counts and a status DataFrame.
    """
    # Define targets and categories
    UC01_ID = "UC01_CC_DC_AC_Sessions"
    DC_TARGET = 5
    AC_TARGET = 2
    # Re-ordered to prioritize longer, more specific matches first
    END_METHODS_TO_TRACK = ["Target SOC", "LAT", "HMI", "APP", "RFID"] 
    CHARGE_TYPES = ["AC", "DC"]

    # Initialize status tracking
    status = {
        "dc_completed": 0,
        "ac_completed": 0,
        "dc_target": DC_TARGET,
        "ac_target": AC_TARGET,
        "status_df": pd.DataFrame('⬜️', index=END_METHODS_TO_TRACK, columns=CHARGE_TYPES)
    }

    record_file = "mission_test_records.csv"
    if not os.path.exists(record_file):
        return status # Return default status if no records exist

    # Read records for the selected day
    try:
        df = pd.read_csv(record_file)
        
        # Logic to filter based on the selected day from the sidebar
        if selected_day == 'All':
            # For 'All', we show today's progress as a default view
            day_filter = df["Date"] == datetime.datetime.now(UTC8).strftime("%Y-%m-%d")
        else:
            # For a specific day, filter by the 'Day' column
            day_filter = df["Day"] == selected_day
            
        day_df = df[day_filter & (df["Use Case"] == UC01_ID)].copy()

    except (FileNotFoundError, pd.errors.EmptyDataError):
        return status # Return default if file is empty or not found

    if day_df.empty:
        return status

    # --- Determine Charge Type (AC/DC) ---
    # The 'MODEL' column now directly contains "AC" or "DC" from the selectbox.
    day_df['Charge Type'] = day_df['MODEL']

    # Count completed AC/DC sessions
    status["dc_completed"] = day_df[day_df['Charge Type'] == 'DC'].shape[0]
    status["ac_completed"] = day_df[day_df['Charge Type'] == 'AC'].shape[0]

    # Update the status matrix
    for _, row in day_df.iterrows():
        # Ensure method is a string and strip whitespace for robust matching
        method = str(row["End Method"]).strip()
        charge_type = row["Charge Type"]
        result = row["Test Result"]
        
        # Find which category the method falls into by checking for substrings.
        # The list is ordered to check for "Target SOC" before shorter ones.
        tracked_method = None
        for m in END_METHODS_TO_TRACK:
            if m in method:
                tracked_method = m
                break
        
        if tracked_method and charge_type in CHARGE_TYPES:
            if result == "Pass":
                status["status_df"].loc[tracked_method, charge_type] = '✅'
            elif result == "Failed":
                # Mark as failed, but only if not already passed
                if status["status_df"].loc[tracked_method, charge_type] != '✅':
                    status["status_df"].loc[tracked_method, charge_type] = '❌'

    return status

def get_daily_summary():
    """
    Generates a summary of AC/DC charges per day for UC01.
    """
    record_file = "mission_test_records.csv"
    if not os.path.exists(record_file):
        return pd.DataFrame(columns=["AC", "DC"])

    try:
        df = pd.read_csv(record_file)
        uc01_df = df[df["Use Case"] == "UC01_CC_DC_AC_Sessions"].copy()
        if uc01_df.empty:
            return pd.DataFrame(columns=["AC", "DC"])

        # Group by Day and MODEL (which is Charge Type), then count
        summary = uc01_df.groupby(['Day', 'MODEL']).size().unstack(fill_value=0)

        # Ensure both AC and DC columns exist
        if 'AC' not in summary:
            summary['AC'] = 0
        if 'DC' not in summary:
            summary['DC'] = 0
            
        return summary[['AC', 'DC']]

    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=["AC", "DC"])

# --- UC01 Daily Task Dashboard ---
st.header("UC01 Daily Task Dashboard")

if selected_day == 'All':
    st.markdown("##### Daily AC/DC Charging Summary")
    daily_summary_df = get_daily_summary()
    if not daily_summary_df.empty:
        st.dataframe(daily_summary_df, use_container_width=True)
    else:
        st.info("No UC01 records found to generate a summary.")
else:
    # Pass the selected_day from the sidebar to the function
    uc01_status = get_uc01_status_today(selected_day)

    col1, col2 = st.columns(2)
    col1.metric("DC Charging Progress", f"{uc01_status['dc_completed']} / {uc01_status['dc_target']}")
    col2.metric("AC Charging Progress", f"{uc01_status['ac_completed']} / {uc01_status['ac_target']}")

    st.markdown("##### End Method Tracking Matrix")
    st.dataframe(uc01_status['status_df'], use_container_width=True)

st.markdown("---") # Add a separator

# --- Raw Data Viewer ---
st.markdown("---")
with st.expander("Raw Test Records Log (mission_test_records.csv)"):
    record_file = "mission_test_records.csv"
    if os.path.exists(record_file):
        try:
            raw_df = pd.read_csv(record_file)
            if not raw_df.empty:
                # Convert object columns to string to prevent LargeUtf8 error on Streamlit Cloud
                for col in raw_df.columns:
                    if raw_df[col].dtype == 'object':
                        raw_df[col] = raw_df[col].astype("str")
                st.dataframe(raw_df, use_container_width=True)
            else:
                st.info("The record file is empty.")
        except pd.errors.EmptyDataError:
            st.info("The record file is empty.")
        except Exception as e:
            st.error(f"Could not read the record file: {e}")
    else:
        st.info("No records have been saved yet (`mission_test_records.csv` not found).")