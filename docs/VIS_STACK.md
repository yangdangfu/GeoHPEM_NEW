# 可视化技术栈（M5 定版）

## 决策

- **Input（建模/几何编辑）**：Qt2D（`QGraphicsView/QGraphicsScene`）
  - 适合：交互绘制、编辑、吸附、约束（后续）、轻量拾取与高亮
- **Output（网格/结果可视化）**：VTK（通过 `pyvista + pyvistaqt` 嵌入 PySide6）
  - 适合：大网格渲染、标量云图、变形、切片/剖切、等值线、探针、拾取、导出

## 为什么这样分工

- Qt2D 做编辑更轻、状态机更清晰；VTK 做渲染/后处理能力更完整且性能更强。
- 该边界稳定后，后续功能只需在 Output 侧扩展 VTK pipeline（不影响 Input 编辑器）。

## 依赖

- `PySide6`
- `pyvista`
- `pyvistaqt`
- （可选）`vtk`（通常被 pyvista 拉入环境）

环境建议：`environment.yml`

