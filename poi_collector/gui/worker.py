"""后台采集工作线程，避免界面卡死。

支持实时进度推送与断点续传：每完成一页通过 progress_signal 上报，
同时将已采集 ID 写入检查点文件，中断后可续采。

v1.2：支持"突破 200 条上限"的网格分片采集（SplitCollector）。
"""
import hashlib
import os

from PyQt6.QtCore import QThread, pyqtSignal

from ..core.amap_client import AMapError
from ..core.checkpoint import Checkpoint
from ..core.splitter import SplitCollector
from ..data.exporter import Exporter


class CollectWorker(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, str)      # (文本, 状态: running/done/error)
    result_signal = pyqtSignal(list)          # 规范化记录列表
    progress_signal = pyqtSignal(int, int, int)  # (当前数量, 估算总数, 当前页码)

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
            split_can_run = self.mode in ("around", "polygon")

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
                # 从业务参数中提取中心/半径/多边形
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
                else:  # polygon
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
                records, total, probe_cnt = collector.run()
                self.log_signal.emit(
                    f"[分片] 完成：探测 {probe_cnt} 次，合并去重后 {total} 条")
            else:
                # ---- 原有单次查询（自动翻页，同参数最多 200 条；支持断点续传）----
                request_params = _clean_params()
                resume_page = 1
                if ckpt:
                    saved = ckpt.load()
                    if saved.get("collected_ids"):
                        resume_page = saved.get("last_page", 0) + 1
                        self.log_signal.emit(
                            f"[续传] 发现检查点，已采集 {len(saved['collected_ids'])} 条，"
                            f"从第 {resume_page} 页继续")
                records, total = self.client.search(
                    self.mode, request_params, auto_paginate=True,
                    start_page=resume_page,
                    progress_callback=self._on_progress,
                    checkpoint=ckpt,
                    cancelled=lambda: self._cancelled,
                )
                self.log_signal.emit(f"[采集] 接口返回去重后 {total} 条")

            # 多格式导出：以 out 为基名，按各格式补全扩展名
            ext_map = {"csv": ".csv", "excel": ".xlsx", "geojson": ".geojson",
                       "json": ".json", "shapefile": ".shp"}
            base = os.path.splitext(self.out)[0]
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
