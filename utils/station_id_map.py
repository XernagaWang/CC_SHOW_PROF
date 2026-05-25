"""Build and apply City + Station Name -> station_id for photo lookup."""
import os
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from utils.paths import (
    CPO_ALIASES_CSV,
    ENRICHED_CSV,
    IMAGES_DIR,
    LOGBOOK_APP_CSV,
    STATION_ID_MAP_CSV,
)


def _normalize_station_name(name) -> str:
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return ""
    return str(name).strip().replace("\t", "")


def _load_cpo_pinyin_lookup() -> dict:
    if not CPO_ALIASES_CSV.is_file():
        return {}
    aliases = pd.read_csv(CPO_ALIASES_CSV)
    lookup = {}
    for _, row in aliases.iterrows():
        pinyin = str(row.get("pinyin_name", "")).strip()
        if not pinyin or pinyin == "nan":
            continue
        for col in ("alias", "canonical_name"):
            key = str(row.get(col, "")).strip().lower()
            if key and key != "nan":
                lookup[key] = pinyin
    return lookup


def _cpo_to_pinyin(cpo_name: str, lookup: dict) -> str:
    cpo = str(cpo_name).strip()
    if "/" in cpo:
        cpo = cpo.split("/")[0].strip()
    low = cpo.lower()
    if low in lookup:
        return lookup[low]
    for key, pinyin in lookup.items():
        if key in low or low in key:
            return pinyin
    token = re.sub(r"[^a-z0-9]+", "_", low).strip("_")
    return token or "unknown"


def _list_gz_folders() -> list:
    if not IMAGES_DIR.is_dir():
        return []
    return sorted(
        d.name
        for d in IMAGES_DIR.iterdir()
        if d.is_dir() and d.name.startswith("GZ_")
    )


def _folder_cpo_keys(folder_name: str) -> set:
    parts = folder_name.split("_")
    if len(parts) < 3:
        return set()
    return {parts[1].lower()}


def _match_folder_for_cpo(cpo_name: str, pinyin: str, folders: list, used: set) -> str:
    cpo_raw = str(cpo_name).split("/")[0].strip()
    cpo_token = re.sub(r"[^A-Za-z0-9]", "", cpo_raw).lower()
    pinyin_compact = pinyin.replace("_", "").lower()

    candidates = []
    for folder in folders:
        if folder in used:
            continue
        keys = _folder_cpo_keys(folder)
        if pinyin_compact and any(
            pinyin_compact.startswith(k) or k in pinyin_compact for k in keys
        ):
            candidates.append(folder)
            continue
        if cpo_token and cpo_token in folder.lower():
            candidates.append(folder)
            continue
        if any(k in cpo_raw.lower() for k in keys):
            candidates.append(folder)

    if candidates:
        return sorted(candidates)[0]

    for folder in folders:
        if folder not in used:
            return folder
    return ""


def build_guangzhou_station_map() -> pd.DataFrame:
    if not ENRICHED_CSV.is_file():
        return pd.DataFrame(columns=["city", "station_name", "station_id"])

    enriched = pd.read_csv(ENRICHED_CSV)
    if "Station Name" not in enriched.columns:
        return pd.DataFrame(columns=["city", "station_name", "station_id"])

    gz = enriched[enriched["City"].astype(str) == "广州"].copy()
    if gz.empty:
        return pd.DataFrame(columns=["city", "station_name", "station_id"])

    if "Date" in gz.columns:
        gz["Date"] = pd.to_datetime(gz["Date"], errors="coerce")
        gz = gz.sort_values("Date")

    lookup = _load_cpo_pinyin_lookup()
    folders = _list_gz_folders()
    used = set()
    rows = []

    for station_name, group in gz.groupby("Station Name", sort=False):
        station_name = _normalize_station_name(station_name)
        if not station_name:
            continue
        cpo_col = "CPO" if "CPO" in group.columns else "CPO Name"
        cpo = group.iloc[0].get(cpo_col, "")
        pinyin = _cpo_to_pinyin(cpo, lookup)
        folder_id = _match_folder_for_cpo(cpo, pinyin, folders, used)
        if folder_id:
            used.add(folder_id)
        rows.append({
            "city": "广州",
            "station_name": station_name,
            "station_id": folder_id,
        })

    return pd.DataFrame(rows)


def build_station_id_map() -> pd.DataFrame:
    frames = []

    if LOGBOOK_APP_CSV.is_file():
        cl = pd.read_csv(LOGBOOK_APP_CSV)
        station_col = "Station" if "Station" in cl.columns else "Station Name"
        if station_col in cl.columns and "station_id" in cl.columns and "City" in cl.columns:
            part = cl[["City", station_col, "station_id"]].copy()
            part.columns = ["city", "station_name", "station_id"]
            part["station_name"] = part["station_name"].map(_normalize_station_name)
            part["station_id"] = part["station_id"].astype(str).str.strip()
            part = part[part["station_id"].notna() & (part["station_id"] != "nan")]
            frames.append(part.drop_duplicates(subset=["city", "station_name"]))

    gz_map = build_guangzhou_station_map()
    if not gz_map.empty:
        frames.append(gz_map)

    if not frames:
        return pd.DataFrame(columns=["city", "station_name", "station_id"])

    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates(subset=["city", "station_name"], keep="first")


def load_station_id_map() -> pd.DataFrame:
    if STATION_ID_MAP_CSV.is_file():
        df = pd.read_csv(STATION_ID_MAP_CSV)
    else:
        df = build_station_id_map()
        if not df.empty:
            STATION_ID_MAP_CSV.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(STATION_ID_MAP_CSV, index=False, encoding="utf-8-sig")

    if df.empty:
        return df

    df = df.copy()
    df["station_name"] = df["station_name"].map(_normalize_station_name)
    df["city"] = df["city"].astype(str).str.strip()
    df["station_id"] = df["station_id"].astype(str).str.strip()
    return df.drop_duplicates(subset=["city", "station_name"])


def apply_station_id_map(df: pd.DataFrame, station_map: pd.DataFrame) -> pd.DataFrame:
    if df.empty or station_map.empty:
        return df

    out = df.copy()
    station_col = "Station Name" if "Station Name" in out.columns else "Station"
    if station_col not in out.columns or "City" not in out.columns:
        return out

    out["_map_city"] = out["City"].astype(str).str.strip()
    out["_map_station"] = out[station_col].map(_normalize_station_name)

    merged = out.merge(
        station_map,
        left_on=["_map_city", "_map_station"],
        right_on=["city", "station_name"],
        how="left",
    )

    if "station_id" in merged.columns:
        mapped = merged["station_id"].astype(str).str.strip()
        mapped = mapped.replace({"nan": "", "None": ""})
        if "Station_ID" not in merged.columns:
            merged["Station_ID"] = ""
        current = merged["Station_ID"].astype(str).str.strip()
        empty = current.isna() | current.eq("") | current.eq("nan") | current.str.startswith("GZ_unknown")
        merged.loc[empty & mapped.ne(""), "Station_ID"] = mapped[empty & mapped.ne("")]

    drop_cols = [
        c
        for c in ("_map_city", "_map_station", "city", "station_name", "station_id")
        if c in merged.columns
    ]
    return merged.drop(columns=drop_cols, errors="ignore")
