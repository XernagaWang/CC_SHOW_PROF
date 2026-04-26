# TODO for Dashboard Development

- [ ] **(P0) Implement Core KPIs on Dashboard**:
  - Total Tests
  - Unique Stations Tested
  - Overall Pass Rate
  - Cities Covered
  - Total DC/AC Charges
- [ ] **(P0) Implement Failure Analysis Charts**:
  - Bar chart for failure reasons based on 'Status' and 'Test Result' columns.
  - Pie chart for failure source (Infrastructure vs. Vehicle), requires mapping 'Status' to source.
- [ ] **(P1) Add Interactive Filters**:
  - Filters for City, Date Range, Test Result, CPO Name.
- [ ] **(P2) Address Geodata Prerequisite for Maps**:
  - Devise a strategy to add Latitude/Longitude to all records in `Logbook_2026.xlsx`.
  - This is a blocker for any map-based visualizations.
- [ ] **(P2) Implement Hexagon Grid Map on a "Plan" Page**:
  - As discussed, this feature is best suited for a future "Plan" page to guide test planning.
  - It requires the geodata prerequisite above and a master list of all national CPOs.

# 待办：照片整理与展示（生成 2026-02-28）

1. 创建样例索引 `images/index.csv` 与城市/CPO 映射模板 `city_cpo_mapping.csv`（已创建示例文件）。
2. 确认 `city` 与 `CPO` 的缩写映射表（CSV）：字段格式为 `city_code,cpo_code,city_name,cpo_name`。
3. 实现可幂等的 ingestion/整理脚本：
   - 读取 `images/raw/` 中的原始上傳文件，按 `station_id` 模式匹配。
   - 将匹配到的文件移动/归档到 `images/structured/{station_id}/`，并标准化文件名。
   - 为每个站点生成或更新 `meta.json`（包含站点信息与照片映射）。
   - 原子性更新 `images/index.csv`，并输出本次整理报告 `photo_report.csv`。
4. 在整理阶段生成缩略图 `thumbs/` 以提高展示性能（可选）。
5. 更新 `pages/5_Team_Feedback.py`：优先读取 `images/index.csv` 与 `meta.json`，展示四张标准照片并在缺图时显示中文占位说明。
6. 为整理脚本添加单元测试（文件匹配、移动、meta 生成等）。
7. 将上传/整理工作流程写入 `docs/PHOTO_WORKFLOW.md`。
8. （可选）扩展为支持 S3/远程存储并在 `meta.json` 中存放 URL，以便扩展至大量图片。

## 路测 Logbook 应用最终测试清单

**目标：** 验证应用在模拟真实使用场景下的数据加载、信息录入、照片拍摄、数据保存和导出的完整流程。

---

### 第一部分：应用初始化与数据加载

- [x] **1.1 城市切换**
  - **操作步骤：**
    1. 打开应用，进入 Logbook 页面。
    2. 在左侧边栏，将城市从“广州”切换到“重庆”，再切换到“贵阳”。
  - **预期结果：**
    - 页面能正常加载，不报错。
    - 酒店名称、总天数、任务总数等“Mission Overview”指标会根据不同城市的数据 (`report_XX_enriched.csv`) 相应更新。
    - “Select Test Station”下拉列表中的站点会更新为所选城市和日期的站点。

- [x] **1.2 按天筛选**
  - **操作步骤：**
    1. 选择一个城市（如“广州”）。
    2. 在左侧边栏，将“Filter by day”从“All”切换到“Day 1”，再到“Day 2”。
  - **预期结果：**
    - “Today's Test Plan”指标会更新为当天计划的站点数。
    - “Select Test Station”下拉列表中的站点会减少，只显示当天未测试的站点。

---

### 第二部分：核心功能 - 数据录入与提交

- [x] **2.1 空表单检查**
  - **操作步骤：**
    1. 选择一个测试站点。
    2. **不要填写任何信息**。
  - **预期结果：**
    - “Submit Record”按钮应为灰色，不可点击。

- [x] **2.2 完整提交流程**
  - **操作步骤：**
    1. **选择一个站点**（例如，广州的某个站点）。
    2. **填写所有字段**：Use Case, Status, CPO Name (请使用英文，如 `TESTCPO`), 充电桩信息, 开始/结束方法等。
    3. **点击“Record Start Time”和“Record End Time”按钮**。
  - **预期结果：**
    - 按钮点击后，对应的时间输入框会显示**当前东八区（UTC+8）时间**。
    - “Submit Record”按钮变为可点击状态。

