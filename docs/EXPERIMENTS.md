# 实验与测试记录

## 2026-11-24：Windows 环境与基线

- 删除从 WSL 搬运后失效的 `venv/`；保留 Windows 项目环境 `.venv/`。
- `.venv` 基于 Windows Python 3.12.10。
- 安装 Pillow、requests、pyflakes、PyQt5 后，`pip check` 无冲突。
- PyQt5、Pillow、requests、pyflakes 导入成功。
- `debug_pet_pyqt.py`、`debug_pet.py`、`run.py`、`build.py` 语法编译通过。
- pyflakes 基线存在未使用导入/变量和无占位符 f-string；未将其误报为环境失败。

## 2026-11-24：构建审计

- 旧脚本依赖本机绝对路径，判定为不可复现。
- 已改为当前解释器执行 `python -m PyInstaller DebugPet.spec`。
- 使用 Python 3.12.10、PyInstaller 6.22.3 实际构建成功，产物为 `dist/DebugPet.exe`。
- 打包产物 offscreen 启动后保持运行并生成有效 IPC endpoint，冒烟测试通过。
- `collect_all(PyQt5)` 收集了未使用的 3D/Web/SQL 插件并产生缺失可选 DLL 警告；不影响本次启动，但构建体积和依赖收集仍需优化。

## 已知问题

- 主文件历史注释和部分 UI 文本存在编码乱码。
- 多显示器移动、UI Automation 和 VSCode IPC 尚未验证。
- Windows 凭据后端需在安装 keyring 后做真实读写与删除测试。

## 2026-11-24：IPC 与诊断管线

- 认证 loopback TCP 端到端测试通过：扩展协议格式的 JSON 事件被 Qt 服务接收。
- 单元测试覆盖诊断去重、5 秒冷却、严重等级筛选、文档版本拒绝和消失事件。
- 当前自动化测试结果：7 passed。
- TypeScript 扩展使用 TypeScript 5.9.3 编译通过。
- 真实 DebugPet 主程序 offscreen 启动后，本机合成诊断事件已成功发送到随机 loopback 端口。
- 当前自动化测试结果已更新为：8 passed。
- 尚未在 VSCode Extension Host 中安装并手动触发真实诊断；因此 V0.2 仍为“进行中”。

## 2026-11-24：配置与凭据

- Windows Credential Manager 临时凭据写入、读取、删除 round-trip 通过。
- 非敏感 JSON 配置 round-trip 测试通过，确认不写入 `api_key` 字段。
- AI 代码分析增加独立 `allow_code_upload=false` 默认值；未授权时只执行本地检查。

## 2026-11-24：SQLite 持久化记忆

- SQLite 使用 WAL、busy timeout 和每操作独立连接，适合 QThread 并发调用。
- 关闭并新建 service 实例后，user/assistant 消息、session、角色和时间戳恢复测试通过。
- 角色隔离、软删除后检索/注入排除、关闭记忆、上下文预算测试通过。
- FTS5 在当前 Python 3.12.10 可用；实测中文子串可能无命中，已增加“FTS 无结果即 LIKE”的运行时降级。
- 40 条长对话触发抽取式摘要；每段包含 `[source:id]`，测试确认 source ID 全部可追溯。
- ChatDialog offscreen 初始化并异步恢复记忆通过。
- 2026-11-25 首个 GLM Key 请求结果为 HTTP 401，未误报为通过。
- 更换有效凭据后，`glm-4-flash` 完成两次真实请求：第一会话保存合成代号，重新创建 SQLite 服务并开启第二会话后正确回答该代号，`cross_session_memory=True`。
- API Key 仅写入 Windows Credential Manager；测试脚本不输出密钥，临时 SQLite 库不进入正式记忆库。

## 2026-11-24：真实 VSCode Extension Host 联调

- VSCode 1.143.1，扩展 `debugpet-local.debugpet-vscode@0.2.0` 构建并安装成功。
- 扩展日志确认多个随机 IPC 端口变化；断线期间事件保持队列，发现新 endpoint 后收到 ACK。
- 使用真实 JavaScript 语法错误测试新增、重复、修改和消失事件。
- 初次屏幕矩形截图在多窗口遮挡下捕获了错误窗口；按 HWND PrintWindow 对 Electron 返回全黑画面，均记录为失败方案。
- 最终精确方案要求目标 VSCode 窗口已在前台，用文档标题匹配 HWND 后截取真实屏幕区域，检测 `#ff00fe` decoration。
- 真实定位坐标为 `(694, 343)` 与 `(710, 343)`；桌宠抵达后才报告第 2 行第 21/22 列。
- 修改错误时旧 removed 与新 diagnostic 紧邻，最初造成误庆祝；加入 500ms 确认窗口后验证不再误庆祝。
- 修复成合法代码后真实触发一次 CELEBRATE。
- 切换到 Untitled 编辑器后真实收到 active=false，日志为 `NAV cancelled: editor-switched`。
- 当前自动化测试：22 passed；TypeScript 编译通过。

## 2026-11-25：发布构建复验

- 使用仓库目录内的便携 Python 3.12.10 重建全新 `.venv`，没有修改系统 PATH，也不复用其他项目依赖。
- PyInstaller 6.22.3 重新构建 `dist/DebugPet.exe` 成功；可选 Qt 3D/Web/SQL 插件仍有缺失 DLL 警告，但主程序未引用这些插件。
- 新产物以 `QT_QPA_PLATFORM=offscreen` 隐藏启动 8 秒，进程保持运行并生成 IPC endpoint；随后仅结束测试进程并清理 endpoint。
- SQLite 连接增加显式关闭；新增 Windows 可删除数据库目录的回归测试，避免临时库或正式库句柄泄漏。

## 2026-11-24：VSCode UI Automation 可行性探针

- 环境：Windows UI Automation backend（pywinauto 0.6.9）。
- 探针识别到两扇标题包含 Visual Studio Code 的窗口。
- 两扇窗口的 UIA rectangle 均返回 `[0, 0, 0, 0]`。
- 未发现 Document、Edit 或 Text 子控件。
- 结论：当前环境无法可靠获得编辑器文本 range 的屏幕矩形，不能宣称精确定位可用。
- 已采用降级方案：VSCode 扩展负责原生 diagnostic range 装饰；桌宠通过 Win32 顶层窗口矩形移动到 VSCode 窗口边缘。若 Win32 也无法定位，则只显示人格化气泡，不强制移动。
