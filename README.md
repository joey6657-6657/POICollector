<p align="center">
  <img src="assets/logo.png" width="120" alt="POICollector Logo">
</p>

<h1 align="center">POICollector · 高德 POI 数据采集工具</h1>

<p align="center">
  <b>基于高德地图 Web 服务 API 的桌面端 POI 采集工具</b><br>
  <b>AMap POI Collection Desktop Tool — PyQt6 + PyInstaller Single-File EXE</b>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.13+-green.svg" alt="Python"></a>
  <a href="https://www.riverbankcomputing.com/software/pyqt/"><img src="https://img.shields.io/badge/PyQt6-Desktop-blue.svg" alt="PyQt6"></a>
</p>

---

<details open>
<summary><b>🇨🇳 中文</b></summary>

## ✨ 功能特性

- **四种采集模式**：周边搜索、关键字搜索、多边形搜索、POI ID 详情查询
- **网格分片突破上限**：自动切分区域，突破高德同参数约 200 条返回上限
- **多 Key 配额感知**：多个 Key 自动轮询分摊 QPS 限流，配额耗尽自动切换
- **五格式导出**：CSV / Excel / GeoJSON / JSON / Shapefile（均使用 WGS-84 坐标系）
- **一键导入 ArcGIS**：直接启动 ArcGIS / ArcGIS Pro 加载数据，或写入已有工程文件
- **断点续爬**：采集中断后可从断点继续，无需重头再来

## 📥 下载与安装

从 GitHub Releases 下载 `POICollector.exe`（约 85 MB，单文件、免安装）。

- **无需 Python 环境**：双击即用，内置解释器与所有依赖
- **首次运行提示**：Windows SmartScreen 可能拦截，属正常现象：

> 点击「更多信息」→「仍要运行」

（软件无代码签名证书，故会被拦截；选择信任即可）

## 🔑 使用前准备

| 前置条件 | 说明 |
|---|---|
| 操作系统 | Windows 10 / 11（64 位） |
| 高德 Web 服务 Key | 免费申请，必填 |

**申请 Key 步骤：**

