# v1.0.0 发布检查清单

每次创建 GitHub Release 前，从干净工作区完成以下检查。

## 代码与测试

- [ ] `git status --short` 没有意外改动。
- [ ] `venv\Scripts\python.exe -m pip install -r requirements-dev.txt` 成功。
- [ ] `venv\Scripts\python.exe -m pytest -q` 全部通过。
- [ ] `venv\Scripts\python.exe -m compileall -q run.py poi_collector tests` 成功。
- [ ] 未追踪或暂存 API Key、个人配置、`output/`、`checkpoints/`、EXE 或过程记录。

## EXE

- [ ] 从项目根目录执行 `venv\Scripts\pyinstaller.exe POICollector.spec --noconfirm`。
- [ ] 在新的 Windows 用户环境或另一台 Windows 电脑启动 `dist\POICollector.exe`。
- [ ] 使用自己的 Key 完成一次小范围查询与 CSV、Excel 导出。
- [ ] 确认 API Key 不会写入仓库、默认配置或日志附件。
- [ ] 将最终 EXE 的 SHA-256 写入 Release 说明。

## 文档与许可证

- [ ] `README.md` 的版本、下载说明、项目结构与实际一致。
- [ ] `README.md`（含第三方声明）、`README_EN.md`、`LICENSE` 和 `LICENSES/` 已随源码仓库提供；若单独分发 EXE，请按各依赖的许可证要求一并提供所需通知材料。
- [ ] 如需提供带说明材料的归档包，可用 `tools/package_release.ps1` 生成并核对 ZIP 内容。
- [ ] `docs/CHANGELOG.md` 写明本次面向用户的变更。
- [ ] `v1.0.0` 标签指向本次已验证的提交。

## GitHub

- [ ] CI 最近一次运行通过。
- [ ] Dependabot alerts 已启用。
- [ ] CodeQL 最近一次扫描完成；若有警告，已评估或修复。
- [ ] 创建 Release 后再上传 EXE；不要将 EXE 提交进 Git。
