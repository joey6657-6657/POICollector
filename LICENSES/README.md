# 第三方许可证材料

发布源码或 Windows EXE 时，请将本目录随发行物一同提供。

- `MIT-wandergis-coordTransform_py.txt`：本项目 `coord_transform.py` 所改编代码的 MIT 许可证。
- `LGPL-3.0.txt`：PySide6 / Qt 采用 LGPL 路径时应提供的 LGPL-3.0 完整文本。
- `GPL-3.0.txt`：LGPL-3.0 所引用的 GPL-3.0 完整文本。

发行 EXE 时还应使用 PyInstaller 的 `--collect-data` / `--add-data` 机制或发行 ZIP，向用户提供各运行时组件要求的许可文本。`tools/package_release.ps1` 会把当前构建的 EXE 与本目录、`LICENSE`、`THIRD-PARTY.md` 一起收进 ZIP；它不替代对依赖许可义务的逐项核验。

其他 Python 依赖的版本见 `requirements-lock.txt`，其各自的许可证仍由相应权利人管理。本项目自身代码采用根目录 `LICENSE` 中的 MIT License；高德 POI 分类数据和 API 内容不因本项目的 MIT 许可证而被重新授权。
