import streamlit as st
import pandas as pd
from utils.data_loader import load_master_data
from views.tab_national import render_national_overview
from views.tab_mission import render_mission_deepdive
from views.tab_stations import render_station_database

st.set_page_config(page_title="BMW EV Public Charging Dashboard", layout="wide", page_icon="⚡")

# 1. 載入原始資料 (Load Data)
df = load_master_data()

# --- Language Selection ---
lang = st.sidebar.radio("🌐 Language / Sprache", ["English", "Deutsch"])

# Translations dictionary
T = {
    "title": {"English": "Public Charging Validation", "Deutsch": "⚡ Öffentliches Laden Validierung"},
    "filters": {"English": "🔍 Global Filters", "Deutsch": "🔍 Globale Filter"},
    "vehicle": {"English": "🚗 Vehicle model", "Deutsch": "🚗 Fahrzeugmodell"},
    "sw_version": {"English": "💾 Software version", "Deutsch": "💾 Softwareversion"},
    "mission": {"English": "📓 Logbook / campaign", "Deutsch": "📓 Logbuch / Kampagne"},
    "tab1": {"English": "🌍 National Overview", "Deutsch": "🌍 Nationale Übersicht"},
    "tab2": {"English": "🚗 Use Case Deep Dive", "Deutsch": "🚗 Detailanalyse der Anwendungsfälle"},
    "tab3": {"English": "🏥 Station & Log Database", "Deutsch": "🏥 Station & Log-Datenbank"},
    "filter_hint": {
        "English": "Tip: clearing a filter shows all (same as selecting all). Filenames: G70_I490_Logbook_2026 → model + SW.",
        "Deutsch": "Tipp: Filter leer = alle anzeigen. Dateiname: G70_I490_Logbook_2026 → Modell + SW.",
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
    
    selected_models = []
    available_vehicle_models = (
        sorted(df["Vehicle Model"].dropna().astype(str).unique().tolist())
        if "Vehicle Model" in df.columns
        else []
    )
    if available_vehicle_models:
        selected_models = st.sidebar.multiselect(
            T["vehicle"][lang],
            available_vehicle_models,
            default=available_vehicle_models[:1],
        )

    available_sw = (
        sorted(df["SW Version"].dropna().astype(str).unique().tolist())
        if "SW Version" in df.columns
        else []
    )
    default_sw = available_sw[:1]
    selected_sw = st.sidebar.multiselect(
        T["sw_version"][lang],
        available_sw,
        default=default_sw,
    )

    available_missions = (
        sorted(df["Mission"].dropna().astype(str).unique().tolist())
        if "Mission" in df.columns
        else []
    )
    default_missions = available_missions[:1]
    selected_missions = st.sidebar.multiselect(
        T["mission"][lang], available_missions, default=default_missions
    )
    st.sidebar.caption(T["filter_hint"][lang])

    # 3. 處理資料過濾 (Apply Filters)
    filtered_df = df.copy()
    if selected_models and "Vehicle Model" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["Vehicle Model"].astype(str).isin(selected_models)
        ]
    if selected_sw and "SW Version" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["SW Version"].astype(str).isin(selected_sw)]
    if selected_missions and "Mission" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["Mission"].astype(str).isin(selected_missions)]
    
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
        render_station_database(filtered_df, lang)
else:
    st.error(T["no_data"][lang])
