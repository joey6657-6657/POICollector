<p align="center">
  <img src="assets/logo.png" width="120" alt="POICollector Logo">
</p>

<h1 align="center">POICollector · AMap POI Collection Tool</h1>

<p align="center">
  <b>A desktop tool for collecting, organizing AMap POI data and bringing the results directly into ArcGIS.</b>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.13+-green.svg" alt="Python"></a>
  <a href="https://www.qt.io/qt-for-python"><img src="https://img.shields.io/badge/PySide6-Desktop-blue.svg" alt="PySide6"></a>
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/🇨🇳_中文-主文档-E53935?style=for-the-badge" alt="Chinese primary documentation"></a>
  <a href="README_EN.md"><img src="https://img.shields.io/badge/🇬🇧_English-README-1677C8?style=for-the-badge" alt="English README"></a>
</p>

<p align="center">
  <a href="#features">Features</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="#arcgis">ArcGIS Workflow</a> ·
  <a href="#usage">Usage Guide</a> ·
  <a href="#project-structure">Project Structure</a> ·
  <a href="#development">Development</a> ·
  <a href="#acknowledgements">Acknowledgements</a>
</p>

---

<a id="features"></a>

## ✨ Features

- **Two direct ArcGIS workflows (core highlight):** after a collection finishes, export a Shapefile and open it in ArcGIS / ArcGIS Pro, or write the current result directly into an existing <code>.aprx</code> / <code>.mxd</code> project.
- **Four collection modes:** Nearby Search, Keyword Search, Polygon Search, and POI ID detail lookup.
- **Grid splitting beyond result limits:** Nearby / Polygon / Keyword searches can split an area automatically to work around AMap’s approximately 200-result limit for a single query. Keyword splitting uses the city administrative boundary.
- **Quota-aware multi-key rotation:** multiple keys rotate automatically to share QPS limits; exhausted keys are skipped.
- **Five export formats:** CSV / Excel / GeoJSON / JSON / Shapefile; spatial formats use WGS-84 coordinates.
- **Checkpoint resume and deduplication:** resume an interrupted run with the same parameters and merge duplicate results automatically.

<a id="download"></a>

## 📥 Download and installation

