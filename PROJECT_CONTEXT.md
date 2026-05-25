# BMW 新車公用充電樁驗證項目 (EV Public Charging Validation Project)

## 項目總體目標 (Project Goal)

核心目的是**為了驗證即將上市的新車在全國各種公共充電場景下的充電兼容性與質量**。為此，測試團隊必須在全國範圍內盡可能地測試最多樣、最廣泛的 **CPO** (Charge Point Operator，負責運營公共充電樁的運營商)。

## 項目三大核心模塊 (The Three Modules)

本專案根據外勤測試的時間軸，分為三大獨立且連貫的數位模組：

### 1. PLAN 模塊 (出發前的探索與路線規劃)

- **定位**：利用演算法和地圖資料，規劃出要在特定城市測試的站點名單（涵蓋盡可能多的 CPO 與設備廠商）。
- **產出**：產生特定城市的測試行程表，例如每日拜訪路線和全量站點地圖（例如 `report_XX_enriched.csv`, `all_map_stations_XX.csv`）。

### 2. LOGBOOK 模塊 (任務執行中的即時紀錄)

- **定位**：這是一套專為外勤人員打造的 MVP 工具。聚焦於在極端環境（地下室、弱網）下提供最穩定、無崩潰風險的資料登錄體驗。
- **架構特點**：完全「離線優先 (Offline-first)」，依靠 Streamlit 介面操作 Pandas，資料被即時寫入本地端的 Excel (`Logbook_2026.xlsx`)，不依賴任何外部資料庫，以防實地測試時斷網漏登。
- **具體功能與防呆機制**：
  - **動態 BaseStation 識別**：不會把「酒店」寫死在程式碼裡，而是透過行程表中的 `Start` 事件動態偵測當日下榻地。
  - **極致效能與穩定度**：像是耗費資源的地圖圖層，全面改為 Lazy-load（放入 `st.expander`），避開了手機端崩潰和白屏的問題。
  - **免授權靜默 GPS 紀錄**：不依賴討人厭的手機瀏覽器定位權限，而是在使用者選擇站點並按鈕後，由後台邏輯自全國資料庫 (`all_map_stations_XX.csv`) 中將 `lat` / `lng` 硬塞到送出記錄中。
  - **真實進度條**：明確區分「日誌收集總數 (Log Volumn / Workload)」和「覆蓋的所有獨特站點總數 (Station Coverage Rate)」。
  - **一致性選單**：匯入了清洗過的 `cpo_brand_aliases_with_pinyin.csv` 及設備廠牌清單，供測試員做精準搜尋與點擊。也貼心地設置了「手動輸入逃生門」。

### 3. SHOW / DASHBOARD 模塊 (展示成果與除錯分析)

- **定位**：負責讀取 `LOGBOOK` 所產出的 `Logbook_2026.xlsx`（以及未來的相片與日誌集），透過可視化圖表 (Data Visualization，如 Plotly / Altair 等工具) 將測試結果精煉展示出來。
- **目標**：透過清晰的看板呈現出：「哪些 CPO 成功率高/低」、「設備發生故障的最大根因是什麼 (損壞、不能導航、APP 崩潰)」、「測試覆蓋度是否達到預期」等 KPI 資訊。
- **本倉入口**：`streamlit run show_dashboard.py`；目錄與資料路徑見 **`SHOW_STRUCTURE.md`**（原 `charging_list_app` demo 已併入 `assets/`、`data/`，不再單獨運行）。

---

## 另一個平行專案：DC Wallbox Code Review (SC - Star Charge)

- **Goal:** Audit C++ firmware code (`.diff` files / `.dipatch`) from supplier SC for upcoming releases (e.g., A2026.4.0).
- **Core Domain:** DC Wallbox, ISO-15118 V2G protocols, State Machine logic, OTA (RSU) firmware updates.
- **Review Strategy:**
  - The user represents BMW (buyer/auditor) and may not be a C-level C++ expert.
  - LLM role: Act as a "C++ translator and fault-finder".
  - Key focus areas: Race conditions (fast plugging/unplugging), Booting state deadlocks, Memory handling, Null pointers, Exception/Timeout handling.
  - Requirement for SC: Must provide Sequence Diagrams and AIT (Automated Integration Test) / PCAP logs before reviewing raw C++.

## 使用者協作偏好 (User Preferences)

- Prefers clear, bilingual (Chinese/English) drafts for management communications (e.g., to Timo).
- Focus on practical, actionable advice for dealing with suppliers.
- Keep file directories clean and highly functional.
