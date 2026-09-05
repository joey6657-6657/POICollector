"""高德 Web 服务 POI 搜索客户端。

封装四类检索：周边(around) / 关键字(text) / 多边形(polygon) / ID(detail)，
并集成多 Key 轮询、指数退避重试、自动翻页、跨页去重、GCJ-02->WGS-84 转换。
"""
import time

import requests

from .key_manager import KeyManager
from .retry_engine import RetryEngine
from .paginator import Paginator
from .coord_transform import gcj02_to_wgs84
from ..data.deduplicator import Deduplicator


class AMapError(Exception):
    """高德接口或客户端层面的可抛出错误。"""


# 触发换 Key / 重试的关键字与错误码
_QUOTA_KEYWORDS = ("DAILY", "QUOTA", "OVER", "LIMIT", "EXCEED", "INVALID_USER_IP")
_QUOTA_CODES = {"10003", "10009", "10010", "10021", "20003", "20011", "20012"}
# Key 无效/不存在/类型错误：与配额无关，单独提示（用户最常见的新手错误：
# 用了 Web端JS/Android/iOS 类型的 Key，而非「Web服务」类型）
_INVALID_KEY_CODES = {"10001"}
_INVALID_KEY_KEYWORDS = ("INVALID_USER_KEY",)


class AMapClient:
    BASE = "https://restapi.amap.com/v3/place"

    def __init__(self, keys, timeout: int = 10, retry: RetryEngine = None,
                 paginator: Paginator = None, event_callback=None):
        self.key_manager = KeyManager(keys)
        self.timeout = timeout
        self.retry = retry or RetryEngine()
        self.paginator = paginator or Paginator()
        self.session = requests.Session()
        self._event = event_callback  # fn(level, message) — level: info/warn/error
        # QPS 限流警告去重：同一 Key 只提示一次，避免刷屏导致用户不信任
        self._qps_warned_keys = set()
        self._qps_all_warned = False
        # 最近一次成功请求的完整 URL（key 已脱敏），供异常场景诊断
        self.last_request_url = None

    def _emit(self, level: str, msg: str):
        if self._event:
            try:
                self._event(level, msg)
            except Exception:
                pass  # 事件回调不应影响主流程

    # ------------------------------------------------------------------ #
    # 低层单次请求（重试 + Key 轮询）
    # ------------------------------------------------------------------ #
    def _call(self, endpoint: str, params: dict, base: str = None):
        last_err = None
        for attempt in range(self.retry.max_retries):
            if not self.key_manager:
                raise AMapError("未配置任何 API Key")
            # 轮询：首次请求用第一把 Key，此后逐请求切换（多 Key 分摊 QPS 限流）
            self.key_manager.acquire()
            params["key"] = self.key_manager.current()
            try:
                resp = self.session.get(
                    (base or self.BASE) + endpoint, params=params, timeout=self.timeout
                )
            except requests.RequestException as e:
                # 纯网络层错误（连接失败/超时/DNS）→ 指数退避重试
                last_err = AMapError(f"网络错误: {e}")
                delay = self.retry.backoff_seconds(attempt)
                self._emit("warn", f"网络异常，第 {attempt+1}/{self.retry.max_retries} 次重试，"
                           f"等待 {delay:.1f}s … ({e})")
                self.retry.sleep(attempt)
                continue

            # 收到了响应：先看 HTTP 状态码，非 200 时响应体大概率是网关/拦截的 HTML
            if resp.status_code != 200:
                snippet = (resp.text or "")[:120].replace("\n", " ").strip() or "(空响应)"
                last_err = AMapError(f"服务返回 HTTP {resp.status_code}: {snippet}")
                delay = self.retry.backoff_seconds(attempt)
                self._emit("warn", f"服务返回 HTTP {resp.status_code}，"
                           f"第 {attempt+1}/{self.retry.max_retries} 次重试，等待 {delay:.1f}s …"
                           f"（响应片段: {snippet}）")
                self.retry.sleep(attempt)
                continue

            try:
                data = resp.json()
            except ValueError as e:
                # 响应体不是 JSON：多为代理/VPN/安全软件/校园网拦截，返回了 HTML 或空体。
                # 把状态码和响应片段写进日志，让用户能自助判断真实原因。
                snippet = (resp.text or "")[:120].replace("\n", " ").strip() or "(空响应)"
                last_err = AMapError(
                    f"响应不是有效 JSON（HTTP {resp.status_code}），可能被代理/VPN/安全软件拦截。"
                    f"响应片段: {snippet}"
                )
                delay = self.retry.backoff_seconds(attempt)
                self._emit("warn", f"响应解析失败，第 {attempt+1}/{self.retry.max_retries} 次重试，"
                           f"等待 {delay:.1f}s …（HTTP {resp.status_code}，"
                           f"响应片段: {snippet}）")
                self.retry.sleep(attempt)
                continue

            if data.get("status") == "1":
                # 记录完整请求 URL（含 Key，仅在本机 GUI 日志展示），供 0 条等
                # 异常场景诊断：用户复制到浏览器可直接查看高德的原始返回
                try:
                    url = getattr(resp, "url", None)
                    if url:
                        self.last_request_url = url
                except Exception:
                    pass
                return data

            info = data.get("info", "未知错误")
            errcode = str(data.get("infocode", ""))
            # Key 无效（10001）：Key 不存在 / 类型错误（如误用 JS/Android Key），
            # 该 Key 永久不可用 → 标记并尝试下一个；全部无效时给出明确指引
            if errcode in _INVALID_KEY_CODES or any(
                    k in info.upper() for k in _INVALID_KEY_KEYWORDS):
                old_key = self.key_manager.current()[:8] + "…" if self.key_manager.current() else "?"
                self.key_manager.mark_exhausted()
                remaining = self.key_manager.available_count()
                self._emit("warn", f"Key [{old_key}] 无效（{errcode}）：不存在或类型错误"
                           f"（须为「Web服务」类型），剩余可用 Key: {remaining}")
                if self.key_manager.next_key():
                    time.sleep(0.3)
                    continue
                raise AMapError(
                    "所有 Key 均无效（10001）。请到高德开放平台控制台检查："
                    "① Key 是否存在且未删除；② 服务平台必须为「Web服务」"
                    "（Web端JS / Android / iOS 类型的 Key 不能用于本软件）")
            if any(k in info.upper() for k in _QUOTA_KEYWORDS) or errcode in _QUOTA_CODES:
                old_key = self.key_manager.current()[:8] + "…" if self.key_manager.current() else "?"
                if errcode == "10021":
                    # QPS 限流是瞬时的：切换 Key + 短暂退避，不永久标记
                    # 同一 Key 的限流警告只显示一次，避免刷屏
                    cur_key = self.key_manager.current()
                    if cur_key not in self._qps_warned_keys:
                        self._qps_warned_keys.add(cur_key)
                        self._emit("warn", f"Key [{old_key}] 触发 QPS 限流，已自动切换 Key 并等待…")
                    if self.key_manager.next_key():
                        time.sleep(0.5)
                        continue
                    # 所有 Key 均受限：指数退避后整体重试（等 QPS 窗口恢复）
                    delay = self.retry.backoff_seconds(attempt)
                    if not self._qps_all_warned:
                        self._qps_all_warned = True
                        self._emit("warn", f"所有 Key 均 QPS 限流，等待 {delay:.1f}s 后重试（后续同类提示将静默）")
                    self.retry.sleep(attempt)
                    continue
                # 日配额耗尽等：永久标记该 Key，不再使用
                self.key_manager.mark_exhausted()
                remaining = self.key_manager.available_count()
                self._emit("warn", f"Key [{old_key}] 配额耗尽/受限 "
                           f"[{errcode}] {info}，剩余可用 Key: {remaining}")
                if self.key_manager.next_key():
                    new_key = self.key_manager.current()[:8] + "…"
                    self._emit("info", f"已切换到新 Key: [{new_key}]")
                    time.sleep(0.3)
                    continue
                raise AMapError(f"所有 Key 均已不可用: {info}（{errcode}）")
            # 业务错误（KEY 无效、参数错误等）不重试
            raise AMapError(f"高德返回错误 [{errcode}] {info}")
        raise last_err or AMapError("请求失败（超过重试上限）")

    # ------------------------------------------------------------------ #
    # 行政区边界（关键词分片用）
    # ------------------------------------------------------------------ #
    DISTRICT_BASE = "https://restapi.amap.com/v3/config"

    def district_polyline(self, keywords: str) -> str:
        """查询行政区边界 polyline（关键词模式网格分片用）。

        调用 /v3/config/district 接口，返回与 keywords 匹配的首个行政区
        的边界坐标串（多环以 | 分隔，环内点以 ; 分隔，点为 lng,lat）。

        注意：extensions 必须为 all —— 官方文档：base 不返回行政区边界
        坐标点，all 才返回当前查询 district 的 polyline。
        """
        p = {"keywords": keywords, "subdistrict": 0,
             "extensions": "all", "offset": 1, "page": 1}
        data = self._call("/district", p, base=self.DISTRICT_BASE)
        districts = data.get("districts") or []
        if not districts:
            raise AMapError(f"行政区接口未找到与 '{keywords}' 匹配的行政区")
        polyline = districts[0].get("polyline") or ""
        if not polyline:
            raise AMapError(f"行政区接口未返回 '{keywords}' 的边界坐标")
        return polyline

    # ------------------------------------------------------------------ #
    # 规范化
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize(poi: dict) -> dict:
        loc = poi.get("location") or ""
        parts = loc.split(",")
        lng = float(parts[0]) if len(parts) == 2 and parts[0] else None
        lat = float(parts[1]) if len(parts) == 2 and parts[1] else None
        wgs = (None, None)
        if lng is not None and lat is not None:
            wgs = gcj02_to_wgs84(lng, lat)
        biz_ext = poi.get("biz_ext") or {}
        return {
            "id": poi.get("id"),
            "name": poi.get("name"),
            "type": poi.get("type"),
            "typecode": poi.get("typecode"),
            "address": poi.get("address"),
            "lng": lng,
            "lat": lat,
            "lng_wgs84": wgs[0],
            "lat_wgs84": wgs[1],
            "tel": poi.get("tel"),
            "pname": poi.get("pname"),
            "cityname": poi.get("cityname"),
            "adname": poi.get("adname"),
            "adcode": poi.get("adcode"),
            "distance": poi.get("distance"),
            "business_area": poi.get("business"),
            "rating": biz_ext.get("rating"),
            "cost": biz_ext.get("cost"),
        }

    # ------------------------------------------------------------------ #
    # 统一入口
    # ------------------------------------------------------------------ #
    def search(self, mode: str, params: dict, auto_paginate: bool = True,
               start_page: int = 1, progress_callback=None,
               checkpoint=None, cancelled=None):
        """执行一次搜索。

        :param mode: 'around' | 'text' | 'polygon' | 'detail'
        :param params: 业务参数（不含 key）
        :param auto_paginate: 列表类接口是否自动翻页
        :param start_page: 断点续传起始页码
        :param progress_callback: fn(current, estimate, page) 进度回调
        :param checkpoint: Checkpoint 实例，非 None 时每页保存断点
        :param cancelled: fn()->bool 是否被取消
        :return: (records, total) —— records 为规范化 dict 列表，total 为去重后数量
        """
        mode = mode.lower()
        if mode == "detail":
            return self._search_detail(params)
        if auto_paginate:
            return self._search_paged(mode, params, start_page=start_page,
                                      progress_callback=progress_callback,
                                      checkpoint=checkpoint,
                                      cancelled=cancelled)
        return self._search_single(mode, params, page=1)

    def _endpoint(self, mode: str) -> str:
        return {"around": "/around", "text": "/text", "polygon": "/polygon"}[mode]

    def _search_single(self, mode: str, params: dict, page: int):
        p = dict(params)
        p["page"] = page
        p.setdefault("offset", self.paginator.page_size)
        p.setdefault("extensions", "base")
        data = self._call(self._endpoint(mode), p)
        pois = data.get("pois") or []
        return [self._normalize(poi) for poi in pois], int(data.get("count") or 0)

    def _search_paged(self, mode: str, params: dict, start_page: int = 1,
                      progress_callback=None, checkpoint=None, cancelled=None):
        dedup = Deduplicator()
        all_records: list = []

        # 从检查点恢复已有 ID
        if checkpoint:
            saved = checkpoint.load()
            for _id in saved.get("collected_ids", []):
                dedup.seen.add(_id)

        page = start_page
        total = 0  # 高德返回的真实总数（count）

        while True:
            if cancelled and cancelled():
                break

            records, count = self._search_single(mode, params, page)
            if page == start_page and count > 0:
                total = count  # 以首页返回的 count 作为真实总数

            new_records = dedup.filter(records)
            all_records.extend(new_records)
            collected = len(all_records)

            # 写入检查点
            if checkpoint:
                checkpoint.save(
                    collected_ids=dedup.seen,
                    last_page=page,
                    params_hash=checkpoint.params_hash,
                )

            # 推送进度（以真实总数作为估算上限）
            if progress_callback:
                progress_callback(collected, total, page)

            if not self.paginator.should_continue(collected, len(records),
                                                  total, page):
                break
            page += 1
            time.sleep(0.2)  # 礼貌性间隔，降低限频风险

        return all_records, collected

    def _search_detail(self, params: dict):
        p = dict(params)
        p.setdefault("extensions", "base")
        data = self._call("/detail", p)
        poi = data.get("poi") or (data.get("pois") or [None])[0]
        if not poi:
            return [], 0
        return [self._normalize(poi)], 1
