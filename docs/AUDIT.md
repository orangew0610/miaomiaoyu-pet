# DebugPet 2.0 现状审计

审计基线：`ee40d7a`，审计日期：2026-11-24。

## 入口与架构

- `debug_pet_pyqt.py` 是当前主程序，UI、动画、移动、配置、静态检查、模型请求和聊天全部集中在单文件中。
- `debug_pet.py` 是较早的 Tkinter 实现，仍保留但不是 README 的默认入口。
- `run.py` 会在每次启动时安装依赖，并通过字符串 `python` 启动程序；不适合隔离环境，暂不作为推荐入口。
- 三套角色素材目录都存在，但 PyQt 主程序和构建配置当前只使用 `miaomiao-all-actions`。

## 动画状态机与移动

- 状态包括 idle、左右 walking、左右 jumping、thinking、happy、sad、waiting、failed。
- idle 使用 `QMovie`，部分其他状态预解码为 `QPixmap` 帧并由 100ms `QTimer` 驱动。
- 随机行为每 5–15 秒调度一次；移动每 30ms 递归 `singleShot`，速度按向量归一化。
- 坐标限制只使用 `QApplication.primaryScreen()`，多显示器和负坐标尚未处理。
- 目标移动能力已经存在，可复用于诊断定位；目前目标仅随机生成。
- 方向素材映射存在历史命名反转，变更前必须做视觉回归。

## 聊天与模型 API

- 当前用户消息先加入 `message_history`，请求体又追加同一消息，导致重复。
- 聊天和 AI 代码检查均在 UI 线程同步调用 `requests.post(timeout=30)`，会冻结动画。
- Chat、CodeChecker、Settings 各自复制配置读取逻辑，默认 provider/model/url 也不完全一致。
- 模型名硬编码，不能从设置界面自定义。
- API 密钥明文写入工作目录 `.debug_pet_settings`；文件虽被 Git 忽略，但不符合安全凭据要求。
- 对话 HTML 未转义用户或模型文本，后续需要修复显示注入风险。
- AI 代码分析会发送完整代码；缺少单独、明确的上传授权开关。

## 代码检查

- 本地 Python 检查使用临时文件和 pyflakes，可在不上传代码的情况下运行。
- AI 检查与本地检查耦合在对话框内，错误结构没有稳定的数据模型。
- 当前高亮仅存在于代码检查窗口，尚未与 VSCode 编辑器选择区联动。

## IPC 与 VSCode

- 导入了 `QLocalSocket`/`QLocalServer`，但未实现服务端协议。
- 仓库内没有 VSCode 扩展或诊断事件 schema。
- 需要定义版本化协议、实例鉴权、消息大小限制和断线重连策略。

## 配置、隐私与记忆

- 1.x 设置依赖当前工作目录，打包后从不同目录启动会读写不同配置。
- 默认是否上传代码没有独立配置，不能满足“默认不上传”。
- 第二阶段已实现 SQLite 持久化记忆：真实 user/assistant 消息、UTC 时间戳、角色 ID、会话 ID、类型和事实来源。
- 已实现 short_term、episodic、preference、summary 四类；偏好和情景记忆只由用户显式管理，不自动推断。
- FTS5 检索已启用；中文子串或 FTS 无结果时降级到参数化 LIKE。
- 摘要采用抽取式原文切片并保存 source ID，不调用模型编造摘要。
- 数据库与模型请求均通过工作线程执行；ChatDialog 初始化也异步恢复历史。
- API Key 和 diagnostic code 字段不写入记忆库；聊天中用户主动发送的文本按真实用户消息保存。

## 构建流程

- 旧 `build.py` 硬编码用户目录中的 PyInstaller。
- 旧 spec 硬编码 `D:\Desktop\debugger`，无法在其他机器复现。
- README 缺少环境、测试和打包说明。
- 当前没有自动化测试。

## 资源解耦

- `GIF_DIR` 和 `GIF_FILES` 是全局常量，角色、动作映射、提示词尚未形成 manifest。
- 三套素材说明项目已有多角色基础，但当前没有角色选择、校验和用户资源目录。

## 高风险项

1. UI 线程网络阻塞。
2. 明文密钥和默认代码上传语义不清。
3. 单文件耦合导致改动容易破坏动画与拖拽。
4. Windows UI Automation 在当前 VSCode/Electron 环境仍不暴露文本范围；精确定位改用 decoration + 前台窗口截图。被遮挡窗口不截图、不抢焦点。
5. 当前源码中有较多历史乱码显示；修复时要避免一次性重写造成行为回归。

## 第二阶段定位结论

- VSCode Extension Host 真实激活和诊断事件已经联调。
- 精确路径：活动且可见 range → 洋红 decoration → 文档标题匹配 HWND → 前台窗口截图 → 确定性颜色聚类 → 屏幕坐标。
- DPI：主进程启用 Per-Monitor-V2；真实 200% 缩放环境下完成字段定位和导航。
- 多窗口：按 `document_name` 匹配窗口；目标窗口被其他窗口遮挡时不使用错误截图。
- 降级：前台窗口中找不到 decoration 时移动到明确标记为 `precise=False` 的窗口边缘；后台窗口则不导航。
