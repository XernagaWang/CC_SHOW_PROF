import streamlit as st
import pandas as pd
from utils.data_loader import load_master_data
from views.tab_national import render_national_overview
from views.tab_mission import render_mission_deepdive

st.set_page_config(page_title="BMW EV Public Charging Dashboard", layout="wide", page_icon="⚡")

# 1. 載入原始資料 (Load Data)
df = load_master_data()

# --- Language Selection ---
lang = st.sidebar.radio("🌐 Language / Sprache", ["English", "Deutsch"])

# Translations dictionary
T = {
    "title": {"English": "Public Charging Validation", "Deutsch": "⚡ Öffentliches Laden Validierung"},
    "filters": {"English": "🔍 Global Filters", "Deutsch": "🔍 Globale Filter"},
    "vin": {"English": "🚗 Vehicle VIN", "Deutsch": "🚗 Fahrzeug-VIN"},
    "mission": {"English": "🎯 Test Mission", "Deutsch": "🎯 Testmission"},
    "tab1": {"English": "🌍 National Overview", "Deutsch": "🌍 Nationale Übersicht"},
    "tab2": {"English": "🚗 Use Case Deep Dive", "Deutsch": "🚗 Detailanalyse der Anwendungsfälle"},
    "tab3": {"English": "🏥 Station & Log Database", "Deutsch": "🏥 Station & Log-Datenbank"},
    "tab3_info": {
        "English": "🚧 Tab 3 under construction... (Waiting for Master Logbook / Station ID mappings)",
        "Deutsch": "🚧 Tab 3 im Aufbau... (Warten auf Master-Logbuch / Station ID Mappings)"
    },
    "no_data": {
        "English": "❌ No test data found. Please ensure Logbook Excel files are in the directory.",
        "Deutsch": "❌ Keine Testdaten gefunden. Bitte überprüfen Sie, ob Logbuch-Excel-Dateien im Verzeichnis vorhanden sind."
    }
}

st.title(T["title"][lang])
st.markdown("---")

if df is not None and not df.empty:
    
    # 2. 建立側邊欄過濾器 (Sidebar Filters)
    st.sidebar.header(T["filters"][lang])
    
    available_vins = sorted(df['VIN'].dropna().unique().tolist()) if 'VIN' in df.columns else []
    selected_vins = st.sidebar.multiselect(T["vin"][lang], available_vins, default=available_vins)
    
    available_missions = sorted(df['Mission'].dropna().unique().tolist()) if 'Mission' in df.columns else []
    selected_missions = st.sidebar.multiselect(T["mission"][lang], available_missions, default=available_missions)
    
    # 3. 處理資料過濾 (Apply Filters)
    filtered_df = df.copy()
    if selected_vins and 'VIN' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['VIN'].isin(selected_vins)]
    if selected_missions and 'Mission' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Mission'].isin(selected_missions)]
    
    # 4. 渲染頁籤 (Render Tabs)
    tab1, tab2, tab3 = st.tabs([
        T["tab1"][lang], 
        T["tab2"][lang], 
        T["tab3"][lang]
    ])
    
    with tab1:
        render_national_overview(filtered_df, lang)
        
    with tab2:
        render_mission_deepdive(filtered_df, lang)
        
    with tab3:
        st.info(T["tab3_info"][lang])
        st.dataframe(filtered_df)
else:
    st.error(T["no_data"][lang])
