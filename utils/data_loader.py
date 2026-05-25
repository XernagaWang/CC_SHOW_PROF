import glob
from typing import Optional

import pandas as pd
import streamlit as st

from utils.paths import (
    ENRICHED_CSV,
    LOGBOOKS_DIR,
    LOGBOOK_APP_CSV,
    PROJECT_ROOT,
)
from utils.station_id_map import apply_station_id_map, load_station_id_map


def _parse_logbook_filename(filename: str) -> tuple:
    """
    Parse names like G70_I490_Logbook_2026.xlsx ->
    vehicle_model=G70, sw_version=I490, mission_label='2026 · I490'
    """
    stem = filename.replace(".xlsx", "").replace(".xls", "")
    parts = stem.split("_")
    logbook_idx = -1
    for i, part in enumerate(parts):
        if "Logbook" in part:
            logbook_idx = i
            break

    vehicle_model = parts[0] if logbook_idx >= 1 else "Unknown"
    sw_version = parts[1] if logbook_idx >= 2 else "Unknown"
    year = parts[-1] if parts and str(parts[-1]).isdigit() else ""
    mission_label = f"{year} · {sw_version}" if year else sw_version
    return vehicle_model, sw_version, mission_label


def _finalize_master_df(combined_df: pd.DataFrame) -> pd.DataFrame:
    """Shared cleaning and derived columns for all logbook sources."""
    if "Date" in combined_df.columns:
        combined_df["Date"] = pd.to_datetime(combined_df["Date"], errors="coerce")

    if "Test Result" in combined_df.columns:
        combined_df["Success"] = combined_df["Test Result"].apply(
            lambda x: pd.notna(x) and "Pass" in str(x)
        )
    else:
        combined_df["Success"] = False

    if "Status" in combined_df.columns:
        combined_df["Status"] = combined_df["Status"].fillna("Normal Test")
    else:
        combined_df["Status"] = "Normal Test"

    def tag_root_cause(row):
        if row["Status"] == "Normal Test" and row["Success"]:
            return "N/A: Success"
        if row["Status"] != "Normal Test":
            return f"Site Issue: {row['Status']}"

        remark = str(row.get("Remark", "")).lower()
        if any(keyword in remark for keyword in ["超時", "timeout", "握手"]):
            return "Protocol: Timeout/Handshake"
        if any(keyword in remark for keyword in ["物理", "干涉", "插槍", "physical"]):
            return "Hardware: Physical Interference"
        if any(keyword in remark for keyword in ["app", "掃碼", "qr"]):
            return "App/Payment Failure"
        if any(keyword in remark for keyword in ["絕緣", "insulation"]):
            return "Vehicle: Insulation Failure"
        if remark.strip() in ["nan", ""]:
            return "Protocol: Unspecified Error"
        return "Protocol: Other Error"

    combined_df["Root Cause Category"] = combined_df.apply(tag_root_cause, axis=1)

    if "Loacation" in combined_df.columns:
        coords = combined_df["Loacation"].astype(str).str.replace("，", ",").str.split(",", expand=True)
        if coords.shape[1] >= 2:
            combined_df["latitude"] = pd.to_numeric(coords[0], errors="coerce")
            combined_df["longitude"] = pd.to_numeric(coords[1], errors="coerce")
    elif "Location" in combined_df.columns:
        coords = combined_df["Location"].astype(str).str.replace("，", ",").str.split(",", expand=True)
        if coords.shape[1] >= 2:
            combined_df["latitude"] = pd.to_numeric(coords[0], errors="coerce")
            combined_df["longitude"] = pd.to_numeric(coords[1], errors="coerce")

    uc_col = [c for c in combined_df.columns if c.lower().replace(" ", "") == "usecase"]
    if uc_col:
        combined_df["Use Case"] = combined_df[uc_col[0]].fillna("Unknown Use Case")
    elif "Use Case" not in combined_df.columns:
        combined_df["Use Case"] = "Standard Test"

    if "CPO" in combined_df.columns and "CPO Name" not in combined_df.columns:
        combined_df["CPO Name"] = combined_df["CPO"]

    if "Station" in combined_df.columns and "Station Name" not in combined_df.columns:
        combined_df["Station Name"] = combined_df["Station"]

    station_id_col = next(
        (c for c in combined_df.columns if c.lower().replace(" ", "") in ("stationid", "station_id")),
        None,
    )
    if station_id_col:
        combined_df["Station_ID"] = combined_df[station_id_col].astype(str).str.strip()

    if "Remark" not in combined_df.columns and "Error Describe" in combined_df.columns:
        combined_df["Remark"] = combined_df["Error Describe"]

    return combined_df


def _load_charging_list_data() -> Optional[pd.DataFrame]:
    if not LOGBOOK_APP_CSV.is_file():
        return None

    df = pd.read_csv(LOGBOOK_APP_CSV)
    if df.empty:
        return None

    if "Mission" not in df.columns:
        df["Mission"] = "2026 Charging List"
    if "Vehicle Model" not in df.columns:
        df["Vehicle Model"] = "G70"
    if "SW Version" not in df.columns:
        df["SW Version"] = "—"

    combined = _finalize_master_df(df)
    return apply_station_id_map(combined, load_station_id_map())


def _load_logbook_excel_files() -> Optional[pd.DataFrame]:
    """Load G70_*_Logbook_*.xlsx from data/logbooks/ (skips ILC aggregate files)."""
    logbook_files = sorted(LOGBOOKS_DIR.glob("*Logbook*.xlsx"))
    data_frames = []

    for file_path in logbook_files:
        filename = file_path.name
        if "ILC" in filename or "master" in filename.lower():
            continue

        try:
            df = pd.read_excel(file_path)
            vehicle_model, sw_version, mission_label = _parse_logbook_filename(filename)

            df["Vehicle Model"] = vehicle_model
            df["SW Version"] = sw_version
            df["Mission"] = mission_label
            df["Logbook File"] = filename

            df.rename(columns={
                "Test Date": "Date",
                "Charger Type": "MODEL",
            }, inplace=True, errors="ignore")

            if "Station" in df.columns and "Station Name" not in df.columns:
                df["Station Name"] = df["Station"]

            data_frames.append(df)
        except Exception as e:
            st.error(f"Error reading `{filename}`: {e}")

    if not data_frames:
        return None

    combined = _finalize_master_df(pd.concat(data_frames, ignore_index=True))
    return apply_station_id_map(combined, load_station_id_map())


@st.cache_data
def load_master_data():
    """
    Loads master logbook data. Priority:
    1. data/logbooks/*Logbook*.xlsx (vehicle + SW from filename)
    2. data/logbook_app_data.csv (station_id for photos)
    3. data/reference/master_logbook_enriched.csv fallback
    """
    logbook_df = _load_logbook_excel_files()
    if logbook_df is not None and not logbook_df.empty:
        return logbook_df

    charging_list_df = _load_charging_list_data()
    if charging_list_df is not None and not charging_list_df.empty:
        return charging_list_df

    if ENRICHED_CSV.is_file():
        df = pd.read_csv(ENRICHED_CSV)
        if "Mission" not in df.columns:
            df["Mission"] = "2026 Enriched Logbook"
        if "Vehicle Model" not in df.columns:
            df["Vehicle Model"] = "G70"
        if "SW Version" not in df.columns:
            df["SW Version"] = "—"
        combined = _finalize_master_df(df)
        return apply_station_id_map(combined, load_station_id_map())

    st.warning("No logbook data found. Add files under data/logbooks/ or data/logbook_app_data.csv.")
    return pd.DataFrame()
