"""最近使用的 ArcGIS 工程文件管理（持久化到 config/recent_projects.yaml）。

按钮 B 需要知道"用户想添加到哪个工程文件"——这个路径必须由用户给，
本模块负责：记住上次路径 + 维护最近使用列表（最多 5 个），并在用户
没有提供路径时给出默认推荐（上次路径目录 / Pro 当前工程 / 桌面 / 文档）。
"""
import os
import sys

import yaml

# 最近列表最多保留条数
_MAX_RECENT = 5

# 配置文件路径：<repo>/config/recent_projects.yaml
# PyInstaller --onefile 兼容：用 sys.executable 目录而非 __file__
if getattr(sys, 'frozen', False):
    _ROOT = os.path.dirname(sys.executable)
else:
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_ROOT, "config", "recent_projects.yaml")


def _load():
    """读取最近工程列表（返回 list[str]，按最近在前）。"""
    if not os.path.exists(_CONFIG_PATH):
        return []
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        recent = data.get("recent", [])
        return [p for p in recent if isinstance(p, str) and os.path.exists(p)]
    except Exception:
        return []


def _save(recent):
    try:
        os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump({"recent": recent}, f, allow_unicode=True)
    except Exception:
        pass


def add(path):
    """把一个工程路径加入最近列表（去重 + 置顶 + 截断）。"""
    if not path:
        return
    recent = _load()
    recent = [p for p in recent if p != path]
    recent.insert(0, path)
    _save(recent[:_MAX_RECENT])


def list_recent():
    """返回最近使用的工程路径列表（已过滤不存在的）。"""
    return _load()


def last_dir():
    """返回上次使用路径所在的目录（用于对话框默认打开位置）。"""
    recent = _load()
    if recent:
        return os.path.dirname(recent[0])
    return ""


def suggest_default_dir():
    """智能猜测默认目录：
        1) 上次路径所在目录
        2) 桌面
        3) 文档
        4) 空（系统默认）
    """
    d = last_dir()
    if d and os.path.isdir(d):
        return d
    # 桌面
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.isdir(desktop):
        return desktop
    # 文档
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    if os.path.isdir(docs):
        return docs
    return ""
