import streamlit as st
import pandas as pd
import os
import json
from PIL import Image
from pathlib import Path

# --- Page Config ---
st.set_page_config(layout="wide", page_title="Charging Station Field Guide")

# --- Internationalization (i18n) ---
@st.cache_data
def load_translations(file_path="locales.json"):
    """Loads translation strings from a JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"Translation file not found: {file_path}")
        return {}

i18n = load_translations()

# --- Language Selector ---
st.sidebar.title("Language / 語言")
# Set default language to English by setting index=1
lang_options = ['zh', 'en', 'de']
lang_choice = st.sidebar.selectbox(
    "Select Language",
    options=lang_options,
    index=1,  # Default to 'en'
    format_func=lambda x: {"zh": "中文", "en": "English", "de": "Deutsch"}[x],
    key='lang'
)

# Helper to get translated text
def T(key, **kwargs):
    """Gets a translated string by key."""
    if key in i18n and lang_choice in i18n.get(key, {}):
        return i18n[key][lang_choice].format(**kwargs)
    # Fallback to the key itself if translation is missing
    return key

# --- Global Path & File Definitions ---
PHOTO_DIR = "images" 
DATA_FILE = "logbook_app_data.csv" 

# --- Helper Functions ---
@st.cache_data
def load_data():
    """Loads data from the final CSV file."""
    if not os.path.exists(DATA_FILE):
        # Use T() for the error message, but it might not be fully initialized on first load
        st.error(i18n.get("data_file_error", {}).get(lang_choice, f"Error: Data file {DATA_FILE} not found.").format(file=DATA_FILE))
        return pd.DataFrame()
    df = pd.read_csv(DATA_FILE)
    # Ensure essential columns exist
    for col in ['station_id', 'CPO Name', 'Station', 'City', 'Test Result', 'Remark', 'Status', 'Manufacturer', 'Power(kW)', 'Voltage(V)', 'Current(A)', 'Has_12A_24A', 'National_Impact_Share (%)']:
        if col not in df.columns:
            df[col] = 'N/A'
    return df

# In app.py

# ... (之前的程式碼) ...

def find_station_photos(station_id):
    """
    Finds photos for a given station_id using simple relative paths.
    """
    photos = {"pile_left": None, "pile_right": None, "gun": None, "plate": None, "others": []}
    if pd.isna(station_id) or station_id == 'N/A':
        return photos

    station_folder_path = os.path.join(PHOTO_DIR, str(station_id).strip())
    print(station_folder_path)
    photos["pile_left"] = os.path.join(station_folder_path, "pile_left.png")
    photos["pile_right"] = os.path.join(station_folder_path, "pile_right.png")
    photos["gun"] = os.path.join(station_folder_path, "gun.png")
    photos["plate"] = os.path.join(station_folder_path, "plate.png")
        
    return photos

def display_photo(path, caption_key):
    """
    Displays a photo from a local path.
    """
    caption = T(caption_key)
    if path and os.path.exists(path):
        try:
            image = Image.open(path)
            st.image(image, caption=caption)
        except Exception as e:
            st.warning(f"Cannot load image: {os.path.basename(path)}")
    else:
        st.info(T("missing_photo", caption=caption))

# --- Main App Logic ---
st.title(T("main_title"))

# Load data
all_data = load_data()

if all_data.empty:
    st.stop()

# --- 1. Dashboard ---
st.header(T("dashboard_header"))
col1, col2, col3 = st.columns(3)

total_scouted = all_data['station_id'].nunique()
problem_station_ids = all_data[all_data['Status'] != 'Normal Test']['station_id'].unique()
inaccessible_stations = len(problem_station_ids)
successful_stations = total_scouted - inaccessible_stations

col1.metric(T("total_scouted"), total_scouted)
col2.metric(T("successful_stations"), successful_stations)
col3.metric(T("problem_stations"), inaccessible_stations)

# --- 2. Search & Filter ---
st.header(T("search_header"))
search_query = st.text_input(T("search_placeholder"))

with st.expander(T("advanced_filter")):
    unique_cities = sorted(all_data['City'].dropna().unique())
    unique_cpos = sorted(all_data['CPO Name'].dropna().unique())
    
    selected_cities = st.multiselect(T("city_filter"), options=unique_cities)
    selected_cpos = st.multiselect(T("cpo_filter"), options=unique_cpos)

# Filter data based on search and filters
filtered_data = all_data
if search_query:
    filtered_data = filtered_data[
        filtered_data['Station'].str.contains(search_query, case=False, na=False) |
        filtered_data['CPO Name'].str.contains(search_query, case=False, na=False) |
        filtered_data['station_id'].str.contains(search_query, case=False, na=False)
    ]
if selected_cities:
    filtered_data = filtered_data[filtered_data['City'].isin(selected_cities)]
if selected_cpos:
    filtered_data = filtered_data[filtered_data['CPO Name'].isin(selected_cpos)]

# --- 3. Results Display ---
st.markdown(T("records_found", count=len(filtered_data)))

if not filtered_data.empty:
    station_options = filtered_data['Station'].unique()
    selected_station_name = st.selectbox(T("select_station_prompt"), options=["-"] + list(station_options))

    if selected_station_name != "-":
        station_records = filtered_data[filtered_data['Station'] == selected_station_name]
        latest_record = station_records.iloc[-1]
        station_id = latest_record['station_id']

        st.markdown("---")
        
        # --- CPO & Station Title ---
        cpo_name = latest_record['CPO Name']
        national_impact = latest_record.get('National_Impact_Share (%)')
        
        st.subheader(f"📍 {selected_station_name}")
        
        caption_parts = [T("cpo_caption", cpo_name=cpo_name)]
        if pd.notna(national_impact):
            caption_parts.append(T("national_share_caption", share=national_impact))
        else:
            caption_parts.append(T("new_discovery_caption"))
            
        caption_parts.append(T("station_id_caption", station_id=station_id))
        
        st.caption(" | ".join(caption_parts))

        # --- Core Information & Alerts ---
        st.subheader(T("core_info_header"))
        
        latest_result = latest_record.get('Test Result', 'N/A')
        latest_remark = latest_record.get('Remark', '')

        if latest_result == 'Pass':
            st.success(T("latest_test_result", result=latest_result))
        else:
            st.error(T("latest_test_result", result=latest_result))

        st.text_input(T("latest_remark"), value=latest_remark, disabled=True)
        
        st.markdown("---")

        # --- Core Specs ---
        st.subheader(T("core_specs_header"))
        
        spec_cols = st.columns(4)
        with spec_cols[0]:
            st.text(T("manufacturer"))
            st.info(latest_record.get('Manufacturer', 'N/A'))
        with spec_cols[1]:
            st.metric(T("rated_power"), str(latest_record.get('Power(kW)', 'N/A')))
        with spec_cols[2]:
            st.metric(T("rated_voltage"), str(latest_record.get('Voltage(V)', 'N/A')))
        with spec_cols[3]:
            st.metric(T("rated_current"), str(latest_record.get('Current(A)', 'N/A')))

        # 12V/24V Support
        has_12_24 = latest_record.get('Has_12A_24A', 0)
        st.text(T("aux_power"))
        if has_12_24 == 1:
            st.error(T("aux_24v_available"))
        else:
            st.success(T("aux_12v_only"))

        st.markdown("---")

        # --- Photo Gallery ---
        st.subheader(T("photos_header"))
        photos = find_station_photos(station_id)
        p_cols = st.columns(4)
        with p_cols[0]:
            display_photo(photos["pile_left"], "photo_pile_left")
        with p_cols[1]:
            display_photo(photos["pile_right"], "photo_pile_right")
        with p_cols[2]:
            display_photo(photos["gun"], "photo_gun")
        with p_cols[3]:
            display_photo(photos["plate"], "photo_plate")
        
        # --- Test History ---
        with st.expander(T("history_header")):
            display_cols = ['Date', 'Use Case']
            display_cols = [col for col in display_cols if col in station_records.columns]
            history_df_display = station_records[display_cols].astype(str)
            st.dataframe(station_records[display_cols])
else:
    st.info(T("no_match"))