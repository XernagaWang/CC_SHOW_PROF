import pandas as pd
import os
import glob
import re
import streamlit as st

@st.cache_data
def load_master_data():
    """
    Loads and combines data from multiple mission logbooks dynamically.
    Parses 'VIN' and 'SW Version' from filenames like G70_I490_Logbook_2026.xlsx.
    """
    data_frames = []
    base_dir = os.path.join(os.path.dirname(__file__), '..')
    
    # 尋找所有包含 "Logbook" 的 Excel 檔案
    search_pattern = os.path.join(base_dir, '*Logbook*.xlsx')
    logbook_files = glob.glob(search_pattern)
    
    if not logbook_files:
        st.warning("No Logbook files found in the directory.")
        return pd.DataFrame()

    for file_path in logbook_files:
        filename = os.path.basename(file_path)
        
        # 略過總和文件
        if 'ILC' in filename or 'master' in filename.lower():
            continue
            
        try:
            df = pd.read_excel(file_path)
            
            # --- 解析檔名以獲取 VIN 和 SW Version ---
            # 假設格式為: {VIN}_{SW_Version}_Logbook_{Year}.xlsx
            # 例如: G70_I490_Logbook_2026.xlsx
            parts = filename.split('_')
            logbook_idx = -1
            for i, part in enumerate(parts):
                if 'Logbook' in part:
                    logbook_idx = i
                    break
            
            # 如果 Logbook 前面有兩個前綴，就認定為 VIN 跟 SW
            if logbook_idx >= 2:
                vin_from_filename = parts[0]
                sw_from_filename = parts[1]
                df['VIN'] = vin_from_filename
                df['SW Version'] = sw_from_filename
                
            # 給一個預設的 Mission 名稱 (例如 Mission: 2026)
            year_part = filename.replace('.xlsx', '').split('_')[-1]
            df['Mission'] = f"{year_part} Mission ({filename})"
            
            # --- 欄位名稱對齊處理 (針對 2025 版舊格式) ---
            df.rename(columns={
                'Test Date': 'Date',
                'Test Vehicle': 'VIN_old', # 避免蓋掉檔名解析出來的
                'Charger Type': 'MODEL'
            }, inplace=True, errors='ignore')
            
            data_frames.append(df)
            
        except Exception as e:
            st.error(f"Error reading `{filename}`: {e}")

    if not data_frames:
        return pd.DataFrame()

    # --- Combine and Clean Data ---
    combined_df = pd.concat(data_frames, ignore_index=True)
    
    # Standardize 'Date'
    if 'Date' in combined_df.columns:
        combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')
    
    # Success tracking
    if 'Test Result' in combined_df.columns:
        combined_df['Success'] = combined_df['Test Result'].apply(lambda x: pd.notna(x) and 'Pass' in str(x))
    else:
        combined_df['Success'] = False 

    # Status filling
    if 'Status' in combined_df.columns:
        combined_df['Status'].fillna('Normal Test', inplace=True)
    else:
        combined_df['Status'] = 'Normal Test'

    # --- Keyword Tagger for Root Causes ---
    def tag_root_cause(row):
        if row['Status'] == 'Normal Test' and row['Success']:
            return 'N/A: Success'
        if row['Status'] != 'Normal Test':
            return f"Site Issue: {row['Status']}"
            
        remark = str(row.get('Remark', '')).lower()
        if any(keyword in remark for keyword in ['超時', 'timeout', '握手']):
            return 'Protocol: Timeout/Handshake'
        elif any(keyword in remark for keyword in ['物理', '干涉', '插槍', 'physical']):
            return 'Hardware: Physical Interference'
        elif any(keyword in remark for keyword in ['app', '掃碼', 'qr']):
            return 'App/Payment Failure'
        elif any(keyword in remark for keyword in ['絕緣', 'insulation']):
            return 'Vehicle: Insulation Failure'
        elif remark.strip() in ['nan', '']:
            return 'Protocol: Unspecified Error'
        else:
            return 'Protocol: Other Error'
            
    combined_df['Root Cause Category'] = combined_df.apply(tag_root_cause, axis=1)

    # --- 解析地理座標及 Use Case ---
    if 'Loacation' in combined_df.columns:
        # 處理中文逗號等可能情況，並拆分為 lat/lon
        coords = combined_df['Loacation'].astype(str).str.replace('，', ',').str.split(',', expand=True)
        if coords.shape[1] >= 2:
            combined_df['latitude'] = pd.to_numeric(coords[0], errors='coerce')
            combined_df['longitude'] = pd.to_numeric(coords[1], errors='coerce')
    elif 'Location' in combined_df.columns:
        coords = combined_df['Location'].astype(str).str.replace('，', ',').str.split(',', expand=True)
        if coords.shape[1] >= 2:
            combined_df['latitude'] = pd.to_numeric(coords[0], errors='coerce')
            combined_df['longitude'] = pd.to_numeric(coords[1], errors='coerce')
            
    # Use Case 清洗 (假設有 Use Case 欄位，例如: 'Use Case', 'Use case', 'use case')
    uc_col = [c for c in combined_df.columns if c.lower().replace(' ', '') == 'usecase']
    if uc_col:
        combined_df['Use Case'] = combined_df[uc_col[0]].fillna('Unknown Use Case')
    else:
        combined_df['Use Case'] = 'Standard Test'
        
    return combined_df
