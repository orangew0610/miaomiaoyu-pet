# DebugPet

DebugPet 是一个基于 PyQt5 的 Windows 桌面宠物。当前 `feature/debugpet-v2` 分支用于开发 DebugPet 2.0：VSCode 环境感知、主动 Debug、人格化对话和持久化记忆。

## Windows 开发环境

项目使用仓库内的 `.venv` 隔离依赖，不会修改其他 Python 项目的包。

```powershell
# 首次创建环境（已创建时无需重复执行）
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv

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

## 安全约定

- 默认只在本地处理 VSCode 诊断事件，不向外部 API 上传代码。
- 只有用户显式启用 AI 分析后才允许发送内容。
- API 密钥不提交到 Git；DebugPet 2.0 使用系统凭据存储。

审计、路线图、实验结果和已知问题见 [`docs/`](docs/)。
