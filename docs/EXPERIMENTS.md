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

## 2026-11-25：扩展屏移动验证

- Qt 在当前 Windows 扩展桌面中识别到 2 个显示器：主屏工作区 `(0, 0, 3200, 1904)`，扩展屏工作区 `(-443, -2160, 3840, 2088)`。
- 桌宠从主屏实际导航至扩展屏坐标 `(1326, -1266)`，最终窗口中心由 Qt 判定属于 `DISPLAY5`。
- 自动化测试覆盖负坐标、右侧扩展屏、屏幕间空隙、虚拟桌面并集和基于绝对原点的窗口边界限制。
- 移动途中使用虚拟桌面边界，避免经过非连续屏幕布局时被错误拉回主屏；最终目标、跳跃落点和气泡仍限制在对应屏幕可用工作区。

## 2026-11-25：跨屏 DPI 缩放修复

- 两块实机显示器的 Windows/Qt 缩放比均为 `2.0`。旧启动流程只启用了 Per-Monitor V2 原生 DPI awareness，却没有在创建 `QApplication` 前启用 Qt 高 DPI scaling，导致物理屏幕坐标与逻辑控件尺寸混用，跨屏后角色被裁剪。
- 在 `QApplication` 构造前启用 `AA_EnableHighDpiScaling` 和 `AA_UseHighDpiPixmaps`，确保窗口、标签、动画帧和屏幕几何统一使用 Qt 逻辑坐标，由 Qt 按目标屏 DPR 绘制。
- 首次复测发现 Windows 在 DPI 过渡时保留旧物理尺寸，使顶层窗口短暂缩为 225×225，而内部动画标签仍为 300×300；因此进一步固定窗口/标签逻辑尺寸，并在 `screenChanged` 后重新应用。
- 最终实测：扩展屏 `DISPLAY5` 上窗口 300×300、标签 300×300、DPR 2.0，窗口抓图 600×600，角色完整且无裁剪。
- 上述 300×300 是逻辑尺寸，在 DPR 2.0 屏幕上会形成 600×600 物理尺寸，较原角色视觉大小放大一倍。后续改为以 300×300 **物理像素**为目标：窗口逻辑尺寸按 `300 / DPR` 动态计算，动画源帧仍保持 300×300 以避免清晰度损失。
- 清晰度复验发现 idle 动画仍由 `QMovie`、其他动作由预渲染帧显示，造成两套 DPI 缩放路径。现已统一为 PIL/LANCZOS 单次生成 300×300 物理帧，并在显示副本上设置目标屏 DPR，避免 QLabel 二次缩放。原始 GIF 未修改。
- 气泡与菜单的字体、边框、圆角、padding 和间距改为按物理像素目标除以 DPR；气泡增加物理宽度上限和跨屏后重新排版。
- `DISPLAY5` 实测抓图：宠物 300×300 物理像素、Pixmap DPR 2.0；气泡约 260×96 物理像素且文本完整；菜单约 296×400 物理像素且条目完整。

## 2026-11-25：多屏渲染与运动逻辑收敛

- 上述逐步 DPI 修复仍同时保留了 Windows 物理坐标、Qt 逻辑坐标和动态 DPR 尺寸三套概念，并在 `screenChanged` 回调中执行 resize、move 和动画重启；屏幕边界附近可能形成反馈循环，引发双屏残影/闪烁。
- 最终方案统一为 Per-Monitor V2 下的原生 Windows 物理像素坐标；移除 Qt 高 DPI scaling、动态 DPR resize 和 `screenChanged` 运动副作用。宠物、气泡、菜单以及三个子窗口均恢复原物理尺寸，Win32/截图诊断坐标也无需二次换算。
- 随机移动、跳跃和惯性动画不再仅共享 `is_moving` 布尔值；每项运动持有递增任务令牌和明确模式。拖拽或新运动会使旧回调永久失效，防止旧随机移动在惯性开始后复活并争抢坐标。
- 实机复验：Qt 只存在 1 个 `PetWindow`；跨到 `DISPLAY5` 后无双屏副本；惯性结束后连续 1 秒坐标保持 `(1596, -392)` 不变。
- “和我对话 / 检查代码 / 设置”窗口恢复为 580×500、750×700、540×650 物理像素。
- 气泡改为自绘云朵轮廓，背景色和边框色随情绪变化，文字色固定；50ms 定时器只创建一次，并以 ±3px 正弦曲线轻微上下浮动。
- 中文长文本不再依赖 `QLabel.adjustSize()`；改用 `QFontMetrics.boundingRect` 按 420px 最大文本宽度精确计算换行后的宽高，并在云朵内部预留 50px/28px 安全边距。扩展屏与主屏实测文本均完全位于窗口内。
- 气泡跟随坐标改为直接读取桌宠窗口的实时 `x()/y()`；扩展屏拉回主屏后，气泡中心与桌宠中心偏差实测为 0px。
- 运动模式期间 `_set_state` 只接受对应的行走/跳跃动画状态；发言和情绪变化仍可改变气泡配色，但不能中断运动动画。实测移动中触发开心发言后仍保持 `walking_right`。

## 2026-11-25：跨屏气泡复测与鼠标陪伴

- 真实双屏复测复现了扩展屏截字：主屏顶层气泡为 `560×182`，跨到 `DISPLAY5` 后被 DPI 过渡缩成 `420×137`，内部标签仍为 `420×110`，证明根因是跨屏 `setGeometry` 同时移动和缩放，而非素材或字体损坏。
- 气泡改为先移动顶层窗口，再在 `WM_DPICHANGED` 处理后重申目标尺寸；文字按最终标签宽度测量，避免“按 420px 测量后又缩窄标签”导致的二次换行。
- 修复后真实两屏结果：`DISPLAY1` 与 `DISPLAY5` 的气泡均为 `560×182`，标签均为 `(70, 36, 420, 110)`，标签矩形完整位于云朵窗口内。
- 新增非侵入式鼠标观察：仅桌面空白左键按下可成为显式目标，不消费应用点击；鼠标静止 12 秒后可触发陪伴，30 秒冷却。
- 鼠标目标复用运动令牌，诊断、拖拽和模态窗口优先；到达后 6–11 秒随机留在原处或开始新的随机活动。
- 自动化测试结果：`38 passed`；新增覆盖诊断/拖拽优先级、显式目标与静止吸引的抢占规则、陈旧到达令牌、气泡测量宽度一致性和单实例入口。
- 构建前发现系统中同时运行两个路径完全相同的旧版 `dist\DebugPet.exe` 进程，这与“双屏同时出现并闪烁”的现象一致；主程序新增跨进程 `QLockFile`，第二次启动会在创建窗口前退出。
- PyInstaller 重新构建成功，`dist\DebugPet.exe` 为 82,736,627 字节；offscreen 首实例运行并生成 IPC endpoint，第二实例以退出码 0 立即退出，首实例保持运行。

## 2026-11-24：VSCode UI Automation 可行性探针

- 环境：Windows UI Automation backend（pywinauto 0.6.9）。
- 探针识别到两扇标题包含 Visual Studio Code 的窗口。
- 两扇窗口的 UIA rectangle 均返回 `[0, 0, 0, 0]`。
- 未发现 Document、Edit 或 Text 子控件。
- 结论：当前环境无法可靠获得编辑器文本 range 的屏幕矩形，不能宣称精确定位可用。
- 已采用降级方案：VSCode 扩展负责原生 diagnostic range 装饰；桌宠通过 Win32 顶层窗口矩形移动到 VSCode 窗口边缘。若 Win32 也无法定位，则只显示人格化气泡，不强制移动。
