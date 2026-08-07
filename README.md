# POICollector · 高德 POI 数据采集工具

> 基于高德地图 Web 服务 API 的桌面端 POI 采集工具，PyQt6 开发，PyInstaller 单文件打包。
> AMap POI collection desktop tool built with PyQt6, shipped as a single-file PyInstaller executable.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 目录 / Contents

- [功能特性 | Features](#功能特性--features)
- [下载与安装 | Download & Install](#下载与安装--download--install)
- [使用前准备 | Prerequisites](#使用前准备--prerequisites)
- [快速上手 | Quick Start](#快速上手--quick-start)
- [四种采集模式 | Collection Modes](#四种采集模式--collection-modes)
- [导出格式 | Export Formats](#导出格式--export-formats)
- [一键导入 ArcGIS | ArcGIS Integration](#一键导入-arcgis--arcgis-integration)
- [开发 | Development](#开发--development)
- [许可证 | License](#许可证--license)

---

## 功能特性 | Features

- **四种采集模式 | Four collection modes**：周边搜索、关键字搜索、多边形搜索、POI ID 详情查询
  Nearby search · Keyword search · Polygon search · POI ID detail query
- **网格分片突破上限 | Grid splitting**：自动切分区域，突破高德同参数约 200 条返回上限
  Auto-splits the area to bypass AMap's ~200-result limit per query
- **多 Key 配额感知 | Multi-key rotation**：多个 Key 自动轮询分摊 QPS 限流，配额耗尽自动切换
  Multiple keys rotate automatically to spread QPS throttling; switches when one is exhausted
- **五格式导出 | Five export formats**：CSV / Excel / GeoJSON / JSON / Shapefile（均使用 WGS-84 坐标系）
  All exports use the WGS-84 (GPS) coordinate system
- **一键导入 ArcGIS | One-click ArcGIS**：直接启动 ArcGIS / ArcGIS Pro 加载数据，或写入已有工程文件
  Launch ArcGIS / ArcGIS Pro to load data, or write into an existing project
- **断点续爬 | Checkpoint resume**：采集中断后可从断点继续，无需重头再来
  Resume from the last checkpoint after interruption

---

## 下载与安装 | Download & Install

从 GitHub Releases 下载 `POICollector.exe`（约 60 MB，单文件、免安装）。

Download `POICollector.exe` (~60 MB, single file, no installation) from GitHub Releases.

- **无需 Python 环境**：双击即用，内置解释器与所有依赖
  No Python required — the executable bundles the interpreter and all dependencies
- **首次运行提示 | First run**：Windows SmartScreen 可能拦截，属正常现象
  Windows SmartScreen may block it on first run — this is expected:

  > 点击「更多信息」→「仍要运行」
  > Click **More info** → **Run anyway**

  （软件无代码签名证书，故会被拦截；选择信任即可）
  The app is not code-signed, so the warning is expected — just choose to run it.

---

## 使用前准备 | Prerequisites

- **操作系统 | OS**：Windows 10 / 11（64 位）
- **高德 Web 服务 Key | AMap Web Service Key**（免费申请，必填）：

  1. 打开 [高德开放平台控制台](https://console.amap.com/dev/key/app)
     Open the [AMap Open Platform console](https://console.amap.com/dev/key/app)
  2. 登录 / 注册（免费）
     Log in / sign up (free)
  3. 点击「+ 创建新 Key」，**服务平台务必选「Web 服务」**
     Click **+ Create Key**, and set **Service Platform = "Web Service"**
  4. 复制生成的 32 位 Key（形如 `82c5...e3b5`）

  > 提示：每人用自己的 Key，不要共用。建议申请 2~3 个 Key 配合"网格分片"使用。
  > Use your own key; do not share. We recommend 2–3 keys when using grid splitting.

---

## 快速上手 | Quick Start

**示例一：采集北京三里屯附近餐厅 | Example 1: restaurants near Sanlitun, Beijing**

1. 切换到「周边搜索」Tab → 城市填 `北京`
   Switch to **Nearby Search** → City: `北京`
2. 经度 `116.454`，纬度 `39.936`，半径 `1000`
   Longitude `116.454`, Latitude `39.936`, Radius `1000`
3. 关键词填 `餐饮` → 选好输出路径 → 点「开始采集」
   Keyword: `餐饮` → choose output → click **Start**

**示例二：采集南京市所有加油站 | Example 2: all gas stations in Nanjing**

1. 切换到「关键字搜索」Tab → 城市填 `南京`
   Switch to **Keyword Search** → City: `南京`
2. 关键词填 `加油站` → 点「开始采集」
   Keyword: `加油站` → click **Start**

---

## 四种采集模式 | Collection Modes

| 模式 Mode | 说明 Description | 必填 Required |
|---|---|---|
| 周边搜索 Nearby | 以坐标点为中心、指定半径内搜索 | 城市 / 经纬度 / 半径(m) |
| 关键字搜索 Keyword | 指定城市内按关键词搜索 | 城市 / 关键词 |
| 多边形搜索 Polygon | 自定义多边形区域内搜索，可导入 GeoJSON 提取边界 | 多边形顶点（每行一个 `经度,纬度`） |
| ID 查询 ID | 根据 POI ID 获取详情 | POI ID |

通用设置 | Common settings：

- **API Key**：支持多个（英文逗号分隔），自动轮询分摊限流
  Multiple keys (comma-separated) rotate automatically
- **POI 类型**：三级树（大类/中类/小类，900+ 项），勾大类即含全部子类
  Three-level type tree (900+ entries); checking a parent selects all children
- **每页条数**：1–25（高德单页上限 25）
  Page size: 1–25 (AMap limit)
- **突破 200 条上限（网格分片）**：自动切分区域逐块采集、合并去重
  Grid splitting: auto-splits and merges to exceed 200 results
- **导出格式**：可多选，按所选格式分别导出同名文件
  Export formats: multi-select, one file per format

---

## 导出格式 | Export Formats

| 格式 Format | 说明 Notes |
|---|---|
| CSV | Excel / WPS 可直接打开，UTF-8 编码 |
| Excel | `.xlsx`，含格式化表头 |
| GeoJSON | QGIS / ArcGIS 可打开，**坐标系 WGS-84** |
| JSON | 原始数组，便于二次开发 |
| Shapefile | ESRI 规范，自动生成 `.shp/.shx/.dbf/.prj` 四件套（标准形态，缺一不可），坐标系 WGS-84 |

所有导出均含：名称、类型、地址、经纬度(WGS-84)、电话、行政区、距离、评分、人均消费等字段。
All exports include: name, type, address, WGS-84 coordinates, phone, district, distance, rating, average cost, etc.

> 坐标系说明 | Coordinate system：高德返回 GCJ-02（火星坐标），软件自动转换为 WGS-84（GPS 标准）后导出。
> AMap returns GCJ-02; the tool converts to WGS-84 before export.

---

## 一键导入 ArcGIS | ArcGIS Integration

前提：本机已安装 ArcGIS Pro 或 ArcMap（软件不含 ArcGIS）。软件自动扫描 C/D/E/F/G 盘识别安装。
Requires ArcGIS Pro or ArcMap installed locally. The tool auto-detects installations on drives C/D/E/F/G.

- **按钮 A · 在 ArcGIS 中打开 | Open in ArcGIS**
  导出为 Shapefile 并直接启动本机 ArcGIS 加载数据（后台线程执行，不弹命令行）。
  Exports to Shapefile and launches local ArcGIS to load the data.
- **按钮 B · 导入到工程文件 | Import to Project**
  将本次 POI 作为新图层写入已有工程（`.aprx` / `.mxd`），下次打开即可见。
  Writes POI as a new layer into an existing project (`.aprx` / `.mxd`).

> 注意 | Note：按钮 B 需 ArcGIS 自带 Python(arcpy) 可外部调用；ArcGIS Pro 首次使用前请先启动并登录一次。
> Button B needs arcpy callable; launch and sign in to ArcGIS Pro once before first use.

---

## 开发 | Development

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
Icon source: `assets/logo.svg` (vector); `tools/build_icon.py` renders it into multi-size `logo.ico`.

---

## 许可证 | License

本项目基于 [MIT License](LICENSE) 开源。
Released under the [MIT License](LICENSE).

Copyright (c) 2026 joey6657-6657
