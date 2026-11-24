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

## 2026-11-24：VSCode UI Automation 可行性探针

- 环境：Windows UI Automation backend（pywinauto 0.6.9）。
- 探针识别到两扇标题包含 Visual Studio Code 的窗口。
- 两扇窗口的 UIA rectangle 均返回 `[0, 0, 0, 0]`。
- 未发现 Document、Edit 或 Text 子控件。
- 结论：当前环境无法可靠获得编辑器文本 range 的屏幕矩形，不能宣称精确定位可用。
- 已采用降级方案：VSCode 扩展负责原生 diagnostic range 装饰；桌宠通过 Win32 顶层窗口矩形移动到 VSCode 窗口边缘。若 Win32 也无法定位，则只显示人格化气泡，不强制移动。
