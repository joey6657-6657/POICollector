"""统一 QSS 样式表 —— B 端 Dashboard 风格。

参考设计语言：
- 左侧图标导航栏（深色或浅色）
- 顶部标题栏
- 浅灰背景 (#F1F5F9)
- 白色圆角卡片、大圆角 (12-16px)
- 柔和边框、清晰的层级
- 蓝色 (#2563EB) 作为主强调色
"""

MAIN_STYLE = """
/* =========================================================
   基础 / 窗口
   ========================================================= */
QMainWindow { background:#F1F5F9; }
QWidget { font-family:"Microsoft YaHei UI","Segoe UI",Arial,sans-serif; }

/* =========================================================
   左侧窄侧边栏（浅色、简洁、参考图风格）
   ========================================================= */
QWidget#sidebar {
    background:#fff;
    border-right:1px solid #E2E8F0;
    border-top-right-radius:0px;
    border-bottom-right-radius:0px;
}
QLabel#sidebarLogo {
    background:transparent;
    border-radius:10px;
}
QLabel#sidebarVersion { font-size:10px; color:#94A3B8; padding:4px 0px; }
QPushButton#navBtn {
    background:transparent; color:#64748B; border:none; border-radius:10px;
    padding:8px 2px; font-size:11px; line-height:140%;
}
QPushButton#navBtn:hover { background:#F1F5F9; color:#334155; }
QPushButton#navBtn:checked, QPushButton#navBtn[active="true"] {
    background:#EFF6FF; color:#2563EB; font-weight:600;
}
QFrame#sidebarLine {
    background:#E2E8F0; max-height:1px; min-height:1px;
    margin:8px 10px;
}

/* =========================================================
   顶部标题栏
   ========================================================= */
QWidget#topBar {
    background:#fff; border-bottom:1px solid #E2E8F0;
}
QLabel#topTitle { font-size:17px; font-weight:700; color:#1E293B; }
QLabel#topSub { font-size:12px; color:#64748B; }
QPushButton#topBtn {
    background:#F8FAFC; color:#334155; font-size:12.5px;
    border:1px solid #E2E8F0; border-radius:8px; padding:7px 16px;
}
QPushButton#topBtn:hover { background:#F1F5F9; border-color:#CBD5E1; }

/* =========================================================
   主体区域
   ========================================================= */
QWidget#bodyArea { background:#F1F5F9; }
QScrollArea#configScrollArea { background:transparent; border:none; }

/* =========================================================
   卡片 / 分组
   ========================================================= */
QWidget#cardPanel {
    background:#fff; border:1px solid #E2E8F0; border-radius:16px;
}
QLabel#cardTitle {
    font-size:15px; font-weight:700; color:#1E293B; padding-bottom:8px;
    border-bottom:1px solid #F1F5F9; margin-bottom:6px;
}
QLabel#cardTitleSmall {
    font-size:13px; font-weight:600; color:#475569;
}

/* KPI 小卡片 */
QWidget#kpiCard {
    background:#fff; border:1px solid #E2E8F0; border-radius:12px;
}
QLabel#kpiValue {
    font-size:22px; font-weight:700; color:#1E293B;
}
QLabel#kpiLabel {
    font-size:12px; color:#64748B;
}
QLabel#kpiDelta {
    font-size:12px; font-weight:600;
}

/* =========================================================
   文字标签
   ========================================================= */
QLabel { color:#1E293B; }
QLabel#fieldLabel { font-size:13px; font-weight:600; color:#334155; margin-top:6px; }
QLabel#sectionTitle { font-size:14px; font-weight:600; color:#1E293B; }
QLabel#hintLabel {
    font-size:11.5px; color:#64748B; line-height:150%;
    margin-top:4px; margin-bottom:4px;
}
QLabel#outPathLabel {
    font-size:12px; color:#047857; background:#ECFDF5;
    border:1px solid #A7F3D0; border-radius:8px; padding:8px 12px;
}
QLabel#idNote {
    font-size:12px; color:#92400E; background:#FFFBEB;
    border:1px solid #FDE68A; border-radius:8px; padding:10px 12px;
}
QLabel#radiusUnitLabel { font-size:13px; color:#64748B; padding-left:4px; }
QLabel#polygonInfo { font-size:11.5px; color:#64748B; }

/* =========================================================
   分割线
   ========================================================= */
QSplitter::handle { background:#E2E8F0; }
QSplitter::handle:horizontal { width:2px; }
QSplitter::handle:vertical { height:2px; }

/* =========================================================
   输入控件
   ========================================================= */
QLineEdit, QComboBox, QPlainTextEdit, QSpinBox {
    border:1px solid #CBD5E1; border-radius:8px; padding:8px 12px;
    font-size:13px; color:#1E293B; background:#fff;
}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QSpinBox:focus { border:1px solid #2563EB; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled { background:#F1F5F9; color:#94A3B8; }
QComboBox::drop-down { border:none; width:24px; }
QComboBox QAbstractItemView {
    background:#fff; border:1px solid #E2E8F0; border-radius:8px;
    selection-background-color:#DBEAFE;
}
QSpinBox::up-button, QSpinBox::down-button {
    width:22px; border-left:1px solid #E2E8F0; background:#F8FAFC;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background:#F1F5F9; }

/* =========================================================
   选择控件
   ========================================================= */
QCheckBox, QRadioButton { font-size:13px; color:#334155; spacing:6px; }
QCheckBox::indicator, QRadioButton::indicator { width:16px; height:16px; }
QCheckBox::indicator:unchecked { background:#fff; border:2px solid #CBD5E1; border-radius:4px; }
QCheckBox::indicator:checked { background:#2563EB; border:2px solid #2563EB; border-radius:4px; }
QRadioButton::indicator:unchecked { background:#fff; border:2px solid #CBD5E1; border-radius:8px; }
QRadioButton::indicator:checked { background:#2563EB; border:2px solid #2563EB; border-radius:8px; }

/* =========================================================
   按钮
   ========================================================= */
QPushButton#primaryBtn {
    background:#2563EB; color:#fff; border:none; border-radius:10px;
    padding:12px 20px; font-size:14px; font-weight:600;
}
QPushButton#primaryBtn:hover { background:#1D4ED8; }
QPushButton#primaryBtn:pressed { background:#1E40AF; }
QPushButton#primaryBtn:disabled { background:#93C5FD; }

QPushButton#toolBtn {
    background:#fff; color:#334155; border:1px solid #CBD5E1;
    border-radius:8px; padding:6px 14px; font-size:12.5px;
}
QPushButton#toolBtn:hover { background:#F8FAFC; border-color:#94A3B8; }

QPushButton#arcBtn {
    background:#fff; color:#2563EB; border:1px solid #BFDBFE;
    border-radius:10px; padding:9px 16px; font-size:13px; font-weight:600;
}
QPushButton#arcBtn:hover:!disabled { background:#EFF6FF; border-color:#3B82F6; }
QPushButton#arcBtn:disabled { color:#94A3B8; border-color:#E2E8F0; background:#F8FAFC; }

QPushButton#arcBtnMenu {
    background:#fff; color:#2563EB; border:1px solid #BFDBFE;
    border-radius:10px; padding:9px 6px; font-weight:600;
}
QPushButton#arcBtnMenu:hover:!disabled { background:#EFF6FF; }
QPushButton#arcBtnMenu:disabled { color:#94A3B8; border-color:#E2E8F0; background:#F8FAFC; }

/* =========================================================
   Tab（采集模式四标签）
   ========================================================= */
QTabWidget::pane {
    border:1px solid #E2E8F0; border-radius:12px;
    border-top-left-radius:0px; background:#fff;
    padding:4px;
}
QTabBar::tab {
    padding:10px 20px; font-size:13px; color:#64748B;
    background:#F1F5F9; border:1px solid #E2E8F0;
    border-bottom:none; border-top-left-radius:10px; border-top-right-radius:10px;
    margin-right:4px;
}
QTabBar::tab:selected {
    color:#2563EB; font-weight:600; background:#fff;
    border-bottom:2px solid #2563EB;
}
QTabBar::tab:hover:!selected { color:#334155; background:#E2E8F0; }
QTabBar::tab:!selected { margin-top:3px; padding-top:8px; }

/* =========================================================
   滑块
   ========================================================= */
QSlider::groove:horizontal { height:6px; background:#E2E8F0; border-radius:3px; }
QSlider::handle:horizontal {
    width:18px; height:18px; margin:-6px 0;
    background:#fff; border:2px solid #2563EB; border-radius:9px;
}
QSlider::sub-page:horizontal { background:#93C5FD; border-radius:3px; }

/* =========================================================
   树形 / 列表
   ========================================================= */
QTreeWidget { font-size:12.5px; background:#fff; border:1px solid #E2E8F0;
              border-radius:10px; color:#334155; padding:4px; outline:none; }
QTreeWidget::item { padding:4px 6px; border-radius:4px; }
QTreeWidget::item:hover { background:#F0F9FF; }
QTreeWidget::item:selected { background:#DBEAFE; color:#1E40AF; }

QListWidget { font-size:12px; background:#fff; border:1px solid #E2E8F0;
              border-radius:10px; color:#334155; padding:4px; outline:none; }
QListWidget::item { padding:4px 6px; border-radius:4px; }
QListWidget::item:hover { background:#F0F9FF; }
QListWidget::item:selected { background:#DBEAFE; color:#1E40AF; }

/* =========================================================
   表格
   ========================================================= */
QTableWidget { font-size:12.5px; gridline-color:#F1F5F9;
               border:1px solid #E2E8F0; border-radius:10px;
               background:#fff; color:#1E293B; }
QTableWidget::item { padding:6px 8px; }
QTableWidget::item:selected { background:#DBEAFE; color:#1E40AF; }
QTableWidget::item:alternate { background:#F8FAFC; }
QHeaderView::section { background:#F8FAFC; color:#64748B; font-weight:600;
                       font-size:12px; border:none; padding:8px;
                       border-bottom:2px solid #E2E8F0; }

/* =========================================================
   日志 / 进度 / 状态栏
   ========================================================= */
QPlainTextEdit#logBox { background:#fff; color:#334155; border-radius:10px;
                        font-family:'Cascadia Code','Fira Code',Consolas,monospace;
                        font-size:11.5px; border:1px solid #E2E8F0; }

QProgressBar#progressBar { border:1px solid #CBD5E1; border-radius:8px;
                           background:#F1F5F9; text-align:center;
                           color:#ffffff; font-size:11.5px; font-weight:600;
                           min-height:22px; }
QProgressBar#progressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
    stop:0 #2563EB, stop:1 #3B82F6); border-radius:7px; }
QLabel#progressLabel { font-size:12px; color:#64748B; }

/* 状态栏基础样式；颜色由 results_panel.set_status 动态设置 */
QLabel#statusBar {
    font-size:13.5px; font-weight:600; padding:10px 14px;
    border:1px solid #E2E8F0; border-radius:10px; background:#fff;
}

/* =========================================================
   滚动条
   ========================================================= */
QScrollArea { border:none; background:transparent; }
QScrollBar:vertical { background:#F1F5F9; width:10px; border-radius:5px; }
QScrollBar::handle:vertical { background:#CBD5E1; min-height:30px; border-radius:5px; }
QScrollBar::handle:vertical:hover { background:#94A3B8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
QScrollBar:horizontal { background:#F1F5F9; height:10px; border-radius:5px; }
QScrollBar::handle:horizontal { background:#CBD5E1; min-width:30px; border-radius:5px; }
QScrollBar::handle:horizontal:hover { background:#94A3B8; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0px; }
"""
