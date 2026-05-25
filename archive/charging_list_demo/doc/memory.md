# **项目核心记忆：充电站 Facebook (Charging List App)**

## **1. 项目最终目标**

* 创建一个名为 “充电站的 Facebook” 的 Web 应用。
* 核心功能是以动态、可视化的方式，展示我们去过的每一个充电站的详细信息、照片和相关记录。
* 应用应该能够读取一个标准化的数据文件，并自动生成每个充电站的“主页”。

## **2. 核心数据与“交接文件”**

* **数据源头** : 所有的数据处理逻辑都源自 `logbook_deployment` 项目中的 [app.ipynb](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html)。
* **最终交接文件** : 新项目将依赖于一个最终生成的 `logbook_final.csv` 文件。这个文件是在 [app.ipynb](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html) 中处理完所有数据后导出的，它必须包含以下关键列：
* `station_unique_id`:  **最重要的唯一标识符** 。
* `Date` / `datetime`: 充电日期和时间。
* `City`: 城市中文名 (e.g., '成都')。
* `city_code`: 城市两位简码 (e.g., 'CD')。
* `CPO Name`: CPO 中文名 (e.g., '小桔充电')。
* `cpo_name_pinyin`: CPO 拼音，下划线连接 (e.g., 'xiao_ju_chong_dian')。
* `Station`: 充电站的具体名称。
* `longitude`, `latitude`: 从高德 API 获取的经纬度。
* 以及 `Logbook_2026.xlsx` 中的其他所有原始数据列。

## **3. 关键处理逻辑与规则 (ID 生成)**

`station_unique_id` 的生成逻辑是整个项目的基石，必须严格遵守：

* **格式** : `城市简码_CPO拼音_序号` (e.g., `CD_xiao_ju_chong_dian_001`)
* **城市简码 (`city_code`)** :
* 基于一个固定的映射关系，例如：`{'成都': 'CD', '重庆': 'CQ', '贵阳': 'GY'}`。
* **CPO 拼音 (`cpo_name_pinyin`)** :
* 将 `CPO Name` 列的中文名转换为小写拼音。
* 使用**下划线 `_`** 连接每个字，而不是空格。
* **序号 (`station_seq_code`)** :
* 这是最复杂的规则：序号是 **在同一个城市、同一个 CPO 内部** ，根据充电站**首次出现的时间顺序**生成的。
* **实现步骤** :
  1. 对所有记录按 `Date` (或 `datetime`) 列进行升序排序。
  2. 去除重复的充电站（基于 `City` 和 `Station` 列），只保留每个站第一次出现的记录。
  3. 对这些不重复的站，按 `City` 和 `cpo_name_pinyin` 进行分组 (`groupby`)。
  4. 在每个组内，使用累积计数 (`cumcount()`) 生成一个从 0 开始的排名，然后加 1。
  5. 将这个数字格式化为**三位、前面补零**的字符串 (e.g., `1` -> `001`)。

## **4. 其他重要信息**

* **地理编码** :
* 使用**高德 (Amap) API** 获取经纬度。
* API Key: `e04966e153cf5a14405299a75cadafdd`
* 为了效率和节省 API 调用，我们为每个城市都创建了缓存文件 (e.g., [geocoded_stations_成都.csv](vscode-file://vscode-app/Applications/Visual%20Studio%20Code.app/Contents/Resources/app/out/vs/code/electron-browser/workbench/workbench.html))。
* **照片与日志文件** :
* 您会将照片和原始日志文件移植到新项目中，我们需要规划好新项目中的目录结构，以便 Web 应用可以根据 `station_unique_id` 找到并展示对应的照片。
