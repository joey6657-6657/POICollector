"""从 assets/logo.svg 或 assets/logo.png 生成 Windows 多尺寸高清 ICO。

Windows 桌面/任务栏/标题栏会按 DPI 和显示尺寸自动挑选 ICO 里合适的帧。
本脚本优先读取 assets/logo.svg（真矢量）并用 PyQt6 渲染为高清位图，
 fallback 到 assets/logo.png；最终生成 16/24/32/48/64/128/256 七个尺寸，
并全部使用 BMP 位图帧（非 PNG 压缩），以最大限度兼容 Windows 资源管理器。

用法（在项目根目录执行）：
    venv\\Scripts\\python.exe tools\\build_icon.py
"""
from __future__ import annotations

import os
import sys

from PIL import Image

# 需要 PyQt6 来渲染真矢量 SVG；项目 venv 已安装 PyQt6
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
FRAMES_DIR = os.path.join(ASSETS_DIR, "ico_frames")
SVG_SOURCE = os.path.join(ASSETS_DIR, "logo.svg")
PNG_SOURCE = os.path.join(ASSETS_DIR, "logo.png")
TARGET_PNG = os.path.join(ASSETS_DIR, "logo.png")
TARGET_ICO = os.path.join(ASSETS_DIR, "logo.ico")

# Windows 图标常用尺寸，覆盖 100% ~ 200% DPI 下的常见显示大小
SIZES = [16, 24, 32, 48, 64, 128, 256]
# 矢量渲染目标分辨率，必须 >=256 才能保证 256 帧清晰
RENDER_SIZE = 1024


def _render_svg_to_png(svg_path: str, png_path: str, size: int = RENDER_SIZE) -> None:
    """用 PyQt6 将 SVG 渲染为指定尺寸的透明 PNG。"""
    app = QApplication(sys.argv)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    renderer = QSvgRenderer(svg_path)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    if pixmap.isNull() or pixmap.width() == 0:
        raise RuntimeError(f"SVG 渲染失败：{svg_path}")
    pixmap.save(png_path, "PNG")
    # 立即退出事件循环，避免脚本 hang 住
    app.quit()


def _find_source() -> tuple[str, bool]:
    """返回 (source_path, is_svg)。"""
    if os.path.exists(SVG_SOURCE):
        return SVG_SOURCE, True
    if os.path.exists(PNG_SOURCE):
        return PNG_SOURCE, False
    raise FileNotFoundError(f"找不到源图片：{SVG_SOURCE} 或 {PNG_SOURCE}")


def build_icon() -> None:
    os.makedirs(FRAMES_DIR, exist_ok=True)

    source_path, is_svg = _find_source()
    print(f"源文件：{source_path}")

    if is_svg:
        # 将 SVG 渲染为高清 PNG，同时作为软件内显示用图
        _render_svg_to_png(source_path, TARGET_PNG, RENDER_SIZE)
        png_path = TARGET_PNG
    else:
        png_path = source_path

    # 读取源图并转换为 RGBA，确保缩放时保留透明通道
    source = Image.open(png_path).convert("RGBA")
    if source.width != source.height:
        print(f"警告：源图片非正方形（{source.width}x{source.height}），将按短边居中裁剪。", file=sys.stderr)
        side = min(source.width, source.height)
        left = (source.width - side) // 2
        top = (source.height - side) // 2
        source = source.crop((left, top, left + side, top + side))

    frames: list[Image.Image] = []
    for size in SIZES:
        frame = source.resize((size, size), Image.Resampling.LANCZOS)
        frames.append(frame)
        frame_path = os.path.join(FRAMES_DIR, f"frame_{size}x{size}.png")
        frame.save(frame_path, format="PNG")

    # Pillow 的 ICO 保存有一个隐式过滤：它会用首帧的 size 判断后续尺寸是否"超出原图"，
    # 导致大帧被丢弃。 workaround：将最大帧（256）放到第一位，其余 append。
    frames_sorted = sorted(frames, key=lambda f: f.size[0], reverse=True)
    frames_sorted[0].save(
        TARGET_ICO,
        format="ICO",
        append_images=frames_sorted[1:],
        bitmap_format="bmp",
    )

    print(f"已生成：{TARGET_PNG}（{RENDER_SIZE}x{RENDER_SIZE}）")
    print(f"已生成：{TARGET_ICO}")
    print(f"包含尺寸：{SIZES}")
    print(f"单帧预览保存在：{FRAMES_DIR}")


if __name__ == "__main__":
    build_icon()
