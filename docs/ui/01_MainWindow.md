# MainWindow（主界面）规格

## 菜单/工具栏
- File：New/Open/Save/Save As/Recent/Import Mesh/Export
- Workspace：Input / Output 切换
- Solve：Select Solver / Run / Cancel / Open Output Folder
- View：显示/隐藏各 Dock
- Help：About / Diagnostics

## Dock 模块
- Project Explorer（左）
- Properties（右）
- Stage Manager（右）
- Log Console（下）
- Tasks & Progress（下）

## 中央区域
- WorkspaceStack（InputWorkspace / OutputWorkspace）
- 每个 workspace 内包含 Viewport（共享）与特定工具面板（后续）

## 状态栏
- 当前项目路径、solver 选择、运行状态（Idle/Running/Failed）

