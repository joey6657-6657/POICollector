"""入口：以脚本方式启动 PyQt6 桌面应用。

用法：
    python run.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QColor, QPalette
from poi_collector.gui.main_window import MainWindow


def _apply_light_palette(app):
    """强制浅色调色板：不同 Windows 主题（深色/浅色）下界面颜色保持一致。"""
    pal = QPalette()
    # 窗口/控件底色
    pal.setColor(QPalette.ColorRole.Window, QColor("#f6f7fb"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#1f2937"))
    pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#f9fafb"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#1f2937"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#f3f4f6"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#1f2937"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor("#1f2937"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#1B60A1"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#9ca3af"))
    pal.setColor(QPalette.ColorRole.Link, QColor("#1B60A1"))
    # 禁用态文字（在深色主题下避免变成白色看不清）
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#9ca3af"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#9ca3af"))
    pal.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#9ca3af"))
    app.setPalette(pal)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    _apply_light_palette(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
