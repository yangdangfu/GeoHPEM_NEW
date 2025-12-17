# GeoHPEM UI 规格（MVP）

目标：以“类 PLAXIS”工作流实现 **建模(Input) → 求解 → 后处理(Output)** 的端到端闭环；UI 不依赖 solver 内部实现，所有可用项由 `capabilities()` 与结果 `registry` 驱动。

## 工作区（Workspaces）
- **Input（建模）**：几何/网格/集合/材料/边界/荷载/阶段/输出请求/求解设置
- **Output（后处理）**：结果浏览、云图/等值线/变形、剖面线与探针、曲线、导出
- （预留）Compare（对标）/Batch（批处理）

## 主窗口布局（Dock）
- **中央**：Viewport（几何/网格/结果显示；MVP 先占位，后续接入 VTK/PyVistaQt）
- **左侧**：Project Explorer（项目树）
- **右侧**：Properties（属性编辑器）
- **右侧/下方**：Stage Manager（阶段列表/变更）
- **底部**：Log Console（日志）+ Tasks/Progress（任务与进度）

## UI 与数据的边界
- UI 编辑 `Domain Model`（平台对象），由 `Contract Builder` 导出为 `request.json + mesh.npz`
- 求解结果以 `result.json + result.npz` 读入，UI 仅依赖 `registry` 动态构建可视化选项

## MVP 优先级（P0）
1. 打开/保存工程（先按 case folder：`request.json + mesh.npz`）
2. 项目树 + 属性面板（展示 request 结构，支持最小编辑）
3. 选择 solver（fake / python:<module>）并运行，显示进度与日志
4. 结果浏览（registry 列表）+ 最小可视化入口（先做字段选择与色标面板占位）

