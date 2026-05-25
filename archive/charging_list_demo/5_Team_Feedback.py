import streamlit as st # type: ignore
import pandas as pd # type: ignore
import os # type: ignore
import subprocess
import shutil
from PIL import Image # type: ignore
from pathlib import Path
import hashlib
import urllib.parse

# --- Page Config ---
st.set_page_config(layout="wide", page_title="Station Facebook")

# --- Global Path Definitions ---
# Photo dir should be relative to the project root (where Streamlit runs)
PHOTO_DIR = "images/structured"
RECORD_FILE = "log_book_final.xlsx" # Keep using the sample Excel file as requested
THUMB_DIR = "images/thumbs"

# --- Check Dependencies ---
if not os.path.exists(PHOTO_DIR):
    st.warning(f"Photo directory '{PHOTO_DIR}' not found. Creating it for you...")
    os.makedirs(PHOTO_DIR)

if not os.path.isfile(RECORD_FILE):
    st.error(f"Record file '{RECORD_FILE}' not found.")
    st.stop()

# --- Data Loading (using original Chinese field names) ---
@st.cache_data
def load_records():
    """Load records from the Excel file and handle station_id."""
    df = pd.read_excel(RECORD_FILE)
    if 'station_id' not in df.columns:
        st.error(f"Error: '{RECORD_FILE}' is missing the 'station_id' column.")
        st.stop()
    
    # Treat station_id as string: keep original formatting (e.g., GZ_BP_001)
    # If numeric IDs exist, convert them to string but preserve as-is to allow mapping.
    df['station_id'] = df['station_id'].astype(str).str.strip()
    df['站點'] = df['站點'].astype(str).str.strip()
    return df

def get_structured_photos(station_id):
    """Find photos in the subfolder corresponding to the station_id."""
    photos = {"pile_left": None, "pile_right": None, "gun": None, "plate": None, "others": []}
    if pd.isna(station_id):
        return photos
    
    station_folder_path = os.path.join(PHOTO_DIR, str(station_id))

    if not os.path.isdir(station_folder_path):
        return photos

    try:
        for filename in sorted(os.listdir(station_folder_path)):
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext not in ['.jpg', '.jpeg', '.png']:
                continue

            path = os.path.join(station_folder_path, filename)
            file_base_name = os.path.splitext(filename)[0]

            if file_base_name == "pile_left":
                photos["pile_left"] = path
            elif file_base_name == "pile_right":
                photos["pile_right"] = path
            elif file_base_name == "gun":
                photos["gun"] = path
            elif file_base_name == "plate":
                photos["plate"] = path
            else:
                photos["others"].append(path)
    except Exception as e:
        st.error(f"Error reading photos: {e}")
    return photos

# --- Main App ---
records_df = load_records()
# Use original Chinese field name '站點' for sidebar selection
unique_stations = sorted(records_df.drop_duplicates(subset=['站點'])['站點'].tolist())

# --- Sidebar: Station Selector (UI Translated) ---
st.sidebar.header("Select Station")
selected_station_name = st.sidebar.selectbox(
    "Select from tested stations:",
    options=["-"] + unique_stations
)

# Support navigation via query parameter: ?station=<station_id>
try:
    params = st.experimental_get_query_params()
    query_station = params.get('station', [None])[0]
except Exception:
    query_station = None

if query_station:
    matches = records_df[records_df['station_id'] == query_station]
    if not matches.empty:
        # map station_id -> 站點 name and override selection
        selected_station_name = matches['站點'].iloc[0]

