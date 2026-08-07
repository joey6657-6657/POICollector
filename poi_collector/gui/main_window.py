"""主窗口：浅色窄侧边栏 + QStackedWidget 页面切换（首页/关于）。"""
import os
import sys

import yaml
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMessageBox, QFileDialog, QSplitter,
                             QScrollArea, QFrame, QSizePolicy, QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap

from .config_panel import ConfigPanel
from .results_panel import ResultsPanel
from .styles import MAIN_STYLE
from .worker import CollectWorker
from .. import __version__
from ..core.amap_client import AMapClient
from ..core.retry_engine import RetryEngine
from ..core.paginator import Paginator
from ..data.exporter import Exporter
from ..core import arcgis_bridge
from ..core import recent_projects


def _get_base_dir():
    """获取项目根目录。

    PyInstaller --onefile 模式下 __file__ 指向临时解压目录（重启后消失），
    因此必须用 sys.executable 所在目录代替；开发模式（直接跑 py）则用 __file__ 推导。
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


ROOT_DIR = _get_base_dir()


def _get_resource_path(filename: str):
    """返回 assets 目录下指定文件的绝对路径；兼容开发模式和 PyInstaller onefile。"""
    candidates = []
    # PyInstaller onefile 运行时的临时解压目录（资源实际在此）
    if hasattr(sys, '_MEIPASS'):
        candidates.append(os.path.join(sys._MEIPASS, "assets", filename))
    # 开发模式 / PyInstaller onedir / exe 同目录部署
    candidates.append(os.path.join(ROOT_DIR, "assets", filename))
    # 兜底：exe 所在目录
    candidates.append(os.path.join(os.path.dirname(sys.executable), "assets", filename))
    for p in candidates:
        if os.path.exists(p):
            return p
    return ""


def _get_logo_path():
    """返回 logo.png 的绝对路径。"""
    return _get_resource_path("logo.png")


class ArcGisWorker(QThread):
    """在后台线程执行 ArcGIS 打开/导入操作，避免阻塞 GUI（无响应）与闪退。"""
    done_signal = pyqtSignal(bool, str, str)

    def __init__(self, func):
        super().__init__()
        self._func = func

    def run(self):
        try:
            result = self._func()
            if isinstance(result, tuple) and len(result) == 3:
                ok, msg, extra = result
            else:
                ok, msg = result
                extra = ""
            self.done_signal.emit(bool(ok), str(msg), str(extra or ""))
        except Exception as e:
            self.done_signal.emit(False, f"操作异常：{e}", "")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"高德 POI 数据采集 v{__version__}")
        self.resize(1440, 900)
        self.setMinimumSize(1160, 720)
        self.worker = None
        self._nav_buttons = {}
        self._build_ui()
        self._apply_style()
        self._apply_window_icon()

    # ----------------------------- UI 构建 ----------------------------- #
    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------- 左侧浅色窄侧边栏 ----------
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(90)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(8, 16, 8, 12)
        sb.setSpacing(0)

        # Logo 图标（使用用户提供的 logo.png）
        self.sidebar_logo = QLabel()
        self.sidebar_logo.setObjectName("sidebarLogo")
        self.sidebar_logo.setFixedSize(42, 42)
        self.sidebar_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sidebar_logo.setScaledContents(True)
        logo_path = _get_logo_path()
        if logo_path and os.path.exists(logo_path):
            self.sidebar_logo.setPixmap(QPixmap(logo_path))
        sb.addWidget(self.sidebar_logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        sb.addSpacing(24)

        # 导航按钮：首页 + 关于
        self.nav_home = self._nav_btn("🏠", "首页")
        self.nav_about = self._nav_btn("ℹ", "关于")
        self._nav_buttons = {
            "home": self.nav_home,
            "about": self.nav_about,
        }
        sb.addWidget(self.nav_home)
        sb.addSpacing(8)
        sb.addWidget(self.nav_about)
        sb.addStretch(1)

        # 底部分隔线 + 操作按钮
        line = QFrame()
        line.setObjectName("sidebarLine")
        line.setFrameShape(QFrame.Shape.HLine)
        sb.addWidget(line)
        sb.addSpacing(8)
        sb.addWidget(self._nav_btn("💾", "保存配置", self._save_config))
        sb.addSpacing(8)
        sb.addWidget(self._nav_btn("📂", "加载配置", self._load_config))
        sb.addSpacing(10)

        # 版本号
        version_lb = QLabel(f"v{__version__}")
        version_lb.setObjectName("sidebarVersion")
        version_lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb.addWidget(version_lb)

        root.addWidget(sidebar)

        # ---------- 右侧：QStackedWidget 页面切换 ----------
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_home_page())
        self.stack.addWidget(self._build_about_page())
        root.addWidget(self.stack, 1)

        self.setCentralWidget(central)

        # 导航按钮行为
        self.nav_home.clicked.connect(lambda: self._set_nav("home"))
        self.nav_about.clicked.connect(lambda: self._set_nav("about"))

        # 信号
        self.config.start_btn.clicked.connect(self._start)
        self.results.pause_btn.clicked.connect(self._pause_collection)
        self.results.arcgis_open_btn.clicked.connect(self._open_in_arcgis)
        self.results.arcgis_import_btn.clicked.connect(self._import_to_project)
        self._refresh_recent_menu()

        # 启动重置
        self.results.clear()
        self.results.set_status("就绪 · 等待采集", "idle")
        self._auto_load_config()
        self._set_nav("home")

        # 缓存
        self.last_records = []
        self.last_base = ""

    def _build_home_page(self):
        """首页：顶部标题栏 + 左右分栏（配置 / 结果）。"""
        page = QWidget()
        rv = QVBoxLayout(page)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        # 顶部标题栏
        header = QWidget()
        header.setObjectName("topBar")
        hb = QHBoxLayout(header)
        hb.setContentsMargins(20, 14, 20, 14)
        hb.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lb = QLabel("采集配置")
        title_lb.setObjectName("topTitle")
        sub_lb = QLabel("设置参数后点击「开始采集」，结果将实时显示在右侧面板")
        sub_lb.setObjectName("topSub")
        title_col.addWidget(title_lb)
        title_col.addWidget(sub_lb)
        hb.addLayout(title_col)

        hb.addStretch()

        rv.addWidget(header)

        # 主体：左右分栏
        body = QWidget()
        body.setObjectName("bodyArea")
        bv = QHBoxLayout(body)
        bv.setContentsMargins(16, 16, 16, 16)
        bv.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：配置面板（带滚动条）
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll.setObjectName("configScrollArea")

        self.config = ConfigPanel()
        self.config.setMinimumWidth(520)
        left_scroll.setWidget(self.config)
        splitter.addWidget(left_scroll)

        # 右侧：结果预览
        self.results = ResultsPanel()
        self.results.setMinimumWidth(540)
        splitter.addWidget(self.results)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([820, 580])
        splitter.setHandleWidth(2)

        bv.addWidget(splitter)
        rv.addWidget(body, 1)
        return page

    def _build_about_page(self):
        """关于页：白色卡片展示版本与说明。"""
        page = QWidget()
        page.setObjectName("bodyArea")
        v = QVBoxLayout(page)
        v.setContentsMargins(24, 24, 24, 24)
        v.setSpacing(16)

        # 顶部标题栏（与首页风格一致）
        header = QWidget()
        header.setObjectName("topBar")
        hb = QHBoxLayout(header)
        hb.setContentsMargins(20, 14, 20, 14)
        title_lb = QLabel("关于 / About")
        title_lb.setObjectName("topTitle")
        hb.addWidget(title_lb)
        hb.addStretch()
        v.addWidget(header)

        card = QWidget()
        card.setObjectName("cardPanel")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(28, 28, 28, 28)
        cv.setSpacing(16)

        title = QLabel("高德 POI 数据采集")
        title.setObjectName("topTitle")
        cv.addWidget(title)

        body = QLabel(
            f"版本 / Version: v{__version__}\n\n"
            "本工具基于高德地图 Web 服务 API 开发，支持周边搜索、关键字搜索、"
            "多边形搜索与 POI ID 详情查询四种采集模式。\n"
            "This tool is built on AMap Web Service API, supporting four collection modes: "
            "nearby search, keyword search, polygon search, and POI ID query.\n\n"
            "内置网格分片突破高德同参数约 200 条的返回上限，支持 CSV / Excel / GeoJSON / JSON / Shapefile 五种导出格式，"
            "并可直接在 ArcGIS / ArcGIS Pro 中打开或写入工程文件。\n"
            "Built-in grid splitting breaks AMap's ~200-result limit per query. "
            "Supports five export formats (CSV/Excel/GeoJSON/JSON/Shapefile) and one-click ArcGIS integration."
        )
        body.setWordWrap(True)
        body.setObjectName("hintLabel")
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cv.addWidget(body)
        cv.addStretch(1)

        v.addWidget(card)
        return page

    def _nav_btn(self, icon: str, label: str, callback=None):
        """生成侧边栏图标按钮：图标在上、文字在下、垂直居中。"""
        btn = QPushButton(f"{icon}\n{label}")
        btn.setObjectName("navBtn")
        btn.setCheckable(callback is None)
        btn.setFixedSize(74, 64)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(label)
        if callback:
            btn.clicked.connect(callback)
        return btn

    def _line(self):
        line = QFrame()
        line.setObjectName("sidebarLine")
        line.setFrameShape(QFrame.Shape.HLine)
        return line

    def _set_nav(self, key: str):
        """高亮当前选中的侧边栏导航按钮并切换页面。"""
        for k, btn in self._nav_buttons.items():
            btn.setChecked(k == key)
            btn.setProperty("active", "true" if k == key else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if key == "home":
            self.stack.setCurrentIndex(0)
        elif key == "about":
            self.stack.setCurrentIndex(1)

    def _apply_window_icon(self):
        """设置窗口图标与任务栏图标；优先使用多尺寸 .ico。"""
        ico_path = _get_resource_path("logo.ico")
        if ico_path:
            self.setWindowIcon(QIcon(ico_path))
        else:
            png_path = _get_logo_path()
            if png_path:
                self.setWindowIcon(QIcon(png_path))

    # ----------------------------- 采集流程 ----------------------------- #
    def _start(self):
        try:
            keys, mode, params, out, fmts = self.config.collect_params()
        except ValueError as e:
            QMessageBox.warning(self, "参数错误", str(e))
            return
        client = AMapClient(
            keys,
            retry=RetryEngine(),
            paginator=Paginator(page_size=params.get("offset", 20)),
        )
        self.results.clear()
        self.results.set_status("采集中", "running")
        self.config.set_collecting(True)
        self.results.add_log(f"[系统] 模式={mode}，参数校验通过，启动采集线程")
        self.last_records = []
        self.last_base = os.path.splitext(out)[0]
        ckpt_dir = os.path.join(ROOT_DIR, "checkpoints")
        os.makedirs(ckpt_dir, exist_ok=True)
        self.worker = CollectWorker(client, mode, params, out, fmts,
                                    checkpoint_dir=ckpt_dir)
        self.worker.log_signal.connect(self.results.add_log)
        self.worker.status_signal.connect(lambda t, s: self.results.set_status(t, s))
        self.worker.result_signal.connect(self._on_result)
        self.worker.progress_signal.connect(self.results.on_progress)
        self.worker.finished.connect(self._on_finished)
        self.config.start_btn.setEnabled(False)
        self.worker.start()
        # 采集开始后确保在首页，方便直接看结果
        self._set_nav("home")

    def _pause_collection(self):
        """用户点击暂停采集：取消当前 worker，并联动恢复左侧按钮为开始采集。"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.results.add_log("[系统] 用户暂停采集，等待当前请求结束后停止…")
            self.results.set_paused()
            self.config.set_collecting(False)
        else:
            self.results.add_log("[系统] 当前没有正在运行的采集任务")

    def _on_result(self, records):
        self.last_records = records
        self.results.show_results(records)
        self.results.set_final_total(len(records))
        self.results.set_arcgis_enabled(bool(records))

    def _on_finished(self):
        self.config.set_collecting(False)
        self.results.finish_progress()
        self.results.add_log("[系统] 采集线程结束")
        # 兜底：若已完成（非用户暂停），确保 KPI 最终数值与 last_records 一致
        if self.last_records and getattr(self.results, "_result_ready", False):
            self.results.update_kpi_total(len(self.last_records))

    # ----------------------------- ArcGIS 桥接 ----------------------------- #
    def _ensure_shapefile(self):
        if not self.last_records:
            return None, "尚未采集到数据，无法导出 Shapefile"
        if self.last_base:
            base = self.last_base
        else:
            base = os.path.join(ROOT_DIR, "output", "poi_result")
        if not os.path.isabs(base):
            base = os.path.join(ROOT_DIR, "output", base)
        shp = base + ".shp"
        try:
            Exporter().export(self.last_records, shp, "shapefile")
        except Exception as e:
            return None, f"Shapefile 导出失败：{e}"
        return os.path.abspath(shp), None

    def _open_in_arcgis(self):
        try:
            shp, err = self._ensure_shapefile()
            if err:
                QMessageBox.information(self, "提示", err)
                return
            self.results.add_log("[ArcGIS·打开] 正在启动 ArcGIS 并加载数据，请稍候…")
            self._run_arcgis_task(
                lambda: arcgis_bridge.open_in_arcgis(shp),
                log_prefix="[ArcGIS·打开]",
                fail_title="ArcGIS 打开失败",
                success_title="ArcGIS 已启动",
            )
        except Exception as e:
            QMessageBox.warning(self, "打开异常", f"操作过程中发生错误：{e}")

    def _import_to_project(self):
        try:
            shp, err = self._ensure_shapefile()
            if err:
                QMessageBox.information(self, "提示", err)
                return
            try:
                default_dir = recent_projects.suggest_default_dir()
            except Exception:
                default_dir = ""
            path, _ = QFileDialog.getOpenFileName(
                self, "选择 ArcGIS 工程文件", default_dir,
                "ArcGIS Pro 工程 (*.aprx);;ArcMap 文档 (*.mxd);;All Files (*)")
            if not path:
                self.results.add_log("[ArcGIS·导入] 已取消选择")
                return
            self.results.add_log(f"[ArcGIS·导入] 已选择工程：{os.path.basename(path)}")
            self._import_with_path(path)
        except Exception as e:
            QMessageBox.warning(self, "导入异常", f"操作过程中发生错误：{e}")

    def _import_with_path(self, path):
        try:
            shp, err = self._ensure_shapefile()
            if err:
                QMessageBox.information(self, "提示", err)
                return
            if not path or not os.path.exists(path):
                QMessageBox.warning(self, "文件不存在", f"未找到工程文件：\n{path}")
                self._refresh_recent_menu()
                return
            self._do_import(shp, path)
        except Exception as e:
            QMessageBox.warning(self, "导入异常", f"操作过程中发生错误：{e}")

    def _do_import(self, shp, path):
        if arcgis_bridge.is_pro_running():
            reply = QMessageBox.question(
                self, "ArcGIS Pro 正在运行",
                "检测到 ArcGIS Pro 正在运行。\n"
                "若目标工程已打开，写入时会因文件被占用而自动另存为副本\n"
                "（原工程不受影响）。是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return
        self.results.add_log(f"[ArcGIS·导入] 正在写入工程：{os.path.basename(path)}，请稍候…")
        self._run_arcgis_task(
            lambda: arcgis_bridge.import_to_project(shp, path),
            log_prefix="[ArcGIS·导入]",
            fail_title="导入失败",
            success_title="导入成功",
            on_success_extra=lambda saved_path: (
                recent_projects.add(saved_path or path),
                self._refresh_recent_menu(),
                self._ask_and_open_project(saved_path or path),
            ),
        )

    def _ask_and_open_project(self, saved_path):
        """导入成功后询问用户是否立即打开工程文件。"""
        reply = QMessageBox.question(
            self, "导入成功",
            f"POI 数据已写入工程：\n{os.path.basename(saved_path)}\n\n"
            "是否立即打开该工程文件？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._auto_open_saved_project(saved_path)
        else:
            self.results.add_log(
                f"[ArcGIS·导入] 用户选择暂不打开工程：{os.path.basename(saved_path)}")

    def _auto_open_saved_project(self, saved_path):
        try:
            ok, msg = arcgis_bridge.launch_arcgis_with_project(saved_path)
            self.results.add_log(f"[ArcGIS·打开工程] {msg}")
            if not ok:
                QMessageBox.information(
                    self, "提示",
                    f"POI 已写入工程，但自动打开 ArcGIS 失败：\n{msg}\n\n"
                    f"工程文件路径：\n{saved_path}\n请手动用 ArcGIS 打开。")
        except Exception as e:
            self.results.add_log(f"[ArcGIS·打开工程] 异常：{e}")

    def _run_arcgis_task(self, func, log_prefix, fail_title,
                          success_title=None, on_success_extra=None):
        self._ag_worker = ArcGisWorker(func)
        def _on_done(ok, msg, extra):
            self.results.add_log(f"{log_prefix} {msg}")
            if ok:
                if on_success_extra:
                    try:
                        on_success_extra(extra)
                    except Exception as e:
                        self.results.add_log(f"{log_prefix} 后续操作异常：{e}")
                if success_title:
                    QMessageBox.information(self, success_title, msg)
            else:
                QMessageBox.warning(self, fail_title, msg)
        self._ag_worker.done_signal.connect(_on_done)
        self._ag_worker.start()

    def _refresh_recent_menu(self):
        self.results.refresh_recent_menu(
            recent_projects.list_recent(),
            on_pick=self._import_with_path,
        )

    # ----------------------------- 配置存取 ----------------------------- #
    def _save_config(self):
        path = os.path.join(ROOT_DIR, "config", "user_config.yaml")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config.get_config(), f, allow_unicode=True)
            self.results.add_log(f"[配置] 已保存至 {path}")
            QMessageBox.information(
                self, "配置已保存",
                f"配置已保存到：\n{path}\n\n"
                f"注意：出于安全考虑，API Key 不会写入配置文件，"
                f"下次启动时需重新填写 Key。其他参数（模式/半径/类型/输出等）会自动恢复。")
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))

    def _load_config(self):
        path = os.path.join(ROOT_DIR, "config", "user_config.yaml")
        if not os.path.exists(path):
            QMessageBox.information(self, "提示", "未找到已保存的配置（config/user_config.yaml）")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.config.set_config(yaml.safe_load(f) or {})
            self.results.add_log("[配置] 已加载 user_config.yaml")
        except Exception as e:
            QMessageBox.warning(self, "加载失败", str(e))

    def _auto_load_config(self):
        path = os.path.join(ROOT_DIR, "config", "user_config.yaml")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.config.set_config(yaml.safe_load(f) or {})
            self.results.add_log("[配置] 已自动加载上次的配置（Key 需重新填写）")
        except Exception:
            pass

    def _apply_style(self):
        self.setStyleSheet(MAIN_STYLE)
