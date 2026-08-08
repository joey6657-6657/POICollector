# 第三方致谢 / Third-Party Acknowledgements

本项目在设计与实现上参考/借鉴了以下开源项目与数据，谨致谢意：

## 致谢列表

| 项目 | 许可证 | 借鉴内容 | 链接 |
|---|---|---|---|
| **GaoDe-poi-crawler** | MIT | 网格/四叉树递归拆分突破高德 API 返回上限、多 Key 轮询的思路参考 | [GitHub](https://github.com/zdbpython/GaoDe-poi-crawler) |
| **POIKit**（AMapPoi） | 未明示（Java） | "网格四分/网格剖分"概念参考 | [GitHub](https://github.com/Davydxm/AMapPoi) |
| **wandergis/coordTransform_py** | MIT | GCJ-02/WGS84/BD09 坐标系转换算法实现参考 | [GitHub](https://github.com/wandergis/coordTransform_py) |
| **高德开放平台（AMap）** | 高德服务条款 | POI 分类数据（915 项三级分类）与 Web 服务 API 来源 | [官网](https://lbs.amap.com/) |

## 说明

- **GaoDe-poi-crawler**：`core/splitter.py` 的网格四分片算法思路来源于此项目的四叉树实现。本项目的代码为独立重写，未直接复制其源码。
- **wandergis/coordTransform_py**：`core/coord_transform.py` 的坐标系转换算法参考了该项目的标准实现（GCJ-02 ↔ WGS-84 ↔ BD09），这是中文 GIS 社区最广泛使用的坐标转换方案。
- **高德开放平台**：`data/poi_types.json` 中的 915 项 POI 三级分类数据源自高德官方 POI 分类编码规范；工具的全部功能基于高德 Web 服务 API。

## 许可声明

本项目自身代码以 **MIT License** 发布；上述项目各自保留其原有许可证与版权。