- [x] **2.3 照片拍摄**
  - **操作步骤：**
    1. 按照提示，依次完成 4 张照片的拍摄。
    2. 拍摄完成后，点击“重新拍摄所有照片”按钮。
  - **预期结果：**
    - 每拍完一张，应用会自动跳转到下一步。
    - 页面下方会显示已拍摄照片的预览图。
    - 4 张全部拍完后，会显示成功提示。
    - 点击“重新拍摄”后，拍摄流程会从第 1 步重新开始，旧照片被清空。

- [ ] **2.4 提交与重置**
  - **操作步骤：**
    1. 完成所有信息填写和照片拍摄后，点击“Submit Record”。
  - **预期结果：**
    - 页面显示“Record saved successfully!”的绿色成功提示。
    - 整个表单（包括所有输入框、下拉菜单、照片）应被**自动清空**，恢复到初始状态。
    - 页面刷新，准备下一次记录。

---

### 第三部分：数据验证与导出

- [x] **3.1 文件生成验证**
  - **操作步骤：**
    1. 提交一次记录后，在您的项目文件夹中检查。
    2. 检查 `images/structured/` 目录。
    3. 检查 `mission_test_records.csv` 文件。
  - **预期结果：**
    - `images/structured/`下应创建了一个新的文件夹，命名格式为 `城市代码_CPO名称_序号` (例如 `GZ_TESTCPO_001`)。
    - 该文件夹内应包含 4 张 `.png` 照片和 1 个 `meta.json` 文件。
    - 打开 `meta.json`，检查 `last_updated` 时间是否为**东八区时间**。
    - 打开 `mission_test_records.csv`，文件末尾应增加了一行刚刚提交的记录，`Date` 和时间相关字段也应为**东八区时间**。

- [x] **3.2 打包下载**
  - **操作步骤：**
    1. 在侧边栏，点击“Prepare Full Archive for Download”。
    2. 等待打包完成后，点击出现的“Download Full Archive (ZIP)”按钮。
    3. 解压下载的 `.zip` 文件。
  - **预期结果：**
    - 打包过程有“loading”提示。
    - 能够成功下载一个 `.zip` 文件，文件名包含**东八区时间**的时间戳。
    - 解压后，压缩包内应包含 `mission_test_records.csv` 文件和一个 `structured` 文件夹，其内容与您在步骤 3.1 中验证的完全一致。

## 新增 Use Case 任务 (2026-03-06)

### Use Case 1: UC01_CC_DC_AC_Sessions (综合交直流充电任务)

- **核心要求**: 每个测试日完成 5 次直流快充 (DC) 和 2 次交流慢充 (AC)。
- **关键约束**: 每次充电需要尝试使用不同的结束方式，以全面验证功能。
- **已知结束方式**:
  - **LAT**: 按下充电口旁的物理“充电中止按钮”。
  - **Target SOC**: 达到预设的目标电量后自动停止。
  - **EVSE stop**: 在充电桩设备上手动停止。
  - **HMI**: 在车机中控屏幕上手动停止。

### 优化建议与每日回顾页面功能

- **目标**: 在 `pages/1_Daily_Review.py` 页面中增加一个仪表盘，用于追踪 `UC01` 的完成情况。
- **功能点**:
  - [x] **创建追踪表格**: 设计一个表格或一组指标卡，实时显示当天已完成的充电次数。
    - DC 充电: `x / 5`
    - AC 充电: `y / 2`
  - [x] **记录结束方式**: 在表格中清晰地列出当天已经使用过的充电结束方式 (例如，`LAT`, `Target SOC` 等)，并标记其使用次数。这可以帮助测试人员确保多样性，避免重复。

---

### 应用功能完整性测试计划 (表格版)

