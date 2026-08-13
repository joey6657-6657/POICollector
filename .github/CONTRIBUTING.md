# 贡献指南

感谢你关注 POICollector。提交 Issue 或代码前，请先阅读以下约定。

## 提交问题

- 使用 GitHub Issue 模板，写明操作系统、软件版本、复现步骤、预期结果与实际结果。
- 请勿在截图、日志或 Issue 中粘贴 API Key、个人路径、联系电话、精确住址或其他敏感信息。
- 涉及高德接口的反馈，请用脱敏后的错误码和响应摘要说明问题。

## 提交代码

1. 从 `main` 创建分支。
2. 保持改动聚焦，并为新增核心逻辑补充或更新 `tests/` 中的离线测试。
3. 在提交前执行：

   ```powershell
   venv\Scripts\python.exe -m pytest -q
   venv\Scripts\python.exe -m compileall -q run.py poi_collector tests
   ```

4. 不提交 `output/`、`checkpoints/`、本地配置、API Key、可执行文件或个人过程记录。
5. 不引入 GPL / AGPL 依赖；新增第三方代码或数据时，须在 `README.md` 的「致谢与第三方说明」中说明来源和许可证。

## 开发环境

- Windows 10 / 11 x64
- Python 3.13
- 运行程序：`venv\Scripts\python.exe -m pip install -r requirements.txt`
- 参与开发或运行测试：`venv\Scripts\python.exe -m pip install -r requirements-dev.txt`

`requirements-lock.txt` 记录了 v1.0.0 已验证的完整环境；只有在有意升级依赖并重新验证后才更新它。
