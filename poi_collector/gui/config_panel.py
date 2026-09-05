"""左侧配置面板：API Key、四模式动态字段、POI 类型、Base/All、翻页、输出格式、保存位置。"""
import os
import sys

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QComboBox, QCheckBox, QRadioButton, QPushButton, QSlider,
                             QTabWidget, QPlainTextEdit, QFileDialog, QButtonGroup,
                             QSpinBox)
from PySide6.QtCore import Qt

from .widgets import PoiTypeList

MODES = ["around", "text", "polygon", "detail"]

# 项目根目录（用于推导默认输出路径）
# PyInstaller --onefile 模式下用 sys.executable 所在目录，否则 __file__ 推导
if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ConfigPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    # ----------------------------- 辅助：卡片容器 ----------------------------- #
    def _make_card(self, title: str):
        """创建一个带标题的白色圆角卡片，返回 (card_widget, inner_layout)。"""
        card = QWidget()
        card.setObjectName("cardPanel")
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(12)
        title_lb = QLabel(title)
        title_lb.setObjectName("cardTitle")
        v.addWidget(title_lb)
        return card, v

    # ----------------------------- 构建 ----------------------------- #
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(18)

        # ---------- API Key ----------
        key_card, key_v = self._make_card("API Key")
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("输入高德 Web 服务 Key；多 Key 用英文逗号分隔")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        key_v.addWidget(self.key_edit)
        self.show_key = QCheckBox("显示 Key")
        self.show_key.toggled.connect(
            lambda v: self.key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if v else QLineEdit.EchoMode.Password))
        key_v.addWidget(self.show_key)
        root.addWidget(key_card)

        # ---------- 采集模式 ----------
        mode_card, mode_v = self._make_card("采集模式")
        self.tab = QTabWidget()
        self._build_around_tab()
        self._build_text_tab()
        self._build_polygon_tab()
        self._build_detail_tab()
        mode_v.addWidget(self.tab)
        root.addWidget(mode_card)

        # ---------- POI 类型 ----------
        type_card, type_v = self._make_card("POI 类型（与关键词二选一；ID 模式忽略）")
        self.type_list = PoiTypeList()
        type_v.addWidget(self.type_list)
        type_v.addWidget(self._hint("大类 / 中类 / 小类 三级树：勾选大类即包含其全部子类；"
                                     "点击左侧箭头可展开查看下级明细"))
        root.addWidget(type_card)

        # ---------- 采集参数 ----------
        param_card, param_v = self._make_card("采集参数")

        # 返回详情程度
        param_v.addWidget(self._label("返回详情程度"))
        ext_row = QHBoxLayout()
        self.base_radio = QRadioButton("Base（推荐）")
        self.all_radio = QRadioButton("All 完整详情")
        self.base_radio.setChecked(True)
        self._ext_group = QButtonGroup(self)
        self._ext_group.addButton(self.base_radio)
        self._ext_group.addButton(self.all_radio)
        ext_row.addWidget(self.base_radio)
        ext_row.addWidget(self.all_radio)
        ext_row.addStretch()
        param_v.addLayout(ext_row)
        param_v.addWidget(self._hint("Base 返回核心字段；All 额外返回评分/人均消费/照片/商圈等，数据量更大"))

        # 每页条数 & 自动翻页
        param_v.addWidget(self._label("每页条数 & 自动翻页"))
        pp = QHBoxLayout()
        pp.setSpacing(12)
        self.offset_spin = self._spin_box(1, 25, 20, 80)
        self.offset_spin.setToolTip(
            "高德接口单页上限为 25 条（官方：强烈建议不超过25，超过可能报错）；"
            "工具会自动翻页，同参数最多累计约 200 条")
        self.autopage_check = QCheckBox("自动翻页（同参数最多约 200 条）")
        self.autopage_check.setChecked(True)
        pp.addWidget(self.offset_spin)
        pp.addSpacing(8)
        pp.addWidget(self.autopage_check)
        pp.addStretch()
        param_v.addLayout(pp)

        # 突破 200 条：区域网格分片
        param_v.addWidget(self._label("突破 200 条上限（自动网格分片）"))
        split_row = QHBoxLayout()
        split_row.setSpacing(14)
        self.split_mode_group = QButtonGroup(self)
        self.split_off = QRadioButton("关闭")
        self.split_auto = QRadioButton("自动（推荐）")
        self.split_manual = QRadioButton("手动")
        self.split_auto.setChecked(True)
        self.split_mode_group.addButton(self.split_off, 0)
        self.split_mode_group.addButton(self.split_auto, 1)
        self.split_mode_group.addButton(self.split_manual, 2)
        for rb in (self.split_off, self.split_auto, self.split_manual):
            split_row.addWidget(rb)
        split_row.addSpacing(16)
        self.threshold_spin = self._spin_box(50, 180, 150, 80)
        self.threshold_spin.setEnabled(False)
        self.threshold_spin.setToolTip("单个网格内 POI 超过此数量时，自动拆分为更小的网格")
        self.threshold_label = QLabel("阈值")
        self.threshold_label.setObjectName("hintLabel")
        self.threshold_label.setEnabled(False)
        split_row.addWidget(self.threshold_label)
        split_row.addWidget(self.threshold_spin)
        split_row.addStretch()
        param_v.addLayout(split_row)
        self.split_mode_group.buttonClicked.connect(self._on_split_mode_changed)
        param_v.addWidget(self._hint("自动模式：先探测整体数量，接口返回 >= 180 条则自动启用分片；"
                                      "手动模式：始终按设定的阈值拆分。适用于周边/多边形/关键词搜索"
                                      "（关键词分片需指定城市，按城市边界切格；ID 查询为单点查询无需分片）。"
                                      "分片会大幅增加请求次数，请配置多个 Key 分摊 QPS 限流。"))
        root.addWidget(param_card)

        # ---------- 导出设置 ----------
        out_card, out_v = self._make_card("导出设置")

        # 输出格式（多选）
        out_v.addWidget(self._label("输出格式（可多选）"))
        fmt_row = QHBoxLayout()
        self.fmt_checks = {}
        for i, (txt, val) in enumerate([("CSV", "csv"), ("Excel", "excel"),
                                        ("GeoJSON", "geojson"), ("JSON", "json"),
                                        ("Shapefile", "shapefile")]):
            cb = QCheckBox(txt)
            cb.setObjectName("fmtCheck")
            if i == 0:
                cb.setChecked(True)
            self.fmt_checks[val] = cb
            fmt_row.addWidget(cb)
        fmt_row.addStretch()
        out_v.addLayout(fmt_row)
        out_v.addWidget(self._hint("可同时勾选多种格式，将按所选格式分别导出同名文件。"
                                    "CSV/Excel/GeoJSON/JSON 各为单文件；Shapefile 是 ESRI 规范格式，"
                                    "会同时生成 .shp/.shx/.dbf/.prj 等配套文件，ArcMap / ArcGIS Pro 可直接打开"))

        # 保存位置
        out_v.addWidget(self._label("导出文件名与保存位置"))
        out_row = QHBoxLayout()
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("输入文件名（无需扩展名），如：南京餐饮POI")
        self.out_edit.setText("poi_result")
        self.out_edit.textChanged.connect(self._update_out_path_label)
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setObjectName("toolBtn")
        self.browse_btn.clicked.connect(self._browse)
        out_row.addWidget(self.out_edit)
        out_row.addWidget(self.browse_btn)
        out_v.addLayout(out_row)
        self.out_path_label = QLabel("")
        self.out_path_label.setObjectName("outPathLabel")
        self.out_path_label.setWordWrap(True)
        out_v.addWidget(self.out_path_label)
        self._update_out_path_label()
        out_v.addWidget(self._hint("点击“浏览...”可直接指定完整保存路径与名称；也可直接输入含路径的完整名称。"
                                    "将按所选格式自动生成 .csv / .xlsx / .geojson / .json / .shp 等文件"))
        root.addWidget(out_card)

        # ---------- 开始采集 ----------
        self.start_btn = QPushButton("开始采集")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setCheckable(True)
        root.addWidget(self.start_btn)
        root.addStretch(1)

    def set_collecting(self, collecting: bool):
        """设置采集按钮的文本与状态，collecting=True 显示'采集中'并禁用。"""
        self.start_btn.setChecked(collecting)
        self.start_btn.setText("采集中" if collecting else "开始采集")
        self.start_btn.setEnabled(not collecting)

    def _build_around_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(6)
        v.addWidget(self._label("中心点经纬度 *"))
        hl = QHBoxLayout()
        self.around_lng = QLineEdit(); self.around_lng.setPlaceholderText("经度（如 118.793）")
        self.around_lat = QLineEdit(); self.around_lat.setPlaceholderText("纬度（如 32.047）")
        hl.addWidget(self.around_lng); hl.addWidget(self.around_lat)
        v.addLayout(hl)
        v.addWidget(self._hint("经度在前，小数点后不超过 6 位（GCJ-02 坐标系）"))
        v.addWidget(self._label("搜索半径（米）"))
        rs = QHBoxLayout()
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(100, 50000)
        self.radius_slider.setValue(5000)
        self.radius_slider.setSingleStep(100)
        # 手动输入框（与滑块双向绑定；单位 m 固定不可改）
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(100, 50000)
        self.radius_spin.setValue(5000)
        self.radius_spin.setSingleStep(100)
        self.radius_spin.setFixedWidth(90)
        self.radius_unit = QLabel("m")
        self.radius_unit.setObjectName("radiusUnitLabel")
        # 滑块 → 输入框
        self.radius_slider.valueChanged.connect(lambda x: self.radius_spin.setValue(x))
        # 输入框 → 滑块（并保持范围上限 50000）
        self.radius_spin.valueChanged.connect(lambda x: self.radius_slider.setValue(x))
        rs.addWidget(self.radius_slider, 4)
        rs.addWidget(self.radius_spin, 0)
        rs.addWidget(self.radius_unit, 0)
        v.addLayout(rs)
        v.addWidget(self._hint("半径范围 100–50000 米；可直接输入数字，滑块会同步移动；单位 m 固定"))
        v.addWidget(self._label("关键词（可选，与类型二选一）"))
        self.around_kw = QLineEdit(); self.around_kw.setPlaceholderText("如：快餐、银行")
        v.addWidget(self.around_kw)
        v.addWidget(self._label("城市（可选）"))
        self.around_city = QLineEdit(); self.around_city.setPlaceholderText("城市名称或编码（如：南京 / 025 / 320100）")
        v.addWidget(self.around_city)
        self.around_citylimit = QCheckBox("仅限本市结果（citylimit）")
        v.addWidget(self.around_citylimit)
        v.addWidget(self._hint("填写城市可缩小搜索范围；支持城市名（南京）、城市编码（025）或行政区编码（320100）"))
        v.addWidget(self._label("排序方式"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("按距离排序（由近到远）", "distance")
        self.sort_combo.addItem("按综合权重排序（默认）", "weight")
        v.addWidget(self.sort_combo)
        v.addWidget(self._hint("按距离排序仅传 types 时生效；只传 keywords 不传 types 时不生效"))
        v.addWidget(self._hint("关键词与 POI 类型都为空时，高德默认查询：餐饮服务 / 生活服务 / 商务住宅"))
        v.addStretch()
        self.tab.addTab(w, "周边搜索")

    def _build_text_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(6)
        v.addWidget(self._label("关键词 *"))
        self.text_kw = QLineEdit(); self.text_kw.setPlaceholderText("如：肯德基、地铁站")
        v.addWidget(self.text_kw)
        v.addWidget(self._label("城市（可选）"))
        self.text_city = QLineEdit(); self.text_city.setPlaceholderText("城市名称或编码（如：南京 / 025 / 320100）")
        v.addWidget(self.text_city)
        self.text_citylimit = QCheckBox("仅限本市结果（citylimit）")
        v.addWidget(self.text_citylimit)
        v.addWidget(self._hint("填写城市可缩小搜索范围；支持城市名（南京）、城市编码（025）或行政区编码（320100）"))
        v.addStretch()
        self.tab.addTab(w, "关键字搜索")

    def _build_polygon_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(6)
        v.addWidget(self._label("多边形顶点坐标 *"))
        self.polygon_edit = QPlainTextEdit()
        self.polygon_edit.setPlaceholderText(
            "每行一个 经度,纬度，至少 3 个顶点：\n118.793,32.047\n118.801,32.050\n118.798,32.058")
        self.polygon_edit.setMaximumHeight(120)
        self.polygon_edit.textChanged.connect(self._update_polygon_info)
        v.addWidget(self.polygon_edit)

        # AOI 辅助工具栏
        tools = QHBoxLayout()
        self.geojson_btn = QPushButton("导入 GeoJSON")
        self.geojson_btn.setObjectName("toolBtn")
        self.geojson_btn.clicked.connect(self._import_geojson)
        tools.addWidget(self.geojson_btn)
        tools.addStretch()
        v.addLayout(tools)

        # 坐标信息
        self.polygon_info = QLabel("已输入 0 个顶点")
        self.polygon_info.setObjectName("polygonInfo")
        v.addWidget(self.polygon_info)

        # 关键词（高德文档确认 polygon 接口支持 keywords 参数）
        v.addWidget(self._label("关键词（可选，与类型二选一）"))
        self.polygon_kw = QLineEdit()
        self.polygon_kw.setPlaceholderText("如：餐饮、肯德基")
        v.addWidget(self.polygon_kw)

        v.addWidget(self._hint("坐标对以 | 连接；软件会自动闭合首尾顶点（高德要求非矩形多边形首尾坐标对相同）；"
                                "顶点过多时会自动改用包围盒查询并在本地按边界过滤；支持导入 GeoJSON 文件自动提取多边形坐标"))
        v.addStretch()
        self.tab.addTab(w, "多边形搜索")

    def _build_detail_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(6)
        note = QLabel(
            "ID 查询接口（/v3/place/detail）仅需 POI ID 即可获取详情，"
            "不支持城市/范围/类型等筛选参数。适用于已知 POI ID、需获取完整详情的场景，"
            "建议配合「输入提示」API 获取 ID 后使用。")
        note.setObjectName("idNote")
        note.setWordWrap(True)
        v.addWidget(note)
        v.addWidget(self._label("POI ID *"))
        self.detail_id = QLineEdit(); self.detail_id.setPlaceholderText("如：B000A7BD6C")
        v.addWidget(self.detail_id)
        v.addStretch()
        self.tab.addTab(w, "ID 查询")

    # ----------------------------- 辅助 ----------------------------- #
    def _label(self, text):
        lb = QLabel(text)
        lb.setObjectName("fieldLabel")
        return lb

    def _hint(self, text):
        lb = QLabel(text)
        lb.setObjectName("hintLabel")
        lb.setWordWrap(True)
        return lb

    def _spin_box(self, mn, mx, val, width):
        sb = QSpinBox()
        sb.setRange(mn, mx)
        sb.setValue(val)
        sb.setFixedWidth(width)
        return sb

    def _browse(self):
        fmts = [v for v, cb in self.fmt_checks.items() if cb.isChecked()] or ["csv"]
        fmt = fmts[0]
        filters = {
            "csv": "CSV (*.csv)",
            "excel": "Excel (*.xlsx)",
            "geojson": "GeoJSON (*.geojson)",
            "json": "JSON (*.json)",
            "shapefile": "Shapefile (*.shp)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self, "选择保存位置（将按所选格式生成同名文件）",
            self.out_edit.text() or "poi_result",
            filters.get(fmt, "All Files (*)"))
        if path:
            # 去掉扩展名，交由采集线程按各格式自动补全
            self.out_edit.setText(os.path.splitext(path)[0])

    def _update_out_path_label(self):
        """根据 out_edit 内容实时显示文件将保存到的目录与完整路径预览。"""
        text = (self.out_edit.text() or "").strip()
        if not text:
            text = "poi_result"
        # 判断是纯文件名还是含路径
        dirname = os.path.dirname(text)
        basename = os.path.basename(text)
        if dirname and os.path.isabs(text):
            dir_display = dirname
            abs_base = text
        else:
            # 纯文件名 → 保存到项目 output/ 目录下
            dir_display = os.path.join(ROOT_DIR, "output")
            abs_base = os.path.join(dir_display, basename)
        fmts = [v for v, cb in self.fmt_checks.items() if cb.isChecked()] or ["csv"]
        ext_map = {"csv": ".csv", "excel": ".xlsx", "geojson": ".geojson",
                   "json": ".json", "shapefile": ".shp"}
        exts = ", ".join(basename + ext_map.get(f, "") for f in fmts[:3])
        if len(fmts) > 3:
            exts += f" …（共 {len(fmts)} 种格式）"
        self.out_path_label.setText(
            f"📁 保存目录：{dir_display}\n"
            f"📄 将生成：{exts}")

    def _on_split_mode_changed(self, _btn):
        """分片模式切换：仅手动模式启用阈值输入。"""
        is_manual = self.split_manual.isChecked()
        self.threshold_spin.setEnabled(is_manual)
        self.threshold_label.setEnabled(is_manual)

    def _split_mode(self) -> str:
        """返回当前分片模式 'off' / 'auto' / 'manual'。"""
        if self.split_manual.isChecked():
            return "manual"
        if self.split_auto.isChecked():
            return "auto"
        return "off"

    def _update_polygon_info(self):
        """更新多边形顶点计数。"""
        lines = [l.strip() for l in self.polygon_edit.toPlainText().splitlines()
                 if l.strip()]
        count = len(lines)
        if hasattr(self, 'polygon_info'):
            self.polygon_info.setText(f"已输入 {count} 个顶点"
                                      + (f"（需 ≥ 3）" if count < 3 else ""))

    def _import_geojson(self):
        """从 GeoJSON 文件导入多边形坐标。"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 GeoJSON 文件", "",
            "GeoJSON (*.geojson);;JSON (*.json);;All Files (*)")
        if not path:
            return
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 提取第一个 Polygon 的坐标
            coords = self._extract_polygon_coords(data)
            if not coords:
                raise ValueError("未在文件中找到有效的 Polygon 几何数据")
            lines = [f"{c[0]},{c[1]}" for c in coords]
            self.polygon_edit.setPlainText("\n".join(lines))
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "导入失败", f"无法解析 GeoJSON：{e}")

    @staticmethod
    def _extract_polygon_coords(data: list | dict) -> list:
        """递归提取 GeoJSON 中第一个 Polygon 的外环坐标，返回 [(lng,lat), ...]。"""
        if isinstance(data, dict):
            geom_type = data.get("type", "")
            if geom_type == "Polygon" and "coordinates" in data:
                # Polygon: [[[lng,lat], ...], ...] — 取外环 (ring 0)
                rings = data["coordinates"]
                if rings and isinstance(rings[0], list):
                    return [(round(c[0], 6), round(c[1], 6)) for c in rings[0]]
            elif geom_type == "MultiPolygon" and "coordinates" in data:
                # MultiPolygon: [[[[lng,lat],...]], ...]
                polys = data["coordinates"]
                if polys and isinstance(polys[0], list) and isinstance(polys[0][0], list):
                    return [(round(c[0], 6), round(c[1], 6)) for c in polys[0][0]]
            elif geom_type == "FeatureCollection" and "features" in data:
                for feat in data["features"]:
                    result = ConfigPanel._extract_polygon_coords(feat)
                    if result:
                        return result
            elif geom_type == "Feature" and "geometry" in data:
                return ConfigPanel._extract_polygon_coords(data["geometry"])
            elif "geometry" in data:
                return ConfigPanel._extract_polygon_coords(data["geometry"])
        elif isinstance(data, list):
            for item in data:
                result = ConfigPanel._extract_polygon_coords(item)
                if result:
                    return result
        return []

    # ----------------------------- 参数收集 ----------------------------- #
    def collect_params(self):
        mode = MODES[self.tab.currentIndex()]
        keys = [k.strip() for k in self.key_edit.text().split(",") if k.strip()]
        if not keys:
            raise ValueError("请填写至少一个 API Key")
        extensions = "all" if self.all_radio.isChecked() else "base"
        offset = self.offset_spin.value()
        params = {"extensions": extensions, "offset": offset}
        types = self.type_list.selected_codes()

        if mode == "around":
            lng = self.around_lng.text().strip()
            lat = self.around_lat.text().strip()
            if not lng or not lat:
                raise ValueError("周边搜索需填写中心点经纬度")
            params["location"] = f"{lng},{lat}"
            params["radius"] = self.radius_slider.value()
            if self.around_kw.text().strip():
                params["keywords"] = self.around_kw.text().strip()
            if types:
                params["types"] = "|".join(types)
            city = self.around_city.text().strip()
            if city:
                params["city"] = city
            if self.around_citylimit.isChecked():
                params["citylimit"] = "true"
            params["sortrule"] = self.sort_combo.currentData()
        elif mode == "text":
            kw = self.text_kw.text().strip()
            if not kw and not types:
                raise ValueError("关键字搜索需填写关键词或选择 POI 类型")
            if kw:
                params["keywords"] = kw
            if types:
                params["types"] = "|".join(types)
            city = self.text_city.text().strip()
            if city:
                params["city"] = city
            if self.text_citylimit.isChecked():
                params["citylimit"] = "true"
        elif mode == "polygon":
            lines = [l.strip() for l in self.polygon_edit.toPlainText().splitlines() if l.strip()]
            if len(lines) < 3:
                raise ValueError("多边形至少需 3 个顶点")
            params["polygon"] = "|".join(lines)
            if types:
                params["types"] = "|".join(types)
            kw_poly = self.polygon_kw.text().strip()
            if kw_poly:
                params["keywords"] = kw_poly
        elif mode == "detail":
            pid = self.detail_id.text().strip()
            if not pid:
                raise ValueError("ID 查询需填写 POI ID")
            params["id"] = pid

        fmts = [val for val, cb in self.fmt_checks.items() if cb.isChecked()]
        if not fmts:
            raise ValueError("请至少选择一种输出格式")
        out = self.out_edit.text().strip()
        if not out:
            raise ValueError("请选择保存位置")
        # 分片采集设置（around/polygon/text 模式可用；detail 模式忽略）
        params["split_mode"] = self._split_mode()   # off / auto / manual
        params["split_threshold"] = self.threshold_spin.value()
        return keys, mode, params, out, fmts
    # ----------------------------- 配置存取 ----------------------------- #
    def get_config(self):
        # 安全：API Key 属敏感凭据，默认不写入配置文件（避免明文落盘泄漏）。
        # 如需保存 Key，请改用专门的密钥管理工具；此处仅保存非敏感配置。
        return {
            "api_key": "",
            "mode": MODES[self.tab.currentIndex()],
            "around": {"lng": self.around_lng.text(), "lat": self.around_lat.text(),
                       "radius": self.radius_slider.value(),
                       "keywords": self.around_kw.text(), "city": self.around_city.text(),
                       "citylimit": self.around_citylimit.isChecked(),
                       "sortrule": self.sort_combo.currentData()},
            "text": {"keywords": self.text_kw.text(), "city": self.text_city.text(),
                     "citylimit": self.text_citylimit.isChecked()},
            "polygon": {"vertices": self.polygon_edit.toPlainText(), "keywords": self.polygon_kw.text()},
            "detail": {"id": self.detail_id.text()},
            "types": self.type_list.selected_codes(),
            "extensions": "all" if self.all_radio.isChecked() else "base",
            "offset": self.offset_spin.value(),
            "autopage": self.autopage_check.isChecked(),
            "split_mode": self._split_mode(),
            "split_threshold": self.threshold_spin.value(),
            "fmt": [val for val, cb in self.fmt_checks.items() if cb.isChecked()],
            "output": self.out_edit.text(),
        }

    def set_config(self, c):
        # Key 不随配置文件保存，加载时留空并提示用户重新填写
        self.key_edit.setText(c.get("api_key", ""))
        if not self.key_edit.text().strip():
            self.key_edit.setPlaceholderText("（配置已加载，但 Key 未保存，请重新填写）")
        self.tab.setCurrentIndex(MODES.index(c.get("mode", "around")))
        a = c.get("around", {})
        self.around_lng.setText(a.get("lng", ""))
        self.around_lat.setText(a.get("lat", ""))
        self.radius_slider.setValue(a.get("radius", 5000))
        self.around_kw.setText(a.get("keywords", ""))
        self.around_city.setText(a.get("city", ""))
        self.around_citylimit.setChecked(a.get("citylimit", False))
        idx = self.sort_combo.findData(a.get("sortrule", "distance"))
        if idx >= 0:
            self.sort_combo.setCurrentIndex(idx)
        t = c.get("text", {})
        self.text_kw.setText(t.get("keywords", ""))
        self.text_city.setText(t.get("city", ""))
        self.text_citylimit.setChecked(t.get("citylimit", False))
        self.polygon_edit.setPlainText(c.get("polygon", {}).get("vertices", ""))
        self.polygon_kw.setText(c.get("polygon", {}).get("keywords", ""))
        self.detail_id.setText(c.get("detail", {}).get("id", ""))
        codes = set(c.get("types", []))
        self.type_list.set_checked_codes(codes)
        self.all_radio.setChecked(c.get("extensions", "base") == "all")
        self.base_radio.setChecked(c.get("extensions", "base") == "base")
        self.offset_spin.setValue(int(c.get("offset", 20)))
        self.autopage_check.setChecked(c.get("autopage", True))
        split_mode = c.get("split_mode", "auto")  # 兼容旧配置：默认自动
        if isinstance(split_mode, bool):  # 兼容 v1.2.0 的 split_enabled
            split_mode = "manual" if split_mode else "off"
        if split_mode == "off":
            self.split_off.setChecked(True)
        elif split_mode == "manual":
            self.split_manual.setChecked(True)
        else:
            self.split_auto.setChecked(True)
        self.threshold_spin.setValue(int(c.get("split_threshold", 150)))
        is_manual = self.split_manual.isChecked()
        self.threshold_spin.setEnabled(is_manual)
        self.threshold_label.setEnabled(is_manual)
        fmts = c.get("fmt", ["csv"])
        if isinstance(fmts, str):
            fmts = [fmts]
        for val, cb in self.fmt_checks.items():
            cb.setChecked(val in fmts)
        self.out_edit.setText(c.get("output", ""))
