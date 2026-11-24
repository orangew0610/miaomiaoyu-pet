# DebugPet 2.0 分阶段计划

状态只使用：未开始、进行中、已验证、受阻。只有测试结果可支撑“已验证”。

## V0.1 基础可靠性（进行中）

- 可复现的 Windows `.venv`、README 和可移植打包流程。
- 修复聊天当前消息重复。
- 聊天和 AI 检查迁移到工作线程。
- 统一 provider、API URL、模型名、超时和上传授权配置。
- Windows 凭据管理器保存 API 密钥。
- `MemoryService` 接口和 Null 实现。
- 基础单元测试和手动验收清单。

## V0.2 VSCode 诊断闭环（进行中）

- 独立 TypeScript 扩展与版本化 IPC schema。
- 本机 IPC 鉴权、重连、消息大小限制。
- 诊断去重、等级筛选、冷却、版本校验和消失事件。
- VSCode 原生 diagnostic range 高亮/选择。
- 桌宠目标移动、人格化提示、错误清零庆祝。
- 默认仅传元数据；代码内容需显式授权。

## V0.3 Windows 精确定位实验（已验证降级方案）

- UI Automation 探针：VSCode 编辑器、活动标签、文本 range 与 bounding rectangle。
- 校验缩放、多显示器、窗口移动、滚动、折行和 minimap 情况。
- 精确定位可行时映射到屏幕坐标；失败时降级到 VSCode 窗口边缘或诊断面板锚点。
- 记录 VSCode/Electron/Windows 版本和实际结果，不以设计推测代替验证。

2026-11-24 实测未获得文本控件或有效 UIA rectangle，当前不实现伪精确定位；采用“扩展内 range 高亮 + VSCode 顶层窗口边缘锚点”的降级方案。详见 `EXPERIMENTS.md`。

## 后续版本（未开始）

- 可持久化长期记忆实现、保留策略、导出与删除。
- 角色 manifest、原创角色包、用户自定义角色校验和热切换。
- 更完整的隐私审计、签名发布和升级机制。

基础角色 manifest 和路径/资源校验器已在 V0.1 建立；主程序切换到 manifest 驱动、角色选择和热切换仍未开始。
