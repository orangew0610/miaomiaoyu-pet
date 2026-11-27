# DebugPet

DebugPet 是一个基于 PyQt5 的 Windows 桌面宠物。当前 `feature/debugpet-v2` 分支用于开发 DebugPet 2.0：VSCode 环境感知、主动 Debug、人格化对话和持久化记忆。

## Windows 开发环境

项目使用仓库内的 `.venv` 隔离依赖，不会修改其他 Python 项目的包。

```powershell
# 首次创建环境（已创建时无需重复执行）
# 本机已安装 Python 3.12 时
python -m venv .venv

# 或使用仓库目录内的便携解释器（本开发环境采用此方式）
.\.python\tools\python.exe -m venv .venv

# 激活环境并安装依赖
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

如果 PowerShell 禁止执行激活脚本，可以直接使用虚拟环境解释器：

```powershell
.\.venv\Scripts\python.exe debug_pet_pyqt.py
```

正常启动：

```powershell
.\.venv\Scripts\Activate.ps1
python debug_pet_pyqt.py
```

### 多显示器

桌宠支持 Windows“扩展这些显示器”模式，包括位于主屏左侧、右侧或上方的负坐标屏幕。随机活动会从所有显示器选择目标；拖拽、跳跃、抛物线、气泡和 VSCode 诊断导航均使用虚拟桌面坐标。显示器排列或工作区变化会在下一次移动时重新读取，无需在配置中写死分辨率。

### 鼠标目标与陪伴

- 单击桌面空白区域可把该位置指定为移动目标；普通应用窗口、桌面图标和桌宠自身的点击保持原有功能。
- 鼠标连续约 12 秒不动时，空闲桌宠可能主动靠近；同类触发至少间隔 30 秒。
- 抵达后桌宠会停留片刻，并随机选择继续陪伴或自行离开。
- VSCode 诊断导航、用户拖拽和模态对话框优先，鼠标陪伴不会抢占这些状态。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m py_compile debug_pet_pyqt.py debug_pet.py run.py build.py
```

## Windows 打包

打包脚本只使用当前虚拟环境中的 PyInstaller，不依赖开发机绝对路径。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe build.py
```

产物位于 `dist\DebugPet.exe`。角色动画和 `yu.md` 会一并打入程序。

也可以直接使用 spec 文件：

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm DebugPet.spec
```

## VSCode 扩展（DebugPet 2.0）

扩展位于 `vscode-extension/`：

```powershell
cd vscode-extension
npm.cmd install
npm.cmd run compile
```

当前源码和协议已建立，但在 Extension Host 完成真实诊断验收前仍视为开发版本。

安装本地 VSIX：

```powershell
cd vscode-extension
npm.cmd exec vsce package -- --out debugpet-vscode-0.2.0.vsix
code.cmd --install-extension .\debugpet-vscode-0.2.0.vsix --force
```

扩展默认只发送诊断元数据。只有活动编辑器中可见的错误会触发主动定位；隐藏或后台窗口中的错误不会抢焦点。定位使用临时洋红 decoration 与本地截图颜色检测，不调用视觉模型。

## 持久化记忆

- SQLite 数据库位于当前用户的 `%APPDATA%\DebugPet\memory.sqlite3`。
- Enter 和“发送”进行普通对话，消息会自动保存到当前对话存档，不会为每句话新建存档。
- 右上角“新建对话”是唯一创建新存档和新上下文的入口；关闭并重开聊天会继续最近的存档。
- “🧠 记忆”可查看对话存档数量，并可查看、编辑、删除、清空或关闭长期记忆。
- “新增长期记忆”统一入口可选择“偏好/习惯”或“经历/事件”；两类数据仍按角色 ID 隔离。
- 当前存档中的对话会在关闭窗口或重启后自动恢复。
- FTS5 无结果或不可用时自动回退到参数化 LIKE 检索。
- 长对话摘要是带 `[source:id]` 的抽取式摘录，不生成不存在的经历。
- 删除记忆后，该条目不会再进入后续模型上下文。

## 待办与提醒

- 右键桌宠选择“待办与提醒”，可新增、编辑、完成、暂停或删除提醒。
- 支持单次、每天、工作日、周末、每周、每月、每年及自定义星期重复。
- 单次提醒使用明确日期；重复提醒使用“开始日期 + 时间 + 重复规则”，列表中的“下次提醒”会随触发自动更新。
- 提醒使用本地确定性调度，不依赖大模型，不发送到外部 API。
- 数据位于 `%APPDATA%\DebugPet\reminders.sqlite3`。桌宠必须正在运行才能弹出提醒；关闭期间错过的任务会在下次启动时补发。
- 设置页的“开机自动启动”使用当前 Windows 用户的启动项，不需要管理员权限。

## 安全约定

- 默认只在本地处理 VSCode 诊断事件，不向外部 API 上传代码。
- 只有用户显式启用 AI 分析后才允许发送内容。
- API 密钥不提交到 Git；DebugPet 2.0 使用系统凭据存储。

审计、路线图、实验结果和已知问题见 [`docs/`](docs/)。
