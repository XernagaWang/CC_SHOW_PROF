# **项目核心记忆：高德地图 POI 爬虫 (Amap POI Crawler)**

## **1. 项目目标**

* 创建一个独立的、可重用的 Python 脚本，用于从高德地图 Web 服务 API 爬取指定城市和指定类型的兴趣点 (POI)。
* 脚本应支持通过命令行参数传入城市名称、POI 分类代码以及高德 API Key。
* 核心逻辑是先将目标城市区域切分成精细的六边形网格，然后遍历每个网格，爬取其中的 POI 数据。

## **2. 核心数据与依赖**

* **输入数据**:
  * **城市边界数据**: 存储在 `road_plan_prod/District/` 目录下的 Shapefile (`.shp`) 文件。脚本需要根据城市中文名 (e.g., '贵阳市') 找到对应的边界文件。
  * **高德 API Key**: 一个有效的高德 Web 服务 API 密钥。
  * **POI 分类代码**: 高德地图定义的 POI 类型代码，例如充电站是 `011100`。

* **输出数据**:
  * 一个包含所有爬取到的 POI 信息的 GeoDataFrame。
  * 最终会保存为 CSV 或其他地理数据格式 (如 GeoJSON, Shapefile)。
  * 关键列应包括：`name`, `type`, `address`, `tel`, `location` (经纬度), `geometry` (Shapely Point 对象)。

* **核心 Python 库**:
  * `geopandas`: 用于处理地理数据（城市边界、六边形网格、POI 点）。
  * `pandas`: 用于数据处理和管理。
  * `requests`: 用于向高德 API 发送 HTTP 请求。
  * `shapely`: 用于地理对象的创建和操作 (Polygon, Point)。
  * `tqdm`: 用于在爬取过程中显示进度条。
  * `os`, `sys`: 用于路径管理。

## **3. 关键处理逻辑**

1. **生成六边形网格 (`generate_perfect_hex_grid`)**:
    * 根据城市边界的 `total_bounds` 和指定的六边形半径 (e.g., 1km) 生成覆盖整个城市的六边形网格。
    * 使用 `geopandas.clip` 裁剪网格，确保所有网格都在城市边界内部。

2. **爬取核心逻辑 (`crawl_city_stations_simplified`)**:
    * 遍历每一个六边形网格。
    * **简化几何**: 为了防止 URL 过长，需要简化六边形的边界坐标。使用 `polygon.simplify(tolerance)` 方法，`tolerance` 值需要仔细调整 (e.g., `0.0001`)。
    * **构造 API 请求**:
        * URL: `https://restapi.amap.com/v3/place/polygon`
        * 参数:
            * `key`: 高德 API Key。
            * `polygon`: 简化后的六边形坐标字符串。
            * `types`: POI 分类代码。
            * `offset`: 每页返回数量 (设为最大值 `25`)。
            * `page`: 当前页码。
    * **分页处理**: API 结果是分页的。需要检查返回的 `count` 字段，并循环请求直到获取所有页的数据。
    * **异常处理**: 对 API 请求进行 `try...except` 封装，处理网络错误或 API 限制。
    * **数据解析 (`parse_pois_to_dataframe`)**: 将 API 返回的 JSON 数据解析成 `pandas.DataFrame`，并将 `location` 字符串转换为 `shapely.geometry.Point` 对象，最终形成 `GeoDataFrame`。

3. **主执行函数 (`run_crawling_for_city_final`)**:
    * 接收城市名称、POI 类型等作为参数。
    * 调用上述函数，串联起整个流程：加载城市边界 -> 生成网格 -> 遍历网格爬取 -> 合并结果 -> 保存文件。

## **4. 待办与优化**

* **封装为独立项目**: 将此逻辑从 Notebook 中剥离，创建一个独立的 Python 项目。
* **命令行接口**: 使用 `argparse` 库为脚本添加入口，使其可以通过命令行调用。
* **数据服务化**: 考虑将城市边界等基础地理数据存入 PostGIS 或 MySQL 数据库，通过统一的数据服务调用，而不是每次都读取文件。
