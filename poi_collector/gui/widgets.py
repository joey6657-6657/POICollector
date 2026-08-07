"""可复用小组件：POI 类型多选树（读取 data/poi_types.json，支持大类/中类/小类三级）。

层级由 poi_types.json 的 name 字段中的 " > " 分隔符推导：
  - 大类：name 不含 " > "（如 "汽车服务"）
  - 中类：含 1 个分隔（如 "汽车服务 > 加油站"）
  - 小类：含 2 个分隔（如 "汽车服务 > 加油站 > 中国石化"）

勾选语义：勾选大类即表示该大类编码（覆盖其全部子类），无需再勾子类；
若一个大类仅部分子类被勾选，父节点显示半选，导出时只列出被勾中的具体编码。
"""
import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QAbstractItemView)

_HERE = os.path.dirname(os.path.abspath(__file__))
_TYPES_PATH = os.path.normpath(os.path.join(_HERE, "..", "data", "poi_types.json"))


class PoiTypeList(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setMinimumHeight(160)
        self.setMaximumHeight(240)
        self.setColumnCount(1)
        self.setAnimated(True)
        self._updating = False
        self.itemChanged.connect(self._on_item_changed)
        # 强制分支箭头为深色（Fusion 样式默认可能画白色箭头）
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Text, QColor("#374151"))
        self.setPalette(pal)
        self._load_types()

    def _load_types(self):
        try:
            with open(_TYPES_PATH, "r", encoding="utf-8") as f:
                types = json.load(f)
        except (OSError, ValueError):
            types = []
        top = {}   # 大类名 -> QTreeWidgetItem
        mid = {}   # (大类名, 中类名) -> QTreeWidgetItem
        for t in types:
            name = t.get("name", "")
            code = t.get("code", "")
            parts = [p.strip() for p in name.split(">")]
            if len(parts) == 1:
                item = QTreeWidgetItem(self, [parts[0]])
                item.setData(0, Qt.ItemDataRole.UserRole, code)
                self._make_checkable(item)
                top[parts[0]] = item
            elif len(parts) == 2:
                parent = top.get(parts[0])
                if parent is None:
                    parent = QTreeWidgetItem(self, [parts[0]])
                    top[parts[0]] = parent
                item = QTreeWidgetItem(parent, [parts[1]])
                item.setData(0, Qt.ItemDataRole.UserRole, code)
                self._make_checkable(item)
                mid[(parts[0], parts[1])] = item
            else:
                key = (parts[0], parts[1])
                parent = mid.get(key)
                if parent is None:
                    p0 = top.get(parts[0])
                    if p0 is None:
                        p0 = QTreeWidgetItem(self, [parts[0]])
                        top[parts[0]] = p0
                    parent = QTreeWidgetItem(p0, [parts[1]])
                    mid[key] = parent
                item = QTreeWidgetItem(parent, [parts[2]])
                item.setData(0, Qt.ItemDataRole.UserRole, code)
                self._make_checkable(item)
        # 默认折叠，仅显示大类
        for i in range(self.topLevelItemCount()):
            self.collapseItem(self.topLevelItem(i))

    def _make_checkable(self, item):
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Unchecked)

    def _set_children(self, item, state):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._set_children(child, state)

    def _refresh_ancestors(self, item):
        parent = item.parent()
        if parent is None:
            return
        n = parent.childCount()
        checked = unchecked = 0
        for i in range(n):
            cs = parent.child(i).checkState(0)
            if cs == Qt.CheckState.Checked:
                checked += 1
            elif cs == Qt.CheckState.Unchecked:
                unchecked += 1
        if checked == n:
            new = Qt.CheckState.Checked
        elif unchecked == n:
            new = Qt.CheckState.Unchecked
        else:
            new = Qt.CheckState.PartiallyChecked
        if parent.checkState(0) != new:
            self._updating = True
            parent.setCheckState(0, new)
            self._updating = False
            self._refresh_ancestors(parent)

    def _on_item_changed(self, item, column):
        if self._updating:
            return
        self._updating = True
        state = item.checkState(0)
        self._set_children(item, state)
        self._updating = False
        self._refresh_ancestors(item)

    def selected_codes(self):
        """返回勾选的类型编码列表。

        大类被勾选（Checked）即取其编码并覆盖整棵子树；父类半选（PartiallyChecked）
        或本身无编码时递归收集被勾中的子节点编码。
        """
        codes = []

        def walk(item):
            cs = item.checkState(0)
            if cs == Qt.CheckState.Unchecked:
                return
            code = item.data(0, Qt.ItemDataRole.UserRole)
            if cs == Qt.CheckState.Checked and code:
                codes.append(code)
                return  # 已覆盖子树，无需再列子类
            for i in range(item.childCount()):
                walk(item.child(i))

        for i in range(self.topLevelItemCount()):
            walk(self.topLevelItem(i))
        return codes

    def set_checked_codes(self, codes):
        """按编码集合还原勾选状态（用于加载配置）。"""
        codes = set(codes or [])

        def walk(item):
            code = item.data(0, Qt.ItemDataRole.UserRole)
            item.setCheckState(
                0, Qt.CheckState.Checked if code in codes else Qt.CheckState.Unchecked)
            for i in range(item.childCount()):
                walk(item.child(i))

        self._updating = True
        for i in range(self.topLevelItemCount()):
            walk(self.topLevelItem(i))
        self._updating = False
