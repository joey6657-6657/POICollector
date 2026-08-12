# 第三方声明与参考边界

本文件区分“改编的代码”和“仅参考的思路”，以免把概念借鉴误写成代码复制，或遗漏真正需要保留的版权声明。

## 已改编的代码（随源码和 EXE 发行时必须保留）

### wandergis/coordTransform_py

- **来源**：[wandergis/coordTransform_py](https://github.com/wandergis/coordTransform_py)
- **使用范围**：`poi_collector/core/coord_transform.py` 中 GCJ-02、WGS-84、BD-09 的转换公式与实现结构。
- **性质**：代码改编，不只是思路借鉴。
- **许可证**：MIT License。
- **原始版权声明**：Copyright (c) 2015 WangMing。
- **随附文本**：[`LICENSES/MIT-wandergis-coordTransform_py.txt`](LICENSES/MIT-wandergis-coordTransform_py.txt)。

## 仅参考的算法或产品思路（未复制或改编其代码）

### GaoDe-poi-crawler

- **来源**：[zdbpython/GaoDe-poi-crawler](https://github.com/zdbpython/GaoDe-poi-crawler)（MIT）。
- **参考内容**：用网格/四叉树递归拆分搜索区域、以小区域查询规避单次返回上限的思路。
- **本项目对应文件**：`poi_collector/core/splitter.py`。
- **边界**：本项目自行实现了几何计算、网格拆分、采集编排与去重流程；未复制或改编该仓库代码。

### POIKit（AMapPoi）

- **历史记录中的来源地址**：[Davydxm/AMapPoi](https://github.com/Davydxm/AMapPoi)。
- **参考内容**：“网格四分/网格剖分”这一产品和算法概念。
- **边界**：未复制或改编其 Java 代码，也未把其代码纳入本项目；因此本项目不以该仓库作为代码许可证来源。

## 数据与运行时依赖

- **高德开放平台（AMap）**：`poi_collector/data/poi_types.json` 来自高德 POI 分类资料，程序通过其 Web 服务 API 请求数据。该数据和 API 内容不因本项目使用 MIT License 而被重新授权。
- **PySide6 / Qt**：桌面界面运行时使用 PySide6。发行 Windows EXE 时应一并提供 `LICENSES/` 中的 LGPL/GPL 文本及相关告知材料；见 [`LICENSES/README.md`](LICENSES/README.md)。
- **其他 Python 依赖**：版本清单见 [`requirements-lock.txt`](requirements-lock.txt)。各依赖保留各自的版权和许可证。

## 项目自身许可证

除上述第三方材料外，本项目自行编写的代码以根目录 [`LICENSE`](LICENSE) 中的 MIT License 发布。