| 分类 | 测试项 | 状态 | 操作步骤 | 预期结果 |
| :--- | :--- | :--- | :--- | :--- |
| **初始化与数据验证** | **1.1 城市切换** | `[ ]` | 1. 在侧边栏切换不同城市（成都、重庆、贵阳）。 | 1. 页面正常加载，不报错。<br>2. "Mission Overview" 指标和 "Select Test Station" 列表根据所选城市更新。 |
| | **1.2 按天筛选** | `[ ]` | 1. 选择一个城市。<br>2. 在侧边栏切换不同日期（All, Day 1, Day 2...）。 | 1. "Today's Test Plan" 指标更新。<br>2. "Select Test Station" 和 "Daily Target List" 中的站点列表根据所选日期筛选。 |
| | **1.3 UC02 标志验证** | `[ ]` | 1. 浏览 "Daily Target List"。 | 1. 对于 `max_dc_power` > 151.2 kW 的充电站，其 "Features" 列应显示 `🌡️🔋 vWM` 图标。 |
| **核心功能** | **2.1 空表单检查** | `[ ]` | 1. 选择一个测试站点。<br>2. **不填写任何信息**。 | 1. "Submit Record" 按钮为灰色，不可点击。 |
| | **2.2 完整提交流程** | `[ ]` | 1. 选择一个站点。<br>2. 完整填写所有字段（Use Case, CPO Name, 充电桩信息等）。<br>3. 点击 "Record Start Time" 和 "Record End Time"。 | 1. 时间输入框显示当前东八区时间。<br>2. "Submit Record" 按钮变为可点击。 |
| | **2.3 照片拍摄** | `[ ]` | 1. 按照提示，依次完成 4 张照片的拍摄。<br>2. 拍摄完成后，点击 "重新拍摄所有照片"。 | 1. 每拍完一张，自动进入下一步。<br>2. 页面下方显示照片预览。<br>3. 点击 "重新拍摄" 后，流程重置，旧照片清空。 |
| | **2.4 提交与重置** | `[ ]` | 1. 完成所有信息填写和照片拍摄后，点击 "Submit Record"。 | 1. 显示 "Record saved successfully!" 提示。<br>2. 整个表单被自动清空，恢复初始状态。 |
| **数据验证与导出** | **3.1 文件生成验证** | `[ ]` | 1. 提交一次记录后，检查项目文件夹。 | 1. `mission_test_records.csv` 末尾增加一行新记录。<br>2. `images/structured/` 下创建 `城市代码_CPO_序号` 文件夹，内含 4 张照片和 1 个 `meta.json`。 |
| | **3.2 打包下载** | `[ ]` | 1. 点击 "Prepare Full Archive for Download"。<br>2. 点击 "Download Full Archive (ZIP)"。<br>3. 解压下载的 `.zip` 文件。 | 1. 成功下载包含时间戳的 `.zip` 文件。<br>2. 解压后，内容与本地生成的 `mission_test_records.csv` 和 `images/structured/` 文件夹一致。 |
| **Use Case 场景** | **4.1 UC01 仪表盘** | `[ ]` | 1. 选择 `UC01` Use Case，提交几条 AC 和 DC 的记录。<br>2. 切换到 "All" 或当天日期查看 "UC01 Daily Task Dashboard"。 | 1. "DC/AC Charging Progress" 计数正确增加。<br>2. "End Method Tracking Matrix" 中对应的单元格根据测试结果显示 `✅` 或 `❌`。 |
| | **4.2 UC02 流程** | `[ ]` | 1. 在 "Daily Target List" 中选择一个带 `🌡️🔋 vWM` 标志的站点。<br>2. Use Case 选择 `UC02`，完成一次提交流程。 | 1. 记录能够被成功提交并保存到 `mission_test_records.csv` 中。 |

---

## 功能優化與使用者體驗

- **1. 為拍照步驟添加示意圖**
  - **任務描述**: 在拍照/上傳的預覽區，為尚未拍攝的步驟顯示示意圖，引導使用者拍攝正確的照片。
  - **具體步驟**:
        1.  在 `images/` 資料夾下建立一個 `examples/` 子資料夾。
        2.  請設計師 (Banana) 產生四張示意圖 (例如 `example_pile_left.png`, `example_pile_right.png` 等) 並放入 `images/examples/`。
        3.  修改 `Mission_Logging.py` 中的 `PHOTO_SEQUENCE`，為每個項目增加 `example_image` 欄位。
        4.  更新照片預覽區的邏輯，當 `st.session_state.photo_data` 中沒有對應照片時，使用 `st.image()` 顯示 `example_image` 路徑的圖片。
