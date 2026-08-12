"""后台采集工作线程，避免界面卡死。

支持实时进度推送与断点续传：每完成一页通过 progress_signal 上报，
同时将已采集 ID 写入检查点文件，中断后可续采。

v1.2：支持"突破 200 条上限"的网格分片采集（SplitCollector）。
v1.3：停止采集时保留检查点与部分导出，下次同参数启动自动续采并合并已有数据。
v1.4：关键词搜索（text）接入网格分片——解析城市行政区边界后切格采集；
      ID 查询（detail）为单点查询无条数限制，无需分片。
"""
import csv
import hashlib
import json
import os

from PySide6.QtCore import QThread, Signal

from ..core.amap_client import AMapError
from ..core.checkpoint import Checkpoint
from ..core.splitter import SplitCollector
from ..data.exporter import Exporter


class CollectWorker(QThread):
    log_signal = Signal(str)
    status_signal = Signal(str, str)      # (文本, 状态: running/done/error)
    result_signal = Signal(list)          # 规范化记录列表
    progress_signal = Signal(int, int, int)  # (当前数量, 估算总数, 当前页码)

    def __init__(self, client, mode, params, out, fmts,
                 checkpoint_dir: str = None):
        super().__init__()
        self.client = client
        self.mode = mode
        self.params = params
        self.out = out
        self.fmts = fmts if isinstance(fmts, (list, tuple)) else [fmts]
        self.checkpoint_dir = checkpoint_dir or ""
        self._cancelled = False

    def cancel(self):
        """请求取消采集（下次循环检测到后跳出）。"""
        self._cancelled = True

    def _checkpoint_path(self) -> str:
        if not self.checkpoint_dir:
            return ""
        # 用参数指纹区分不同任务
        raw = f"{self.mode}:{sorted(self.params.items())}"
        fp = hashlib.md5(raw.encode()).hexdigest()[:12]
        return os.path.join(self.checkpoint_dir, f"ckpt_{fp}.json")

    def run(self):
        ckpt_path = self._checkpoint_path()
        self._ckpt_path = ckpt_path
        ckpt = Checkpoint(ckpt_path) if ckpt_path else None

        # 事件回调：将 AMapClient 的限速/重试事件转发到日志
        def on_event(level: str, msg: str):
            prefix = {"info": "[信息]", "warn": "[警告]", "error": "[错误]"}.get(level, "[事件]")
            self.log_signal.emit(f"{prefix} {msg}")

        # 给 client 注入事件回调
        self.client._event = on_event

        try:
            self.log_signal.emit(f"[采集] 模式={self.mode}，开始请求高德接口…")

            # ---- 分片采集配置（off / auto / manual）----
            split_mode = str(self.params.get("split_mode", "auto"))
            split_threshold = int(self.params.get("split_threshold", 150))
            # 自动模式的判定阈值（高德上限 200，取 180 留余量）
            AUTO_SPLIT_THRESHOLD = 180
            split_can_run = self.mode in ("around", "polygon", "text")
            if self.mode == "detail" and split_mode != "off":
                self.log_signal.emit("[分片] ID 查询为单点查询，无 200 条限制，无需分片")

            # ---- 分片专用键，不应发给高德 API ----
            def _clean_params():
                return {k: v for k, v in self.params.items()
                        if k not in ("split_mode", "split_threshold")}

            # 决定最终是否分片
            use_split = False
            if split_mode == "manual" and split_can_run:
                use_split = True
                self.log_signal.emit(
                    f"[分片] 手动模式：阈值={split_threshold}，将大区域切成小网格逐块采集")
            elif split_mode == "auto" and split_can_run:
                # 自动模式：先探测一次根区域 count
                try:
                    probe_params = _clean_params()
                    probe_params.pop("offset", None)
                    endpoint = self.client._endpoint(self.mode)
                    probe_params["page"] = 1
                    probe_params["offset"] = 1
                    probe_params.setdefault("extensions", "base")
                    probe_data = self.client._call(endpoint, probe_params)
                    count = int(probe_data.get("count") or 0)
                except Exception as e:
                    count = 0
                    self.log_signal.emit(f"[分片] 自动探测失败，按普通模式采集：{e}")
                if count >= AUTO_SPLIT_THRESHOLD:
                    use_split = True
                    self.log_signal.emit(
                        f"[分片] 自动模式：探测到 {count} 条 ≥ {AUTO_SPLIT_THRESHOLD}，"
                        f"启用网格分片（阈值 {AUTO_SPLIT_THRESHOLD}）")
                else:
                    self.log_signal.emit(
                        f"[分片] 自动模式：探测到 {count} 条 < {AUTO_SPLIT_THRESHOLD}，"
                        f"无需分片，按普通模式采集")

            if use_split:
                collector = None
                # 从业务参数中提取中心/半径/多边形/城市
                if self.mode == "around":
                    loc = self.params.get("location", "")
                    parts = loc.split(",")
                    if len(parts) != 2:
                        raise AMapError("周边搜索需填写中心点经纬度（location）")
                    collector = SplitCollector(
                        self.client,
                        mode="around",
                        center=(float(parts[0]), float(parts[1])),
                        radius=int(self.params.get("radius", 5000)),
                        threshold=AUTO_SPLIT_THRESHOLD if split_mode == "auto" else split_threshold,
                        extra_params={k: v for k, v in self.params.items()
                                      if k not in ("location", "radius",
                                                   "split_mode", "split_threshold")},
                        progress_callback=self._on_progress,
                        cancelled=lambda: self._cancelled,
                    )
                elif self.mode == "polygon":  # polygon
                    lines = [l.strip() for l in self.params.get("polygon", "").split("|")
                             if l.strip()]
                    if len(lines) < 3:
                        raise AMapError("多边形至少需 3 个顶点")
                    verts = []
                    for line in lines:
                        xy = line.split(",")
                        if len(xy) == 2:
                            verts.append((float(xy[0]), float(xy[1])))
                    collector = SplitCollector(
                        self.client,
                        mode="polygon",
                        polygon=verts,
                        threshold=AUTO_SPLIT_THRESHOLD if split_mode == "auto" else split_threshold,
                        extra_params={k: v for k, v in self.params.items()
                                      if k not in ("polygon", "split_mode",
                                                   "split_threshold")},
                        progress_callback=self._on_progress,
                        cancelled=lambda: self._cancelled,
                    )
                else:  # text：按城市行政区边界切格，突破关键词搜索 200 条上限
                    city = str(self.params.get("city", "")).strip()
                    if not city:
                        use_split = False
                        self.log_signal.emit(
                            "[分片] 关键词分片需指定城市（未指定时为全国范围，切格代价过大），"
                            "已退回普通翻页（同参数最多约 200 条）")
                    else:
                        try:
                            polyline = self.client.district_polyline(city)
                            rings = self._parse_district_polyline(polyline)
                            if not rings:
                                raise ValueError("边界坐标解析为空")
                        except Exception as e:
                            use_split = False
                            self.log_signal.emit(
                                f"[分片] 解析城市「{city}」行政区边界失败，退回普通翻页：{e}")
                        if use_split:
                            verts = [pt for ring in rings for pt in ring]
                            self.log_signal.emit(
                                f"[分片] 关键词模式：已解析「{city}」边界"
                                f"（{len(rings)} 环 / {len(verts)} 点），按城市范围切格采集")
                            collector = SplitCollector(
                                self.client,
                                mode="polygon",
                                polygon=verts,
                                filter_rings=rings,
                                threshold=AUTO_SPLIT_THRESHOLD if split_mode == "auto" else split_threshold,
                                extra_params={k: v for k, v in self.params.items()
                                              if k not in ("split_mode", "split_threshold")},
                                progress_callback=self._on_progress,
                                cancelled=lambda: self._cancelled,
                            )
            if use_split:
                records, total, probe_cnt = collector.run()
                self.log_signal.emit(
                    f"[分片] 完成：探测 {probe_cnt} 次，合并去重后 {total} 条")
            else:
                # ---- 原有单次查询（自动翻页，同参数最多 200 条；支持断点续传）----
                request_params = _clean_params()
                resume_page = 1
                prior = []
                if ckpt:
                    saved = ckpt.load()
                    if saved.get("collected_ids"):
                        resume_page = saved.get("last_page", 0) + 1
                        self.log_signal.emit(
                            f"[续传] 发现检查点，已采集 {len(saved['collected_ids'])} 条，"
                            f"从第 {resume_page} 页继续")
                        # 检查点只存了 ID，历史数据需从已导出文件回读，
                        # 否则本次导出只剩续采部分，会覆盖丢失上一段数据
                        prior = self._load_prior_records(os.path.splitext(self.out)[0])
                        if prior:
                            self.log_signal.emit(f"[续传] 已回读历史数据 {len(prior)} 条，将与新采数据合并")
                records, total = self.client.search(
                    self.mode, request_params, auto_paginate=True,
                    start_page=resume_page,
                    progress_callback=self._on_progress,
                    checkpoint=ckpt,
                    cancelled=lambda: self._cancelled,
                )
                if prior:
                    # 与回读的历史数据合并；跨段 ID 去重已由检查点完成
                    records = prior + records
                    total = len(records)
                self.log_signal.emit(f"[采集] 接口返回去重后 {total} 条")

            # 多格式导出：以 out 为基名，按各格式补全扩展名
            ext_map = {"csv": ".csv", "excel": ".xlsx", "geojson": ".geojson",
                       "json": ".json", "shapefile": ".shp"}
            base = os.path.splitext(self.out)[0]

            if self._cancelled:
                # 用户中途停止：导出已采部分并保留检查点，下次同参数启动自动续采
                if records:
                    saved = []
                    for fmt in self.fmts:
                        path = base + ext_map.get(fmt, "." + str(fmt))
                        Exporter().export(records, path, fmt)
                        saved.append(path)
                    self.log_signal.emit(
                        f"[导出] 已保存当前进度 {len(records)} 条（{len(saved)} 个文件）")
                self.result_signal.emit(records)
                if ckpt:
                    self.log_signal.emit(
                        f"[系统] 采集已停止，检查点已保留（{os.path.basename(ckpt_path)}），"
                        f"下次使用相同参数点「开始采集」可自动续采")
                self.status_signal.emit(f"已停止（已采 {len(records)} 条，可续采）", "idle")
                return

            saved = []
            for fmt in self.fmts:
                path = base + ext_map.get(fmt, "." + str(fmt))
                Exporter().export(records, path, fmt)
                saved.append(path)
            self.log_signal.emit(f"[导出] 已保存 {len(saved)} 个文件：{', '.join(saved)}")
            self.result_signal.emit(records)
            self.status_signal.emit(f"完成（{total} 条 / {len(saved)} 个文件）", "done")

            # 成功完成后清除检查点
            if ckpt:
                ckpt.clear()

        except AMapError as e:
            self.log_signal.emit(f"[错误] {e}")
            self.status_signal.emit("出错", "error")
        except Exception as e:
            self.log_signal.emit(f"[异常] {e}")
            self.status_signal.emit("出错", "error")

    def _on_progress(self, current: int, estimate: int, page: int):
        self.progress_signal.emit(current, estimate, page)

    @staticmethod
    def _parse_district_polyline(polyline: str):
        """解析高德行政区边界坐标串为环列表。

        格式：多环以 | 分隔，环内点以 ; 分隔，每点为 lng,lat。
        返回 [[(lng, lat), ...], ...]；点数不足 3 的环丢弃。
        """
        rings = []
        for seg in polyline.split("|"):
            pts = []
            for pair in seg.split(";"):
                xy = pair.split(",")
                if len(xy) == 2:
                    try:
                        pts.append((float(xy[0]), float(xy[1])))
                    except ValueError:
                        continue
            if len(pts) >= 3:
                rings.append(pts)
        return rings

    @staticmethod
    def _load_prior_records(base: str):
        """续采前回读上次已导出的记录，优先 .json（字段全），其次 .csv。

        返回规范化 dict 列表；无可用文件时返回 []。
        """
        json_path = base + ".json"
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return [r for r in data if isinstance(r, dict)]
            except (OSError, ValueError):
                pass
        csv_path = base + ".csv"
        if os.path.exists(csv_path):
            _FLOAT = {"lng", "lat", "lng_wgs84", "lat_wgs84", "distance", "rating", "cost"}
            try:
                with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                    rows = []
                    for row in csv.DictReader(f):
                        for k, v in row.items():
                            if v == "":
                                row[k] = None
                            elif k in _FLOAT and v is not None:
                                try:
                                    row[k] = float(v)
                                except ValueError:
                                    row[k] = None
                        rows.append(row)
                    return rows
            except OSError:
                pass
        return []