# --- Main Page Display Logic (UI Translated) ---
if selected_station_name == "-":
    st.title("Station Dossier Overview")
    st.markdown(f"A total of **{len(unique_stations)}** unique stations have been tested so far.")
    # Try to load global index if present
    index_path = Path('images/index.csv')
    if index_path.exists():
        idx = pd.read_csv(index_path)

        cities = sorted(idx['city'].dropna().unique().tolist())
        cpos = sorted(idx['cpo'].dropna().unique().tolist())

        with st.sidebar.expander('Filters'):
            city_filter = st.multiselect('City', options=cities, default=cities)
            cpo_filter = st.multiselect('CPO', options=cpos, default=cpos)
            missing_only = st.checkbox('Show only stations with missing photos')

        filtered = idx[idx['city'].isin(city_filter) & idx['cpo'].isin(cpo_filter)]
        if missing_only:
            filtered = filtered[~(filtered['has_pile_left'] & filtered['has_pile_right'] & filtered['has_gun'] & filtered['has_plate'])]

        st.markdown(f"Showing **{len(filtered)}** stations")

        # Display grid of station cards (4 per row)
        per_row = 4
        records = filtered.to_dict('records')
        for i in range(0, len(records), per_row):
            cols = st.columns(per_row)
            for j, rec in enumerate(records[i:i+per_row]):
                with cols[j]:
                    folder = rec.get('folder_path', '')
                    station_id = rec.get('station_id', '')
                    # Prefer pre-generated thumbnail if available
                    thumb = os.path.join(THUMB_DIR, f"{station_id}.jpg")
                    if not station_id or not os.path.exists(thumb):
                        # fallback to structured folder images
                        thumb = os.path.join(folder, 'pile_left.jpg')
                        if not os.path.exists(thumb):
                            for candidate in ['pile_right.jpg', 'gun.jpg', 'plate.jpg']:
                                cpath = os.path.join(folder, candidate)
                                if os.path.exists(cpath):
                                    thumb = cpath
                                    break

                    if thumb and os.path.exists(thumb):
                        try:
                            img = Image.open(thumb)
                            st.image(img, use_container_width=True)
                        except Exception:
                            st.info('無法載入縮圖')
                    else:
                        st.info('缺少縮圖')

                    # Always show station id, cpo/city and navigation link/details
                    st.markdown(f"**{rec.get('station_id', '')}**")
                    st.caption(f"{rec.get('cpo','')} — {rec.get('city','')}")

                    # Navigation link: open single-station page via query param
                    station_id_for_nav = rec.get('station_id', '')
                    if station_id_for_nav:
                        # include page param so Streamlit opens the correct multipage view
                        page_name = urllib.parse.quote('Team Feedback')
                        nav_link = f"/?page={page_name}&station={urllib.parse.quote(str(station_id_for_nav))}"
                        st.markdown(f"[Open station details]({nav_link})")

                    with st.expander('Details'):
                        st.write(f"Folder: {folder}")
                        st.write(f"Has left: {rec.get('has_pile_left')}")
                        st.write(f"Has right: {rec.get('has_pile_right')}")
                        st.write(f"Has gun: {rec.get('has_gun')}")
                        st.write(f"Has plate: {rec.get('has_plate')}")

    else:
        st.info("Please select a station from the sidebar to view its detailed dossier, or generate `images/index.csv` first.")
    