- **Download v1.0.1:** open the [POICollector v1.0.1 Release](https://github.com/joey6657-6657/POICollector/releases/tag/v1.0.1) and download `POICollector.exe` from Assets.
- **No Python environment required:** the published EXE packages the interpreter and dependencies.
- **SHA-256:** `EF56E055E3033E3420E68B51086B0E31016DE72867B47D94ECCA8DB5583B3FB5`
- **First-run notice:** the app is not code-signed, so Windows SmartScreen may show a warning. Download only from this repository’s Release and verify the SHA-256 checksum.

<a id="faq"></a>

## ❓ FAQ

**Q: The progress bar has not moved for a long time — is it frozen?**

When searching a large area with a whole POI category selected, the tool splits the region into hundreds of small grid cells and collects them one by one, so the total number of requests is large. Personal developer keys are limited to 3 requests/second, so the run may take several minutes to tens of minutes — this is normal. Since v1.0.1 the run log periodically reports "N grid cells probed"; as long as that counter grows, collection is still running. Using 2–3 keys (comma-separated) is recommended so the tool can rotate them to spread the rate limit.

**Q: What does the warning "cell too dense, only the first 200 results can be collected" mean?**

The POI count in that grid cell exceeds the per-request API limit and the maximum split depth has been reached, so it cannot be subdivided further — the result for that cell is **incomplete**. Try a smaller radius / area, or use a more specific keyword or a finer POI sub-category.

**Q: Can I collect by administrative district? What goes in the city field?**

The "city" field accepts a city name (e.g. `苏州`), a citycode, or an adcode (administrative-division code, e.g. `320500`). After filling it in, enabling "limit to city" is recommended for better accuracy.

**Q: Windows SmartScreen blocked the first launch.**

The app is not code-signed, so the warning on first launch is expected — click "More info → Run anyway". Always download only from this repository's Release and verify the SHA-256 checksum.

<a id="scope"></a>

## Intended use and data handling

This project is for **personal learning and research** only. Do not use it to bulk-collect, retain long-term, resell, or redistribute data obtained through AMap services. You are responsible for complying with the terms, quotas, and applicable laws for the services you use.

<a id="preparation"></a>

## 🔑 Before you start

| Requirement | Details |
|---|---|
| Operating system | Windows 10 / 11 (64-bit) |
| AMap Web Service Key | Free registration; required |
| ArcGIS (optional) | ArcGIS Pro or ArcMap is required only for the direct ArcGIS workflows |

**How to obtain a Key:**

1. Open the [AMap Open Platform console](https://console.amap.com/dev/key/app).
2. Sign in or create a free account.
3. Click **+ Create Key** and select **Web Service** as the service platform.
4. Copy the generated Key. Use your own Key; never commit, share, or place it in screenshots.

<p align="center">
  <img src="screenshots/高德开放平台.png" width="46%" alt="AMap Open Platform home">
  <img src="screenshots/高德开放平台注册.png" width="46%" alt="AMap Open Platform registration">
</p>
<p align="center">
  <img src="screenshots/高德开放平台登录.png" width="46%" alt="AMap Open Platform sign in">
  <img src="screenshots/高德开放平台创建Key.png" width="46%" alt="Create an AMap Web Service Key">
</p>

> **Tip:** use your own Key. For larger areas, 2–3 Keys can be used together with grid splitting.

<a id="quick-start"></a>

## 🚀 Quick start

### Example 1: restaurants near Jiangfeng Campus, Suzhou University of Science and Technology

1. Search for “苏州科技大学江枫校区” in the [AMap Coordinate Picker](https://lbs.amap.com/tools/picker), then click the map to obtain GCJ-02 coordinates (approximately <code>120.565,31.300</code>).

<p align="center">
  <img src="screenshots/经纬度查询.png" width="720" alt="AMap Coordinate Picker example">
</p>

2. Switch to **Nearby Search**: set City to <code>Suzhou</code>, Longitude to <code>120.565</code>, Latitude to <code>31.300</code>, and Radius to <code>2000</code>.
3. Enter <code>餐饮</code> (dining) as the keyword, or select the “餐饮服务” POI category. Choose an output location, then click **Start Collection**.

<p align="center">
  <img src="screenshots/示例一：采集苏州科技大学江枫校区附近的餐饮.png" width="900" alt="Nearby Search restaurant collection example">
</p>

### Example 2: metro stations in Suzhou

1. Switch to **Keyword Search**: set City to <code>Suzhou</code> and the keyword to <code>地铁站</code> (metro station).
2. Leave **Automatic Grid Splitting** at its default automatic setting and click **Start Collection**.
3. If the result count reaches the threshold, the tool reads the Suzhou administrative boundary, collects grid by grid, then merges and deduplicates results to avoid the roughly 200-result cap of a single request.

<p align="center">
  <img src="screenshots/示例二：采集苏州市地铁站.png" width="900" alt="Keyword Search automatic grid-splitting example">
</p>

<a id="arcgis"></a>

## 🗺️ One-click ArcGIS workflow (core highlight)

Once collection is complete, two ArcGIS buttons appear in the result area. This is the workflow that sets POICollector apart from export-only tools: move directly from collected POIs into GIS mapping or an existing project without manually locating exported files.

<p align="center">
  <img src="screenshots/一键导入ArcGIS 按钮A、B.png" width="1000" alt="ArcGIS buttons A and B after collection">
</p>

| Button | Best for | Result |
|---|---|---|
| **Button A · Open in ArcGIS** | Viewing this collection immediately | Exports a Shapefile, starts the detected local ArcGIS / ArcGIS Pro, and shows the data path and loading instructions |
| **Button B · Import to Project** | Adding the result to an existing project | Select an <code>.aprx</code> or <code>.mxd</code>; the current POIs are added as a new layer, then you can open the project immediately |

### Button A: Open in ArcGIS

Button A exports the current result as a Shapefile and starts the detected ArcGIS / ArcMap installation. The dialog and run log show the exported path and loading instructions, making it clear that the data has been handed off to ArcGIS.

<p align="center">
  <img src="screenshots/按钮A：在空白地图的ArcGIS中打开.png" width="1000" alt="Button A starts ArcGIS and shows the Shapefile path">
</p>

### Button B: Import to Project

Button B first lets you select an existing ArcGIS Pro project (<code>.aprx</code>) or ArcMap document (<code>.mxd</code>). After the POI layer is added to the project, the program asks whether to open it immediately.

<p align="center">
  <img src="screenshots/按钮B：导入到工程文件.png" width="48%" alt="Button B selects an ArcGIS project file">
  <img src="screenshots/按钮B：导入到工程文件选择是否打开.png" width="48%" alt="Button B asks whether to open the imported project">
</p>

> **Requirements:** ArcGIS Pro or ArcMap must be installed locally. Button B also requires the ArcGIS-supplied Python environment (<code>arcpy</code>) to be callable. Before first use of ArcGIS Pro, start it once and sign in. ArcGIS itself is not bundled with this project.

<a id="usage"></a>

## 📋 Usage guide: collection and export

### Four collection modes

| Mode | Description | Required fields |
|---|---|---|
| Nearby Search | Search around a coordinate within a specified radius | Longitude / Latitude / Radius (m); City is optional |
| Keyword Search | Search by keyword; City narrows the area | Keyword; City is required when grid splitting is enabled |
| Polygon Search | Search within a custom polygon; supports AOI import | Polygon vertices, one <code>longitude,latitude</code> pair per line |
| POI ID Query | Retrieve details for a POI ID | POI ID |

**Common settings:**

- **API Key:** multiple Keys are supported (comma-separated) and rotate automatically to share rate limits.
- **POI type:** a three-level category tree (category / subcategory / type, 915 entries); selecting a parent includes its children.
- **Page size:** 1–25. The tool paginates automatically; a single parameter combination can return up to approximately 200 records.
- **Automatic grid splitting:** off / automatic / manual. Available for Nearby / Polygon / Keyword searches; Keyword splitting requires a City.
- **Export formats:** choose more than one format; the tool writes one same-named file per selected format.

### Export formats

| Format | Notes |
|---|---|
| CSV | Opens directly in Excel / WPS, UTF-8 encoded |
| Excel | <code>.xlsx</code> with formatted headers |
| GeoJSON | Opens in QGIS / ArcGIS; **WGS-84** coordinates |
| JSON | Raw array for further processing |
| Shapefile | A <code>.shp/.shx/.dbf/.prj</code> bundle; **WGS-84** coordinates |

All exports include fields such as name, type, address, WGS-84 coordinates, phone number, district, distance, rating, and average spending.

> **Coordinate note:** AMap returns GCJ-02 (Mars coordinates). The program converts spatial data to WGS-84 before exporting.

<a id="project-structure"></a>

## 📁 Project structure

~~~text
POICollector/
├── run.py                      # Application entry point
├── POICollector.spec           # PyInstaller packaging configuration
├── README.md                   # Chinese primary documentation
├── README_EN.md                # English README
├── requirements.txt            # Runtime Python dependencies
├── requirements-dev.txt        # Development/test dependencies
├── requirements-lock.txt       # Verified v1.0.0 environment
├── LICENSE / LICENSES/         # Project and third-party license materials
├── .github/                    # CI, issue templates, and community policies
├── docs/                       # Change log and Release documentation
├── screenshots/                # README images and operating demos
├── assets/                     # Icon resources
├── poi_collector/
│   ├── core/                   # API, pagination, splitting, checkpoint, ArcGIS bridge
│   ├── data/                   # Deduplication, export, and POI category data
│   └── gui/                    # PySide6 GUI and background collection thread
├── tools/                      # Icon and optional release-archive scripts
└── tests/                      # Offline core-logic tests
~~~

<a id="development"></a>

## 🛠️ Development

~~~bash
# 1. Create a virtual environment (Python 3.13+ required)
python -m venv venv
venv\Scripts\activate

# 2. Install runtime dependencies
pip install -r requirements.txt

# 3. Install development dependencies and run offline tests
pip install -r requirements-dev.txt
python -m pytest -q

# 4. Run in development mode
python run.py

# 5. Package a single-file EXE (output: dist/POICollector.exe)
pyinstaller POICollector.spec --noconfirm

# 6. Optional: create a release archive with license materials
powershell -ExecutionPolicy Bypass -File tools\package_release.ps1 -Version 1.0.0
~~~

## 📄 License

The code written for this project is released under the [MIT License](LICENSE). The [Acknowledgements and third-party notices](#acknowledgements) below distinguish adapted code, idea-only references, data sources, and runtime dependencies. When distributing the EXE, also include the license materials in [LICENSES/](LICENSES/).

Copyright (c) 2026 joey6657-6657

<a id="acknowledgements"></a>

## 🙏 Acknowledgements and third-party notices

Thanks to the following open-source projects, data services, and development collaboration tools. This section is also the project’s third-party notice: it distinguishes adapted code from idea-only references so that a conceptual reference is not misrepresented as copied code.

### Adapted code

#### [wandergis/coordTransform_py](https://github.com/wandergis/coordTransform_py)

- **Use in this project:** the GCJ-02, WGS-84, and BD-09 conversion formulas and implementation structure in <code>poi_collector/core/coord_transform.py</code>.

- **License:** MIT License; original copyright notice: Copyright (c) 2015 WangMing.
- **Included license text:** [LICENSES/MIT-wandergis-coordTransform_py.txt](LICENSES/MIT-wandergis-coordTransform_py.txt).

### Algorithm or product ideas only

#### [zdbpython/GaoDe-poi-crawler](https://github.com/zdbpython/GaoDe-poi-crawler)

- **Idea referenced:** recursively dividing a search area with a grid / quadtree and querying smaller areas to avoid the per-query result cap.
- **Corresponding module:** <code>poi_collector/core/splitter.py</code>.
- **Boundary:** geometry, grid splitting, collection orchestration, and deduplication were independently implemented in this project; no code from that repository was copied or adapted.

#### [Davydxm/AMapPoi](https://github.com/Davydxm/AMapPoi) (POIKit)

- **Idea referenced:** the product and algorithm concept of grid subdivision.
- **Boundary:** no Java code was copied or adapted, and none is included in this project; therefore it is not a source of this project’s code license.

### Data sources and runtime dependencies

- **AMap Open Platform:** <code>poi_collector/data/poi_types.json</code> comes from AMap POI category materials, and the application requests data through its Web Service API. Neither the data nor API content is relicensed under this project’s MIT License.
- **PySide6 / Qt:** the desktop interface uses PySide6. A Windows EXE distribution should include the LGPL / GPL texts and related notices in <code>LICENSES/</code>; see [LICENSES/README.md](LICENSES/README.md).
- **Other Python dependencies:** [requirements-lock.txt](requirements-lock.txt) lists versions; each dependency retains its own copyright and license.

### Development collaboration tools

The following models were used during development for requirements discussion, document review, test ideas, and code discussion: **ChatGPT 5.6 Terra, Qwen3.8 Max, HY3, GLM 5.2, and DeepSeek V4 Flash**. The project maintainer reviewed and made the final decisions on all code, documentation, and release content.

### Contributors

- [@joey6657-6657](https://github.com/joey6657-6657) — project creation, feature development, and maintenance
- Contact: [2842853418@qq.com](mailto:2842853418@qq.com)
