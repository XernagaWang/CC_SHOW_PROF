from typing import Optional

import pandas as pd
import streamlit as st

from utils.station_assets import (
    PHOTO_SLOTS,
    get_images_root,
    get_station_photo_paths,
    is_displayable_image,
)

PHOTO_LABELS = {
    "pile_left": {"English": "Pile (left)", "Deutsch": "Säule (links)"},
    "pile_right": {"English": "Pile (right)", "Deutsch": "Säule (rechts)"},
    "gun": {"English": "Connector", "Deutsch": "Ladepistole"},
    "plate": {"English": "Plate / signage", "Deutsch": "Typenschild"},
}


def _first_col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _format_value(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M") if pd.notna(value) else "—"
    text = str(value).strip()
    return text if text and text.lower() != "nan" else "—"


def _render_field_row(label: str, value: str) -> None:
    """Label (bold, slightly larger) above value for clearer detail hierarchy."""
    safe_label = label.replace("<", "&lt;").replace(">", "&gt;")
    safe_value = value.replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(
        f'<div style="margin-bottom: 0.65rem;">'
        f'<div style="font-size: 0.92rem; font-weight: 600; opacity: 0.85; '
        f'letter-spacing: 0.02em; margin-bottom: 0.15rem;">{safe_label}</div>'
        f'<div style="font-size: 1.05rem; font-weight: 400; line-height: 1.35;">'
        f"{safe_value}</div></div>",
        unsafe_allow_html=True,
    )


def _aux_power_label(row: pd.Series) -> Optional[str]:
    """Return '24v', '12v', or None if Has_12A_24A not recorded."""
    if "Has_12A_24A" not in row.index:
        return None
    raw = row.get("Has_12A_24A")
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    try:
        return "24v" if int(float(raw)) == 1 else "12v"
    except (TypeError, ValueError):
        return None


def _render_aux_power(row: pd.Series, lang: str, t: dict) -> None:
    label = _aux_power_label(row)
    safe_title = t["aux_power"][lang].replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(
        f'<div style="font-size: 0.92rem; font-weight: 600; opacity: 0.85; '
        f'margin-bottom: 0.25rem;">{safe_title}</div>',
        unsafe_allow_html=True,
    )
    if label == "24v":
        st.warning(t["aux_24v"][lang])
    elif label == "12v":
        st.success(t["aux_12v"][lang])
    else:
        st.caption(t["aux_unknown"][lang])


def _aux_filter_series(df: pd.DataFrame) -> pd.Series:
    """Categorize rows for aux-power filtering: 24v, 12v, unknown."""
    if "Has_12A_24A" not in df.columns:
        return pd.Series(["unknown"] * len(df), index=df.index)

    def categorize(value):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return "unknown"
        try:
            return "24v" if int(float(value)) == 1 else "12v"
        except (TypeError, ValueError):
            return "unknown"

    return df["Has_12A_24A"].map(categorize)


def _apply_aux_filter(df: pd.DataFrame, choice: str) -> pd.DataFrame:
    if choice == "all" or "Has_12A_24A" not in df.columns:
        return df
    cats = _aux_filter_series(df)
    if choice == "24v":
        return df[cats == "24v"]
    if choice == "12v":
        return df[cats == "12v"]
    if choice == "unknown":
        return df[cats == "unknown"]
    if choice == "needs_review":
        return df[cats.isin(["12v", "unknown"])]
    return df


def _station_id_from_row(row: pd.Series) -> str:
    for key in ("Station_ID", "station_id"):
        if key in row.index:
            val = row.get(key)
            if val is not None and str(val).strip() and str(val).lower() != "nan":
                return str(val).strip()
    return ""


def _render_photos(station_id: str, lang: str, t: dict) -> None:
    if not station_id:
        st.info(t["no_photos"][lang].format(station_id="—"))
        return

    photos = get_station_photo_paths(station_id)
    if not any(photos.values()):
        st.info(t["no_photos"][lang].format(station_id=station_id))
        return

    cols = st.columns(len(PHOTO_SLOTS))
    for col, slot in zip(cols, PHOTO_SLOTS):
        path = photos.get(slot)
        with col:
            st.caption(PHOTO_LABELS[slot][lang])
            if path and is_displayable_image(path):
                st.image(str(path), use_container_width=True)
            else:
                st.caption(t["photo_missing"][lang])


def _render_station_history(
    full_df: pd.DataFrame,
    station_id: str,
    lang: str,
    t: dict,
) -> None:
    if not station_id or "Station_ID" not in full_df.columns:
        return

    history = full_df[full_df["Station_ID"].astype(str).str.strip() == station_id]
    if len(history) <= 1:
        return

    with st.expander(t["history_header"][lang].format(count=len(history))):
        hist_cols = [
            c
            for c in ["Date", "Use Case", "Test Result", "Status", "Remark"]
            if c in history.columns
        ]
        st.dataframe(
            history[hist_cols].sort_values("Date", ascending=False, na_position="last"),
            use_container_width=True,
            hide_index=True,
        )


def _render_detail_panel(
    row: pd.Series,
    lang: str,
    t: dict,
    full_df: pd.DataFrame,
) -> None:
    station_id = _station_id_from_row(row)
    station_name = _format_value(row.get("Station Name") or row.get("Station"))
    city = _format_value(row.get("City"))
    cpo = _format_value(row.get("CPO Name") or row.get("CPO"))
    lat = row.get("latitude")
    lon = row.get("longitude")

    st.markdown(f"### {t['detail_title'][lang]}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t["metric_station"][lang], station_name[:40] + ("…" if len(station_name) > 40 else ""))
    m2.metric(t["metric_city"][lang], city)
    m3.metric(t["metric_cpo"][lang], cpo[:28] + ("…" if len(cpo) > 28 else ""))
    m4.metric(t["metric_result"][lang], _format_value(row.get("Test Result")))

    left, right = st.columns([1, 1])
    with left:
        st.markdown(f"**{t['section_session'][lang]}**")
        fields = [
            ("Date", "Date"),
            ("Mission", "Mission"),
            ("Use Case", "Use Case"),
            ("Status", "Status"),
            ("Vehicle Model", "Vehicle Model"),
            ("SW Version", "SW Version"),
            ("Manufacturer", "Manufacturer"),
            ("Power(kW)", "Power(kW)"),
            ("Voltage(V)", "Voltage(V)"),
            ("Current(A)", "Current(A)"),
            ("Start Time", "Start Time"),
            ("End Time", "End Time"),
            ("Start SoC(%)", "Start SoC(%)"),
            ("End SoC(%)", "End SoC(%)"),
            ("End Method", "End Method"),
        ]
        for label_key, col_name in fields:
            if col_name in row.index:
                _render_field_row(label_key, _format_value(row.get(col_name)))

        if "Has_12A_24A" in row.index:
            _render_aux_power(row, lang, t)

        remark = row.get("Remark")
        if remark is not None and str(remark).strip() and str(remark).lower() != "nan":
            _render_field_row(t["remark"][lang], str(remark).strip())

        _render_station_history(full_df, station_id, lang, t)

    with right:
        st.markdown(f"**{t['section_location'][lang]}**")
        if station_id:
            _render_field_row("Station ID", station_id)
        else:
            st.caption(t["no_station_id"][lang])

        if pd.notna(lat) and pd.notna(lon):
            _render_field_row(t["coordinates"][lang], f"{lat}, {lon}")
        else:
            st.caption(t["no_coordinates"][lang])

        st.caption(t["photo_path_hint"][lang].format(path=get_images_root()))

        st.markdown(f"**{t['section_photos'][lang]}**")
        _render_photos(station_id, lang, t)


def render_station_database(filtered_df: pd.DataFrame, lang: str) -> None:
    t = {
        "title": {
            "English": "Station & Log Database",
            "Deutsch": "Station & Log-Datenbank",
        },
        "subtitle": {
            "English": "Click a row for details (photos load on demand from assets/images).",
            "Deutsch": "Zeile anklicken für Details (Fotos aus assets/images).",
        },
        "no_data": {
            "English": "No records match the current filters.",
            "Deutsch": "Keine Datensätze für die aktuellen Filter.",
        },
        "search": {"English": "Search station / CPO / remark", "Deutsch": "Station / CPO / Bemerkung suchen"},
        "result_filter": {"English": "Test result", "Deutsch": "Testergebnis"},
        "city_filter": {"English": "City", "Deutsch": "Stadt"},
        "table_hint": {
            "English": "Select one row (↑↓ then click, or click row header). Details appear below.",
            "Deutsch": "Eine Zeile auswählen — Details erscheinen unten.",
        },
        "rows_shown": {"English": "Rows shown", "Deutsch": "Angezeigte Zeilen"},
        "pick_row": {
            "English": "Select a row above to view station details.",
            "Deutsch": "Wählen Sie oben eine Zeile für Stationsdetails.",
        },
        "detail_title": {"English": "Record detail", "Deutsch": "Datensatzdetails"},
        "metric_station": {"English": "Station", "Deutsch": "Station"},
        "metric_city": {"English": "City", "Deutsch": "Stadt"},
        "metric_cpo": {"English": "CPO", "Deutsch": "CPO"},
        "metric_result": {"English": "Result", "Deutsch": "Ergebnis"},
        "section_session": {"English": "Test session", "Deutsch": "Testsitzung"},
        "section_location": {"English": "Location", "Deutsch": "Standort"},
        "section_photos": {"English": "Photos", "Deutsch": "Fotos"},
        "remark": {"English": "Remark", "Deutsch": "Bemerkung"},
        "coordinates": {"English": "Coordinates", "Deutsch": "Koordinaten"},
        "no_coordinates": {
            "English": "No coordinates on this record.",
            "Deutsch": "Keine Koordinaten in diesem Datensatz.",
        },
        "no_station_id": {
            "English": "No station_id on this record.",
            "Deutsch": "Keine station_id in diesem Datensatz.",
        },
        "no_photos": {
            "English": "No photos under `assets/images/{station_id}/`.",
            "Deutsch": "Keine Fotos unter `assets/images/{station_id}/`.",
        },
        "photo_missing": {"English": "Missing", "Deutsch": "Fehlt"},
        "photo_path_hint": {
            "English": "Photo root: `{path}`",
            "Deutsch": "Fotos unter: `{path}`",
        },
        "history_header": {
            "English": "All tests at this station ({count} records)",
            "Deutsch": "Alle Tests an dieser Station ({count} Einträge)",
        },
        "aux_power": {
            "English": "12V / 24V aux power",
            "Deutsch": "12V / 24V Hilfsstrom",
        },
        "aux_24v": {
            "English": "24V available (Has_12A_24A = yes)",
            "Deutsch": "24V verfügbar (Has_12A_24A = ja)",
        },
        "aux_12v": {
            "English": "12V only (no 24V aux)",
            "Deutsch": "Nur 12V (kein 24V-Hilfsstrom)",
        },
        "aux_unknown": {
            "English": "Not recorded for this session",
            "Deutsch": "Für diese Sitzung nicht erfasst",
        },
        "aux_filter": {
            "English": "12V / 24V aux filter",
            "Deutsch": "12V / 24V Filter",
        },
        "aux_filter_all": {"English": "All", "Deutsch": "Alle"},
        "aux_filter_24v": {
            "English": "24V available",
            "Deutsch": "24V verfügbar",
        },
        "aux_filter_12v": {
            "English": "12V only",
            "Deutsch": "Nur 12V",
        },
        "aux_filter_unknown": {
            "English": "Not recorded",
            "Deutsch": "Nicht erfasst",
        },
        "aux_filter_review": {
            "English": "Needs 24V check (12V only or not recorded)",
            "Deutsch": "24V prüfen (nur 12V oder nicht erfasst)",
        },
    }

    aux_filter_choices = {
        "all": t["aux_filter_all"][lang],
        "24v": t["aux_filter_24v"][lang],
        "12v": t["aux_filter_12v"][lang],
        "unknown": t["aux_filter_unknown"][lang],
        "needs_review": t["aux_filter_review"][lang],
    }

    st.subheader(f"📋 {t['title'][lang]}")
    st.caption(t["subtitle"][lang])

    if filtered_df.empty:
        st.warning(t["no_data"][lang])
        return

    view_df = filtered_df.copy()

    filter_cols = st.columns([2, 1, 1, 1])
    with filter_cols[0]:
        search = st.text_input(t["search"][lang], key="tab3_search")
    with filter_cols[1]:
        result_col = _first_col(view_df, "Test Result")
        if result_col:
            options = sorted(view_df[result_col].dropna().astype(str).unique().tolist())
            selected_results = st.multiselect(
                t["result_filter"][lang],
                options,
                key="tab3_result_filter",
            )
            if selected_results:
                view_df = view_df[view_df[result_col].astype(str).isin(selected_results)]
    with filter_cols[2]:
        city_col = _first_col(view_df, "City")
        if city_col:
            city_options = sorted(view_df[city_col].dropna().astype(str).unique().tolist())
            if len(city_options) > 1:
                selected_cities = st.multiselect(
                    t["city_filter"][lang],
                    city_options,
                    default=city_options,
                    key="tab3_city_filter",
                )
                if selected_cities:
                    view_df = view_df[view_df[city_col].astype(str).isin(selected_cities)]
            elif len(city_options) == 1:
                st.caption(f"📍 {city_options[0]}")
    with filter_cols[3]:
        if "Has_12A_24A" in view_df.columns:
            aux_choice = st.selectbox(
                t["aux_filter"][lang],
                options=list(aux_filter_choices.keys()),
                format_func=lambda k: aux_filter_choices[k],
                key="tab3_aux_filter",
            )
            view_df = _apply_aux_filter(view_df, aux_choice)
        else:
            st.caption("—")

    if search.strip():
        mask = pd.Series(False, index=view_df.index)
        for col in (
            _first_col(view_df, "Station Name", "Station"),
            _first_col(view_df, "CPO Name", "CPO"),
            "Remark",
            "Station_ID",
            "station_id",
        ):
            if col:
                mask |= view_df[col].astype(str).str.contains(
                    search.strip(), case=False, na=False
                )
        view_df = view_df[mask]

    view_df = view_df.reset_index(drop=True)

    table_cols = [
        c
        for c in [
            "Date",
            "Mission",
            "Vehicle Model",
            "SW Version",
            "City",
            "CPO Name",
            "Station Name",
            "Station",
            "Use Case",
            "Status",
            "Test Result",
            "Has_12A_24A",
            "Station_ID",
        ]
        if c in view_df.columns
    ]
    seen = set()
    table_cols = [c for c in table_cols if not (c in seen or seen.add(c))]

    st.caption(t["table_hint"][lang])
    st.caption(f"{t['rows_shown'][lang]}: **{len(view_df)}**")

    table_event = st.dataframe(
        view_df[table_cols] if table_cols else view_df,
        use_container_width=True,
        height=360,
        on_select="rerun",
        selection_mode="single-row",
        key="tab3_log_table",
    )

    selected_rows = []
    if hasattr(table_event, "selection") and table_event.selection:
        selection = table_event.selection
        selected_rows = getattr(selection, "rows", None) or selection.get("rows", [])

    st.divider()

    if not selected_rows:
        st.info(t["pick_row"][lang])
        return

    row_idx = selected_rows[0]
    if row_idx < 0 or row_idx >= len(view_df):
        st.warning(t["pick_row"][lang])
        return

    _render_detail_panel(view_df.iloc[row_idx], lang, t, filtered_df)
