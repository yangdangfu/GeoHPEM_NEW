# GeoHPEM 案例教程（Step-by-step）

这些教程按“新建工程 → 建模/网格 → sets → 材料/分配/阶段 → 校验 → 运行求解 → Output 后处理”的闭环来写，适合第一次上手或回忆操作顺序。

建议按顺序做：
1. `01_Tutorial_DrawGeometry_To_Post.md`：画几何 → 网格化 →（ref_elastic）→ 后处理（从零开始最完整）
2. `02_Tutorial_ImportMesh_To_Post.md`：导入现成网格（`.npz`）→（ref_seepage）→ 后处理（导入路线）
3. `03_Tutorial_OpenCase_Output_Advanced.md`：直接打开已有 `out/` 的 case folder → 专注 Output（Profile/History/Export/对标准备）

## 前置准备（推荐）

仓库提供了 2 个“参考真实求解器”（内置）：
- `ref_elastic`：线弹性（平面应变/平面应力），输出 `u`/`vm` 等
- `ref_seepage`：稳态渗流（Darcy/Poisson），输出 `p`

先生成参考算例（输出到 `_Projects/cases/*`，该目录默认 gitignored）：
- `python scripts/make_reference_cases.py`

## 快捷键与交互约定（当前版本）

- VTK 视图（Input/Output）：二维固定方向；滚轮缩放；中键平移；右键弹出菜单（上下文命令）
- `Esc`：退出当前交互模式（box / polyline / profile edit 等）
- `C`：清空选择（Input Mesh Preview）
- `B` / `Shift+B`：Box nodes / Box elems（Input Mesh Preview）
