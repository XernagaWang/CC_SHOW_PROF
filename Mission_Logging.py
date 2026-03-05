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
USE_CASE_OPTIONS = ["AC_UC1_17460722", "AC_UC2_7460719", "AC_UC3_17460723", "DC_UC4_17460724",  "DC_UC5_17460720", "DC_UC6_17460721"]
TEST_STATUS_OPTIONS = ["Normal Test", "Station Inaccessible (Access Control, Construction, etc.)", "Charger Damaged", "Map Navigation Inaccurate", "Other"]
START_METHOD_OPTIONS = ["Scan QR Code", "Insert Card", "APP Operation", "Other"]
HAS_12A_24A_OPTIONS = ["True", "False"]
END_METHOD_OPTIONS = ["reached target SOC", "LAT", "CID", "RFID", "APP", "Other"]
END_REASON_OPTIONS = ["Manual Stop", "Reached Target SoC", "Other"]
TEST_RESULT_OPTIONS = ["None", "Pass", "Failed"]
ERROR_DESCRIBE_OPTIONS = ["None","GBT", "Charger", "ABK", "HVS", "CCU", "LAT", "CID", "PHUD", "Other"]

CITIES = {
    "成都": "CD",
    # "广州": "GZ",
    "重庆": "CQ",
    "贵阳": "GY", 
}

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
    """Load data files based on the city prefix (e.g., CD, GZ)."""
    report_file = f"report_{city_prefix}_enriched.csv"
    hotel_file = f"best_hotel_info_{city_prefix}.json"
    
    try:
        output_path = "output/"
        report_df = pd.read_csv(os.path.join(output_path, report_file))
        # Assuming a general station file is still needed, or we can make this city-specific too
        all_stations_df = pd.read_csv(os.path.join(output_path, "all_map_stations_CD.csv"))
        with open(os.path.join(output_path, hotel_file), "r") as f:
            hotel_info = json.load(f)
        return report_df, all_stations_df, hotel_info
    except FileNotFoundError as e:
        st.error(f"Error: Data file not found for the selected city ({e.filename}). Please ensure reports have been generated.")
        return None, None, None

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
selected_city_name = st.sidebar.selectbox("Current City:", list(CITIES.keys()))
city_prefix = CITIES[selected_city_name]

# For now, strategy is hardcoded, can be a selectbox later if needed.
strategy_prefix = "A" 

# Load data based on selected city
report_df, all_stations_df, hotel_info = load_data(city_prefix)

if report_df is None:
    st.stop()

st.title("Test Log Book")
st.subheader(f"Hotel: {hotel_info.get('Hotel Name', 'N/A')}")

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


st.header("Detail of Each Day")

