# SHOW 模塊目錄結構

BMW 公共充電驗證 **展示層（SHOW）** 的規範佈局。原 `charging_list_app` 獨立 demo 已併入本倉，不再單獨運行。

## 入口

```bash
streamlit run show_dashboard.py
```

## 目錄說明

```
SHOW_PROF/
├── show_dashboard.py          # 主程式（三 Tab 看板）
├── requirements.txt
├── PROJECT_CONTEXT.md         # 三模塊總覽（PLAN / LOGBOOK / SHOW）
├── SHOW_STRUCTURE.md          # 本文件
├── TODO.md
│
├── views/                     # Tab 頁面
│   ├── tab_national.py
│   ├── tab_mission.py
│   └── tab_stations.py        # 站點庫 + 點選詳情 + 照片
│
├── utils/
│   ├── paths.py               # 路徑常量（單一來源）
│   ├── data_loader.py         # 載入 logbook
│   ├── station_id_map.py      # 站名 → station_id
│   └── station_assets.py      # 按需載入照片
│
├── data/
│   ├── logbooks/              # G70_I490_Logbook_2026.xlsx 等
│   ├── logbook_app_data.csv   # 含 station_id 的彙總（成都等）
│   ├── station_id_map.csv     # 城市+站名 → station_id（可手改）
│   ├── reference/             # enriched、CPO 別名表等
│   └── geocoded/              # 各城市經緯度緩存
│
├── assets/
│   └── images/                # {station_id}/pile_left.png …
│
└── archive/
    ├── charging_list_demo/    # 舊 demo 程式與 notebook（僅備查）
    ├── GZ_new/                # 廣州照片整理批次（已併入 assets/images）
    └── backups/               # 替換前備份
```

## 資料載入順序

1. `data/logbooks/*Logbook*.xlsx`（檔名解析車型 `G70`、軟體版本 `I490`）
2. 若無 xlsx → `data/logbook_app_data.csv`
3. 若仍無 → `data/reference/master_logbook_enriched.csv`

載入後會用 `data/station_id_map.csv` 補上 `Station_ID`，供 Tab3 讀取 `assets/images/{station_id}/`。

## 側欄篩選

- **Vehicle model**：檔名第一段（如 G70）
- **Software version**：檔名第二段（如 I460 / I490）
- **Logbook / campaign**：如 `2025 · I460`
- 全不選 = 顯示全部（與全選相同）

## 已移除 / 歸檔

| 項目 | 處理 |
|------|------|
| `show_result.py` | 已刪除（舊入口，依賴不存在的 `pages/`） |
| `charging_list_app/app.py` | 移至 `archive/charging_list_demo/` |
| `charging_list_app/images/` | 移至 `assets/images/` |
| 根目錄 `GZ_new/` | 移至 `archive/GZ_new/`（內容已覆蓋進 assets） |

`charging_list_app/` 目錄已整體移除。

## PLAN 模塊相關（未納入 SHOW 運行時）

以下仍保留在倉庫根目錄，供路線規劃模塊使用，SHOW 不直接讀取：

- `app.ipynb`、`output/`、`national_charge_station.csv`
- `District/`、`G70_ILC_Logbook.xlsx`
