# POICollector v1.0.0

首个公开版本，提供基于高德 Web 服务 API 的 Windows 桌面端 POI 查询、整理与导出工具。

## 包含内容

- 四种查询模式：周边、关键字、多边形、POI ID。
- CSV、Excel、GeoJSON、JSON、Shapefile 导出。
- 断点续采、结果去重、ArcGIS 导入和网格分片。
- 单文件 Windows EXE，无需预先安装 Python。

## 使用前请阅读

- 需要自行申请并使用自己的高德 Web 服务 API Key；本项目不提供、收集或保存 Key。
- 仅供个人学习、科研和内部项目使用；请遵守相关服务条款、接口配额及适用法律法规。
- EXE 没有代码签名，首次运行可能被 Windows SmartScreen 提示。请只从本仓库 Release 下载，并自行核对下方 SHA-256。
- 建议下载包含 `LICENSE`、`THIRD-PARTY.md` 和 `LICENSES/` 的发行 ZIP；其中的 EXE 为 Windows 单文件程序。

## 文件校验

`POICollector.exe`

SHA-256：`0E46E721CFF52C3C2A8BA218D620516DD06D935FBBD533B3E36C405D572F1AC5`

## 已知限制

- 仅支持 Windows 10 / 11（64 位）。
- ArcGIS 功能需要本机已安装 ArcGIS Pro 或 ArcMap。
- POI 查询和结果内容受高德服务、账户权限、配额与网络状态影响。
