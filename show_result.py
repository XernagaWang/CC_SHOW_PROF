import streamlit as st
import pandas as pd

st.set_page_config(page_title="BMW EV QA Dashboard", page_icon="⚡", layout="wide")

st.sidebar.title("⚡ BMW EV Charging QA")
st.sidebar.markdown("---")

nav = st.sidebar.radio("🔍 視圖切換 (Navigation)", ["全國全域巡檢 (National)", "特定站點下鑽 (Mission)"])

if nav == "全國全域巡檢 (National)":
    from pages.tab_national import render_national_tab
    render_national_tab()
else:
    from pages.tab_mission import render_mission_tab
    render_mission_tab()