with st.expander("On-site Test Log Input", expanded=True):
    available_rows = filtered_report_df[~filtered_report_df['目的地'].astype(str).str.contains('完成測試')]
    station_options = available_rows['目的地'].unique().tolist()

    # --- Logic for Manual Station Input ---
    MANUAL_STATION_INPUT = "--- 手动输入新站点 (列表中未找到) ---"
    
    # Add the manual option to the list
    full_station_options = [MANUAL_STATION_INPUT] + station_options

    # Display the selectbox
    selected_option = st.selectbox("Select Test Station", full_station_options)

    # Handle the selection
    if selected_option == MANUAL_STATION_INPUT:
        # If manual input is chosen, show a text input field
        manual_station_name = st.text_input("请输入新站点名称:", key="manual_station_name")
        st.session_state.selected_station_for_submit = manual_station_name
    else:
        # Otherwise, use the selected station from the list
        st.session_state.selected_station_for_submit = selected_option
    
    # We still need to set the day
    st.session_state.selected_day_for_submit = selected_day

    # Only proceed to show the rest of the form if a station has been selected or entered
    if st.session_state.get("selected_station_for_submit"):
        
        # --- Use Case Steps Definition (with partial translation) ---
        AC_UC1_STEPS = [
            {"title": "PRE: Set Charging Method", "details": "Ensure charging method is AC charging."},
            {"title": "PRE: Check SoC", "details": "State of charge of high voltage battery should be < 90%."},
            {"title": "ACTION: Document EVSE Info", "details": "Note EVSE manufacturer, type, and model using the app or sheet."},
            {"title": "ACTION: Set Charging Mode", "details": "Set charging mode to 'charge immediately'."},
            {"title": "ACTION: Set Charging Target", "details": "Set charging target to 100% and deactivate AC-Limit."},
            {"title": "ACTION: Deactivate Auto-Unlock", "details": "Deactivate 'Unlock charging cable after charging end'."},
            {"title": "ACTION: Activate Flap Unlock", "details": "Activate 'Unlock charging socket flap permanently'."},
            {"title": "ACTION: Plug in Cable", "details": "Open the charging flap and plug in the charging plug."},
            {"title": "ACTION: Authenticate", "details": "If needed, authenticate at the charging station (e.g., press start button)."},
            {"title": "ACTION: Check Charging Status", "details": "Expectation: Charging is active."},
            {"title": "ACTION: Read Initial Power", "details": "Read the AC Charging Power. Expectation: Power is plausible."},
            {"title": "ACTION: Adjust Current Limit", "details": "Set any charging current limitation between min/max of the vehicle charging power."},
            {"title": "ACTION: Read Adjusted Power", "details": "Read the AC Charging Power again. Expectation: Power adjusts plausibly."},
            {"title": "ACTION: Terminate Charging", "details": "Terminate 5-10 mins after start via EVSE or CID. Expectation: Terminates without errors."},
            {"title": "ACTION: Check Cable Lock", "details": "Check locking status of charging cable. Expectation: Locked (if ended via EVSE), Unlocked (if ended via CID)."},
            {"title": "ACTION: Unlock and Unplug", "details": "Unlock charging cable via LAT (if needed) and unplug."},
            {"title": "ACTION: Close Flap", "details": "Close the charging flap."},
            {"title": "ACTION: Document Results", "details": "Document test results in the app or sheet. Upload if necessary."}
        ]

        use_case_steps = {
            "AC_UC1_17460722": {"tip": "Follow the 18 steps below to complete the AC charging test.", "steps": AC_UC1_STEPS},
            "DC_UC4_17460724": {"tip": "For this test, please charge for a fixed duration of 3 minutes.", "steps": ["1. Plug in and start charging.", "2. Time for 3 minutes.", "3. Record data and stop charging."]},
            "DC_UC5_17460720": {"tip": "Charge to the target SoC.", "steps": ["1. Set the target SoC.", "2. Plug in to start charging, record the start time.", "3. When target SoC is reached, stop charging and record the end time."]},
            "DC_UC6_17460721": {"tip": "For this test, please charge for a fixed duration of 5 minutes.", "steps": ["1. Plug in and start charging.", "2. Time for 5 minutes.", "3. Record data and stop charging."]},
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
        charger_model = st.text_input("MODEL", "", key="charger_model")
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

        # This download button is now moved to the sidebar for better organization
        # if os.path.isfile("mission_test_records.csv"):
        #     with open("mission_test_records.csv", "rb") as f:
        #         st.download_button(
        #             "Download All Test Records (CSV)",
        #             f,
        #             file_name="mission_test_records.csv",
        #             mime="text/csv"
        #         )
    else:
        st.info("No test stations available for the current selection.")

def generate_ditu_navi_link(row):
    to_name = urllib.parse.quote(str(row['目的地']))
    to_lnglat = f"{row['目的地經度']},{row['目的地緯度']}"
    url = (f"https://ditu.amap.com/dir?type=car&policy=2&to%5Bname%5D={to_name}&to%5Blnglat%5D={to_lnglat}&src=yourAppName")
    return url

with st.expander("Daily Target List (Click to expand)", expanded=False):
    header_cols = st.columns([1, 4, 1])
    header_cols[0].markdown("**Day**")
    header_cols[1].markdown("**Target Station**")
    header_cols[2].markdown("**Navi QR Code**")
    st.markdown("---")

    filtered_navi_df = filtered_report_df[
        ~filtered_report_df['目的地'].astype(str).str.contains('完成測試')
    ]

    for idx, row in filtered_navi_df.iterrows():
        navi_url = generate_ditu_navi_link(row)
        cols = st.columns([1, 4, 1])
        cols[0].write(row['第幾天'])
        cols[1].write(f"{row['目的地']}")
        if cols[2].button("Generate QR Code", key=f"qr_btn_{idx}"):
            st.session_state['current_qr_url'] = navi_url

st.sidebar.header("Navigation QR Code")

if 'current_qr_url' in st.session_state:
    current_row = None
    for idx, row in filtered_navi_df.iterrows():
        if generate_ditu_navi_link(row) == st.session_state['current_qr_url']:
            current_row = row
            break
    if current_row is not None:
        st.sidebar.info(f"**Navigating to: {current_row['目的地']}**")
    else:
        st.sidebar.info("**Navigation QR Code:**")
    qr = qrcode.make(st.session_state['current_qr_url'])
    buf = BytesIO()
    qr.save(buf, format="PNG")
    st.sidebar.image(buf.getvalue(), caption="Scan to navigate", use_column_width=True)
else:
    st.sidebar.info("**Navigation QR Code:**")
    st.sidebar.image("images/qrcode/qrcode_ex.jpg", caption="Try it!")