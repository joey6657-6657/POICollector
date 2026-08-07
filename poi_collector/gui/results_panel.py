"""结果预览面板：KPI 统计 + 状态栏 + 数据预览表 + 进度条 + 运行日志 + ArcGIS 操作。"""
import os

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QPlainTextEdit, QHeaderView, QProgressBar,
                             QMenu, QFrame)
from PyQt6.QtCore import Qt


class ResultsPanel(QWidget):
    COLUMNS = ["名称", "类型", "地址", "经纬度", "距离(m)"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._total_records = 0
        self._result_ready = False  # True 表示已有最终结果，不再被进度信号覆盖
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # ---------- KPI 统计行（2x2 网格，避免右侧宽度不足时拥挤） ----------
        kpi_grid = QHBoxLayout()
        kpi_grid.setSpacing(12)
        left_col = QVBoxLayout()
        left_col.setSpacing(12)
        right_col = QVBoxLayout()
        right_col.setSpacing(12)
        self.kpi_total = self._kpi_card("总记录数", "0")
        self.kpi_preview = self._kpi_card("预览行数", "0")
        self.kpi_status = self._kpi_card("当前状态", "就绪")
        self.kpi_arcgis = self._kpi_card("ArcGIS", "未就绪")
        left_col.addWidget(self.kpi_total)
        left_col.addWidget(self.kpi_preview)
        right_col.addWidget(self.kpi_status)
        right_col.addWidget(self.kpi_arcgis)
        kpi_grid.addLayout(left_col)
        kpi_grid.addLayout(right_col)
        root.addLayout(kpi_grid)

        # ---------- 状态与 ArcGIS 操作卡片 ----------
        top_card = QWidget()
        top_card.setObjectName("cardPanel")
        tc = QVBoxLayout(top_card)
        tc.setContentsMargins(18, 16, 18, 16)
        tc.setSpacing(12)

        # 状态栏
        self.status_bar = QLabel("● 就绪")
        self.status_bar.setObjectName("statusBar")
        tc.addWidget(self.status_bar)

        # ArcGIS 操作区
        arc_row = QHBoxLayout()
        self.arcgis_open_btn = QPushButton("在 ArcGIS 中打开")
        self.arcgis_open_btn.setObjectName("arcBtn")
        self.arcgis_open_btn.setEnabled(False)
        self.arcgis_open_btn.setToolTip(
            "按钮 A：自动将采集结果导出为 Shapefile，然后启动你电脑上的\n"
            "ArcGIS / ArcGIS Pro 并直接加载数据到新地图")
        self.arcgis_import_btn = QPushButton("导入到工程文件")
        self.arcgis_import_btn.setObjectName("arcBtn")
        self.arcgis_import_btn.setEnabled(False)
        self.arcgis_import_btn.setToolTip(
            "按钮 B：将采集结果以 Shapefile 图层形式写入你指定的\n"
            "ArcGIS 工程（.aprx 为 ArcGIS Pro，.mxd 为 ArcMap）")
        self.arcgis_import_menu_btn = QPushButton("▾")
        self.arcgis_import_menu_btn.setObjectName("arcBtnMenu")
        self.arcgis_import_menu_btn.setEnabled(False)
        self.arcgis_import_menu_btn.setToolTip("选择最近使用过的工程文件")
        self.arcgis_import_menu_btn.setFixedWidth(32)
        self._recent_menu = QMenu(self)
        self.arcgis_import_menu_btn.setMenu(self._recent_menu)
        arc_row.addWidget(self.arcgis_open_btn)
        arc_row.addWidget(self.arcgis_import_btn)
        arc_row.addWidget(self.arcgis_import_menu_btn)
        arc_row.addStretch()
        tc.addLayout(arc_row)

        self.arc_hint = QLabel(
            "采集完成后可用：按钮 A 直接在 ArcGIS 中打开数据；"
            "按钮 B 将数据图层写入已有的 ArcGIS 工程文件（.aprx / .mxd）")
        self.arc_hint.setObjectName("hintLabel")
        self.arc_hint.setWordWrap(True)
        tc.addWidget(self.arc_hint)
        root.addWidget(top_card)

        # ---------- 数据预览卡片 ----------
        table_card = QWidget()
        table_card.setObjectName("cardPanel")
        tvc = QVBoxLayout(table_card)
        tvc.setContentsMargins(18, 16, 18, 16)
        tvc.setSpacing(12)

        table_title = QLabel("数据预览")
        table_title.setObjectName("cardTitle")
        tvc.addWidget(table_title)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(240)
        tvc.addWidget(self.table, 1)

        # 进度区域
        self.progress_widget = QWidget()
        ph_layout = QVBoxLayout(self.progress_widget)
        ph_layout.setContentsMargins(0, 0, 0, 0)
        ph_layout.setSpacing(8)
        self.progress_label = QLabel("")
        self.progress_label.setObjectName("progressLabel")
        ph_layout.addWidget(self.progress_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setObjectName("progressBar")
        ph_layout.addWidget(self.progress_bar)
        # 暂停采集按钮（与进度条联动）
        self.pause_btn = QPushButton("暂停采集")
        self.pause_btn.setObjectName("toolBtn")
        self.pause_btn.setMinimumHeight(34)
        self.pause_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_btn.setVisible(False)
        ph_layout.addWidget(self.pause_btn)
        self.progress_widget.setVisible(False)
        tvc.addWidget(self.progress_widget)
        root.addWidget(table_card, 2)

        # ---------- 运行日志卡片 ----------
        log_card = QWidget()
        log_card.setObjectName("cardPanel")
        lc = QVBoxLayout(log_card)
        lc.setContentsMargins(18, 16, 18, 16)
        lc.setSpacing(12)

        log_title = QLabel("运行日志")
        log_title.setObjectName("cardTitle")
        lc.addWidget(log_title)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setObjectName("logBox")
        self.log.setMinimumHeight(140)
        lc.addWidget(self.log, 1)
        root.addWidget(log_card, 1)

        self.set_status("就绪", "idle")

    def _kpi_card(self, label: str, value: str):
        card = QWidget()
        card.setObjectName("kpiCard")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(4)
        val = QLabel(value)
        val.setObjectName("kpiValue")
        lb = QLabel(label)
        lb.setObjectName("kpiLabel")
        v.addWidget(val)
        v.addWidget(lb)
        # 直接保存 value 标签引用，避免 findChild 在复杂布局中查找歧义
        card._value_label = val
        return card

    def _update_kpi(self, total=0, preview=0, status_text=None, arcgis_ready=None):
        if total is not None:
            self.kpi_total._value_label.setText(str(total))
        if preview is not None:
            self.kpi_preview._value_label.setText(str(preview))
        if status_text is not None:
            self.kpi_status._value_label.setText(status_text)
        if arcgis_ready is not None:
            self.kpi_arcgis._value_label.setText(
                "已就绪" if arcgis_ready else "未就绪")

    def set_status(self, text: str, state: str):
        palette = {
            "idle": ("#16a34a", "#f0fdf4", "#bbf7d0"),
            "running": ("#2563EB", "#eff6ff", "#bfdbfe"),
            "done": ("#16a34a", "#f0fdf4", "#bbf7d0"),
            "error": ("#dc2626", "#fef2f2", "#fecaca"),
        }
        color, bg, border = palette.get(state, ("#64748b", "#f8fafc", "#e2e8f0"))
        self.status_bar.setText(f"● {text}")
        self.status_bar.setStyleSheet(
            f"font-size:13.5px;font-weight:600;color:{color};padding:10px 14px;"
            f"background:{bg};border:1px solid {border};border-radius:10px;"
        )
        self._update_kpi(status_text=text)

    def add_log(self, line: str):
        self.log.appendPlainText(line)

    def set_arcgis_enabled(self, enabled: bool):
        """采集完成后启用 ArcGIS 操作按钮。"""
        self.arcgis_open_btn.setEnabled(enabled)
        self.arcgis_import_btn.setEnabled(enabled)
        self.arcgis_import_menu_btn.setEnabled(enabled)
        self._update_kpi(arcgis_ready=enabled)

    def refresh_recent_menu(self, recent_list, on_pick):
        """用最近工程列表刷新下拉菜单。on_pick(path) 在选中时回调。"""
        self._recent_menu.clear()
        if not recent_list:
            act = self._recent_menu.addAction("（暂无最近工程）")
            act.setEnabled(False)
            return
        for p in recent_list:
            label = os.path.basename(p)
            act = self._recent_menu.addAction(label)
            act.setToolTip(p)
            act.triggered.connect(lambda _checked, path=p: on_pick(path))

    def show_results(self, records):
        self._total_records = len(records)
        self._result_ready = True
        self.table.setRowCount(0)
        preview = records[:1000]
        for r in preview:
            row = self.table.rowCount()
            self.table.insertRow(row)
            lng = r.get("lng")
            lat = r.get("lat")
            coord = f"{lng},{lat}" if lng is not None else ""
            vals = [
                str(r.get("name") or ""),
                str(r.get("type") or ""),
                str(r.get("address") or ""),
                coord,
                str(r.get("distance") or ""),
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(v)
                item.setToolTip(v)
                self.table.setItem(row, col, item)
        note = "" if len(records) <= len(preview) else f"（仅预览前 {len(preview)} 条，全部已导出）"
        self.add_log(f"[预览] 表格展示 {min(len(records), len(preview))} 条 {note}")
        self._update_kpi(total=len(records), preview=min(len(records), len(preview)))

    def clear(self):
        """重置所有状态。每次开始新采集前调用。"""
        self._total_records = 0
        self._result_ready = False
        self.table.setRowCount(0)
        self.log.clear()
        self.progress_bar.setValue(0)
        self.progress_label.setText("")
        self.progress_widget.setVisible(False)
        self.pause_btn.setVisible(False)
        self.set_arcgis_enabled(False)
        self.set_status("就绪", "idle")
        self._update_kpi(total=0, preview=0)

    def on_progress(self, current: int, estimate: int, page: int):
        """接收进度信号并更新 UI。"""
        self.progress_widget.setVisible(True)
        self.pause_btn.setVisible(True)
        if estimate > 0:
            self.progress_bar.setMaximum(estimate)
            self.progress_bar.setValue(current)
            self.progress_label.setText(
                f"已采集 {current} 条 / 估算 {estimate} 条  ·  第 {page} 页"
            )
        else:
            self.progress_bar.setMaximum(0)
            self.progress_bar.setValue(0)
            self.progress_label.setText(f"已采集 {current} 条  ·  第 {page} 页")
        # 过程中让 KPI 总记录数随进度增长；一旦已有最终结果则不再覆盖
        if not self._result_ready:
            self._update_kpi(total=current)

    def finish_progress(self):
        """采集结束时收尾。"""
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.pause_btn.setVisible(False)

    def set_paused(self):
        """暂停采集后的 UI 状态。"""
        self.pause_btn.setVisible(False)
        self.progress_label.setText(self.progress_label.text() + "  ·  已暂停")
        self.set_status("已暂停", "idle")

    def set_final_total(self, total: int):
        """设置最终采集条数。"""
        self._result_ready = True
        self.progress_label.setText(f"采集完成，共 {total} 条")
        self._update_kpi(total=total)

    def update_kpi_total(self, total: int, preview: int = None):
        """仅更新 KPI 数值，不重新填充表格（用于 _on_finished 兜底）。"""
        self._result_ready = True
        if preview is None:
            preview = min(total, 1000)
        self._update_kpi(total=total, preview=preview)