else:
    # Find records for the selected station name using original field name '站點'
    station_records = records_df[records_df['站點'] == selected_station_name]
    station_id = station_records['station_id'].iloc[0]
    station_latest_record = station_records.iloc[-1] # Using last row as per original logic

    # --- 1. Dynamic Page Title (UI Translated) ---
    cpo_name = station_latest_record.get('CPO Name', 'Unknown CPO')
    st.title(selected_station_name)
    st.subheader(f"Operator (CPO): {cpo_name} | Station ID: {station_id}")
    st.markdown("---")

    # --- 2. Structured Photo Gallery (UI Translated) ---
    st.subheader("📷 Standard Photo Dossier")
    station_photos = get_structured_photos(station_id)

    def show_image_or_placeholder(path, caption):
            if path and os.path.exists(path):
                try:
                    image = Image.open(path)
                    st.image(image, caption=caption, use_container_width=True)
                    return
                except Exception as e:
                    # Try macOS 'sips' to convert HEIF/HEIC to JPEG as a fallback
                    try:
                        conv_dir = Path('images/converted')
                        conv_dir.mkdir(parents=True, exist_ok=True)
                        # create a stable name for converted file based on path
                        h = hashlib.sha1(str(path).encode('utf-8')).hexdigest()[:10]
                        dest = conv_dir / f"{Path(path).stem}_{h}.jpg"
                        if not dest.exists():
                            # call sips for conversion (macOS). If not available, this will fail.
                            subprocess.run(['sips', '-s', 'format', 'jpeg', str(path), '--out', str(dest)], check=False)
                        if dest.exists():
                            img = Image.open(dest)
                            st.image(img, caption=caption, use_container_width=True)
                            return
                    except Exception:
                        pass

                    st.warning(f"Cannot load: {os.path.basename(path)} - {e}")
            else:
                # Translated placeholder message
                st.info(f"Missing '{caption}'")

    cols = st.columns(4)
    with cols[0]:
        show_image_or_placeholder(station_photos["pile_left"], "Charger Photo (Left)")
    with cols[1]:
        show_image_or_placeholder(station_photos["pile_right"], "Charger Photo (Right)")
    with cols[2]:
        show_image_or_placeholder(station_photos["gun"], "Charging Gun (Close-up)")
    with cols[3]:
        show_image_or_placeholder(station_photos["plate"], "Charger Nameplate")

    # --- 3. Other Photos (UI Translated) ---
    if station_photos["others"]:
        st.markdown("---")
        st.subheader("Other Photos")
        other_cols = st.columns(min(5, len(station_photos["others"])))
        for i, photo_path in enumerate(station_photos["others"][:5]):
            with other_cols[i]:
                 show_image_or_placeholder(photo_path, f"Other_{i+1}")

    st.markdown("---")
    
    # --- 4. Core Information (UI Translated, using original field names) ---
    st.subheader("📋 Core Information (Latest Record)")
    m_col1, m_col2, m_col3 = st.columns(3)
    # Use original Chinese field names like '電壓(V)' to get dataㄋ
    m_col1.metric("Rated Voltage (V)", str(station_latest_record.get('Rated Output Voltage(V)', 'N/A')))
    m_col2.metric("Rated Current (A)", str(station_latest_record.get('Rated Output Current(A)', 'N/A')))
    m_col3.metric("Rated Power (kW)", str(station_latest_record.get('Rated Output Power(kW)', 'N/A')))
    
    # Use original Chinese field name '備註' to get data
    st.text_input("Latest Remark", value=station_latest_record.get('Comment', 'None'), disabled=True)

    st.markdown("---")

    # --- 5. Test History (UI Translated, using original field names) ---
    st.subheader("📜 Test History")

    def find_col(df, candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    # Logical fields with potential column name variants
    col_date = find_col(station_records, ['日期', 'Date'])
    col_usecase = find_col(station_records, ['Use Case', 'UseCase', '用例', '測試場景'])
    col_start = find_col(station_records, ['開始時間', '開始', 'Start Time', 'Start', '開始 Time'])
    col_end = find_col(station_records, ['結束時間', '結束', 'End Time', 'End'])
    col_soc = find_col(station_records, ['SOC', 'SoC', 'State of Charge', '電池SOC'])
    col_result = find_col(station_records, ['測試結果', 'Result'])
    col_error = find_col(station_records, ['Error Describe', 'Error', '錯誤描述'])
    col_remark = find_col(station_records, ['備註', 'Comment', 'Remark'])

    # Build dataframe for display with available columns and friendly names
    display_columns = []
    col_map = {}
    if col_date:
        display_columns.append(col_date); col_map[col_date] = 'Date'
    if col_usecase:
        display_columns.append(col_usecase); col_map[col_usecase] = 'Use Case'
    if col_start:
        display_columns.append(col_start); col_map[col_start] = 'Start'
    if col_end:
        display_columns.append(col_end); col_map[col_end] = 'End'
    if col_soc:
        display_columns.append(col_soc); col_map[col_soc] = 'SOC'
    if col_result:
        display_columns.append(col_result); col_map[col_result] = 'Result'
    if col_error:
        display_columns.append(col_error); col_map[col_error] = 'Error'
    if col_remark:
        display_columns.append(col_remark); col_map[col_remark] = 'Remark'

    if not display_columns:
        st.info('No test history columns found in the logbook for this station.')
    else:
        display_df = station_records[display_columns].rename(columns=col_map)
        st.dataframe(display_df, use_container_width=True)