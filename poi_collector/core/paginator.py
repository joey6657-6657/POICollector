"""自动翻页控制器。

高德搜索接口约束（官方文档）：
  - 单页 `offset` 上限 25 条（"强烈建议不超过25，若超过25可能造成访问报错"），默认 20。
  - 同请求参数翻页最多获取 200 条数据（硬上限）。
  - `page` 最大约 100 页。

本控制器负责决定何时继续翻页、何时停止，并避免超出配额阈值。
核心原则：以高德返回的 `count`（真实总数）为停止依据，而非"本页是否装满"。
"""


class Paginator:
    def __init__(self, page_size: int = 25, max_records: int = 200,
                 max_pages: int = 100):
        # 单页上限强制不超过 25（高德限制）
        self.page_size = min(page_size, 25)
        # 同参数翻页硬上限 200 条
        self.max_records = max_records
        # page 上限（高德约 100 页）
        self.max_pages = max_pages

    def should_continue(self, collected: int, returned_this_page: int,
                        total: int, page: int) -> bool:
        """是否继续请求下一页。

        :param collected: 已累计条数（去重后）
        :param returned_this_page: 本页实际返回条数
        :param total: 高德本次返回的真实总数（count）
        :param page: 已完成页序号（从 1 开始）
        """
        # 1) 达到硬上限 200 条，停止
        if collected >= self.max_records:
            return False
        # 2) 超出 page 上限，停止
        if page >= self.max_pages:
            return False
        # 3) 本页返回数已达单页上限（说明后面可能还有）
        #    → 仅当"已采集 < 真实总数"时继续
        if returned_this_page < self.page_size:
            # 本页没装满：通常已是最后一页
            return False
        if total > 0 and collected >= total:
            # 已采够真实总数
            return False
        return True
