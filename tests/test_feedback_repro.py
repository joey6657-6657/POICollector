"""复现用户反馈：around + POI类型勾选 + city=行政区划编码 的分片请求参数审计。

模拟小红书用户 nonono 的配置：
  周边搜索 + 半径 10000m + 勾选"体育休闲服务"大类(types=080000)
  + 城市框填了行政区划编码(city=350100) + citylimit + 自动分片

检查点：
  1. 分片子请求(polygon 接口)携带了哪些参数 —— 是否残留 city/citylimit/sortrule
  2. 探测阶段(_probe)是否有进度回调 —— 是否存在"长时间无反馈像卡死"
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from poi_collector.core.splitter import SplitCollector


class FakeClient:
    """记录每次请求参数；count 随探测深度递减，模拟"数据量大需多次四分"。"""

    def __init__(self):
        self.calls = []          # (endpoint, params)
        self.probe_count = 0

    def _call(self, endpoint, params):
        self.calls.append((endpoint, dict(params)))
        # 根区域探测: 第一次 count 很大(5000)；后续按请求的多边形面积递减
        if params.get("offset") == 1 and params.get("page") == 1:
            self.probe_count += 1
            poly = params.get("polygon", "")
            # 粗略用顶点跨度估算面积 -> count
            import re
            pts = re.findall(r"([\d.]+),([\d.]+)", poly)
            if pts:
                xs = [float(a) for a, b in pts]
                ys = [float(b) for a, b in pts]
                span = max(max(xs) - min(xs), max(ys) - min(ys))
                count = int(min(5000, span * 50000))  # 每 0.01 度约 500 条
            else:
                count = 5000
            return {"status": "1", "count": str(count), "pois": []}
        return {"status": "1", "count": "0", "pois": []}

    def _normalize(self, poi):
        return poi


def main():
    events = []
    # ---- 模拟她的配置（around + types + city=行政区划编码）----
    params = {
        "extensions": "base",
        "offset": 20,
        "location": "119.30,26.08",          # 福建某市中心
        "radius": 10000,
        "types": "080000",                    # 体育休闲服务（大类勾选）
        "city": "350100",                     # ⚠️ 她把行政区划编码填进了城市框
        "citylimit": "true",
        "sortrule": "distance",
        "split_mode": "manual",
        "split_threshold": 150,
    }

    client = FakeClient()
    collector = SplitCollector(
        client,
        mode="around",
        center=(119.30, 26.08),
        radius=10000,
        threshold=150,
        max_depth=5,
        # 修复后：worker.py around 分支新排除列表（city/citylimit/sortrule 已剔除）
        extra_params={k: v for k, v in params.items()
                      if k not in ("location", "radius", "city",
                                   "citylimit", "sortrule",
                                   "split_mode", "split_threshold")},
        progress_callback=lambda cur, est, page: None,
        cancelled=lambda: False,
        event_callback=lambda msg: events.append(msg),
    )
    records, total, probes = collector.run()

    print("=" * 62)
    print(f"探测次数={probes}，子请求总数={len(client.calls)}，采得 {total} 条")
    print("=" * 62)

    # ---- 检查点 1：polygon 子请求是否残留非法参数 ----
    poly_calls = [p for ep, p in client.calls if ep == "/polygon"]
    illegal_hits = {"city": 0, "citylimit": 0, "sortrule": 0, "radius": 0, "location": 0}
    for p in poly_calls:
        for k in illegal_hits:
            if k in p:
                illegal_hits[k] += 1
    print("\n[检查点1] polygon 子请求中的非法参数残留（高德 polygon 接口不支持这些参数）:")
    for k, n in illegal_hits.items():
        mark = "⚠️ 残留" if n else "✓ 无"
        print(f"    {k:<10}: {n}/{len(poly_calls)} 次  {mark}")

    # 示例：第一条 polygon 子请求的完整参数
    if poly_calls:
        print("\n    示例——第 1 条 polygon 子请求完整参数:")
        for k, v in poly_calls[0].items():
            print(f"        {k} = {v}")

    # ---- 检查点 2：探测阶段是否有进度反馈 ----
    print(f"\n[检查点2] 探测期事件播报 {len(events)} 条（节流后），示例:")
    for e in events[:3]:
        print(f"    {e}")

    # ---- 检查点 2b：过密警告是否触发 ----
    warns = [e for e in events if "过密" in e]
    print(f"[检查点2b] 过密警告 {len(warns)} 条（数据切到最大深度仍超阈值时应出现）")

    print("\n[结论] 见上方两处检查点输出。")


if __name__ == "__main__":
    main()
