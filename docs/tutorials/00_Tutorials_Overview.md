# GeoHPEM 案例教程（Step-by-step）

这些教程按“新建工程 → 建模/网格 → 设置 sets/阶段 → 校验 → 运行 → Output 后处理”的闭环来写，适合第一次上手或回忆操作顺序。

建议按顺序做：
1. `01_Tutorial_DrawGeometry_To_Post.md`：画几何→网格化→求解→后处理（最完整的从零开始）
2. `02_Tutorial_ImportMesh_To_Post.md`：导入现成网格（含 `.npz`）→快速建模→求解→后处理
3. `03_Tutorial_OpenCase_Output_Advanced.md`：直接打开 case folder（含现成 out）→专注后处理功能（Profile/History/Export/对标准备）

快捷键与交互约定（当前版本）：
- VTK 视图（Input/Output）：二维固定方向；滚轮缩放；中键平移；右键保留给菜单
- `Esc`：退出当前交互模式（box/polyline/profile edit 等）
- `C`：清空选择（Input Mesh Preview）
- `B` / `Shift+B`：Box nodes / Box elems（Input Mesh Preview）