1. 打开 [高德开放平台控制台](https://console.amap.com/dev/key/app)
2. 登录 / 注册（免费）
3. 点击「+ 创建新 Key」，**服务平台务必选「Web 服务」**
4. 复制生成的 32 位 Key（形如 `82c5...e3b5`）

> 💡 提示：每人用自己的 Key，不要共用。建议申请 2~3 个 Key 配合"网格分片"使用。

## 🚀 快速上手

### 示例一：采集北京三里屯附近餐厅

1. 切换到「周边搜索」Tab → 城市填 `北京`
2. 经度 `116.454`，纬度 `39.936`，半径 `1000`
3. 关键词填 `餐饮` → 选好输出路径 → 点「开始采集」

### 示例二：采集南京市所有加油站

1. 切换到「关键字搜索」Tab → 城市填 `南京`
2. 关键词填 `加油站` → 点「开始采集」

## 📋 四种采集模式

| 模式 | 说明 | 必填参数 |
|---|---|---|
| 周边搜索 | 以坐标点为中心、指定半径内搜索 | 城市 / 经纬度 / 半径(m) |
| 关键字搜索 | 指定城市内按关键词搜索 | 城市 / 关键词 |
| 多边形搜索 | 自定义多边形区域内搜索，支持 AOI 导入 | 多边形顶点（每行一个 `经度,纬度`） |
| ID 查询 | 根据 POI ID 获取详情 | POI ID |

**通用设置：**

- **API Key**：支持多个（英文逗号分隔），自动轮询分摊限流
- **POI 类型**：三级树（大类/中类/小类，915 项），勾大类即含全部子类
- **每页条数**：1–500（高德单页上限 25，但软件支持设置更大值配合分页）
- **突破 200 条上限（网格分片）**：自动切分区域逐块采集、合并去重
- **导出格式**：可多选，按所选格式分别导出同名文件

## 📤 导出格式

| 格式 | 说明 |
|---|---|
| CSV | Excel / WPS 可直接打开，UTF-8 编码 |
| Excel | `.xlsx`，含格式化表头 |
| GeoJSON | QGIS / ArcGIS 可打开，**坐标系 WGS-84** |
| JSON | 原始数组，便于二次开发 |
| Shapefile | ESRI 规范，自动生成 `.shp/.shx/.dbf/.prj` 四件套，坐标系 WGS-84 |

所有导出均含：名称、类型、地址、经纬度(WGS-84)、电话、行政区、距离、评分、人均消费等字段。

> ⚠️ **坐标系说明**：高德返回 GCJ-02（火星坐标），软件自动转换为 WGS-84（GPS 标准）后导出。

## 🗺️ 一键导入 ArcGIS

前提：本机已安装 ArcGIS Pro 或 ArcMap（软件不含 ArcGIS）。软件自动扫描 C/D/E/F/G 盘识别安装。

| 按钮 | 功能 |
|---|---|
| **按钮 A · 在 ArcGIS 中打开** | 导出为 Shapefile 并直接启动本机 ArcGIS 加载数据 |
| **按钮 B · 导入到工程文件** | 将本次 POI 作为新图层写入已有工程（`.aprx` / `.mxd`） |

> 注意：按钮 B 需 ArcGIS 自带 Python(arcpy) 可外部调用；ArcGIS Pro 首次使用前请先启动并登录一次。

## 🛠️ 开发

```bash
# 1. 创建虚拟环境（需 Python 3.13+）
python -m venv venv
venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行（开发模式）
python run.py

# 4. 打包为单文件 exe（输出 dist/POICollector.exe）
pyinstaller POICollector.spec --noconfirm
```

图标资源位于 `assets/logo.svg`（真矢量源），由 `tools/build_icon.py` 渲染为多尺寸 `logo.ico`。

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

Copyright (c) 2026 joey6657-6657

</details>

<details>
<summary><b>🇬🇧 English</b></summary>

## Features

- **Four collection modes**: Nearby search, Keyword search, Polygon search, POI ID detail query
- **Grid splitting**: Auto-splits the area to bypass AMap's ~200-result limit per query
- **Multi-key rotation**: Multiple keys rotate automatically to spread QPS throttling; switches when one is exhausted
- **Five export formats**: CSV / Excel / GeoJSON / JSON / Shapefile (all in WGS-84 coordinate system)
- **One-click ArcGIS integration**: Launch ArcGIS / ArcGIS Pro to load data, or write into an existing project file
- **Checkpoint resume**: Resume from the last checkpoint after interruption

## Download & Install

Download `POICollector.exe` (~85 MB, single file, no installation) from GitHub Releases.

- **No Python required** — the executable bundles the interpreter and all dependencies
- **First-run warning**: Windows SmartScreen may block it on first run — this is expected:

> Click **More info** → **Run anyway**

(The app is not code-signed, so the warning is expected — just choose to trust it.)

## Prerequisites

| Requirement | Details |
|---|---|
| OS | Windows 10 / 11 (64-bit) |
| AMap Web Service Key | Free registration, required |

**How to get a Key:**

1. Open the [AMap Open Platform console](https://console.amap.com/dev/key/app)
2. Log in / sign up (free)
3. Click **+ Create Key**, set **Service Platform = "Web Service"**
4. Copy the generated 32-character key (e.g., `82c5...e3b5`)

> **Tip**: Use your own key; do not share. We recommend 2–3 keys when using grid splitting.

## Quick Start

### Example 1: Restaurants near Sanlitun, Beijing

1. Switch to **Nearby Search** tab → City: `Beijing`
2. Longitude `116.454`, Latitude `39.936`, Radius `1000`
3. Keyword: `Restaurant` → choose output path → click **Start**

### Example 2: All gas stations in Nanjing

1. Switch to **Keyword Search** tab → City: `Nanjing`
2. Keyword: `Gas Station` → click **Start**

## Collection Modes

| Mode | Description | Required Fields |
|---|---|---|
| Nearby Search | Search within a radius of a coordinate point | City / Longitude-Latitude / Radius (m) |
| Keyword Search | Search by keyword within a city | City / Keyword |
| Polygon Search | Search within a custom polygon area; supports AOI import | Polygon vertices (one `lng,lat` per line) |
| ID Query | Get details by POI ID | POI ID |

**Common settings:**

- **API Key**: Supports multiple keys (comma-separated), auto-rotates for load balancing
- **POI Type**: Three-level tree (Category / Subcategory / Type, 915 entries); checking a parent selects all children
- **Page size**: 1–500 (AMap per-page limit is 25, but higher values work with pagination)
- **Grid splitting**: Auto-splits and merges results to exceed the 200-result limit
- **Export formats**: Multi-select; one output file per selected format

## Export Formats

| Format | Notes |
|---|---|
| CSV | Open directly in Excel / WPS, UTF-8 encoded |
| Excel | `.xlsx` with formatted headers |
| GeoJSON | Open in QGIS / ArcGIS, **WGS-84 coordinate system** |
| JSON | Raw array for further processing |
| Shapefile | ESRI standard, auto-generates `.shp/.shx/.dbf/.prj` bundle, WGS-84 |

All exports include: name, type, address, WGS-84 coordinates, phone, district, distance, rating, average cost, etc.

> **Note on coordinates**: AMap returns GCJ-02 (Mars coordinates); the tool converts to WGS-84 (GPS standard) before export.

## One-click ArcGIS Integration

Requires ArcGIS Pro or ArcMap installed locally (not bundled). The tool auto-detects installations on drives C/D/E/F/G.

| Button | Function |
|---|---|
| **Button A · Open in ArcGIS** | Exports to Shapefile and launches local ArcGIS to load data |
| **Button B · Import to Project** | Writes POI as a new layer into an existing project (`.aprx` / `.mxd`) |

> Note: Button B requires arcpy callable from ArcGIS's Python; launch and sign in to ArcGIS Pro once before first use.

## Development

```bash
# 1. Create virtual environment (Python 3.13+ required)
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run (development mode)
python run.py

# 4. Package as single-file exe (output: dist/POICollector.exe)
pyinstaller POICollector.spec --noconfirm
```

Icon source: `assets/logo.svg` (vector); rendered into multi-size `logo.ico` by `tools/build_icon.py`.

## License

Released under the [MIT License](LICENSE).

Copyright (c) 2026 joey6657-6657

</details>
