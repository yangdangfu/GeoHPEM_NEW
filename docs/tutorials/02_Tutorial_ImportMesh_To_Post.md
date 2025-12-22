# 教程 02：导入现成网格（Import Mesh）→（ref_seepage）→ 后处理

目标：走“导入现成网格”路线，用真实参数驱动一个最小的稳态渗流算例，并学会用 Mesh Preview 做 sets 选集（box/brush/polyline/boundary）。

> 说明：当前版本 `Import Mesh...` 支持：
> - 通用网格格式（依赖 meshio）：`.msh/.vtk/.vtu/.xdmf/...`
> - Contract 格式：`.npz`（例如 case folder 的 `mesh.npz`）

## A. 准备一个可导入的网格文件

推荐直接用仓库自带的参考算例网格：
- `_Projects/cases/reference_seepage_01/mesh.npz`

如果没有该目录：
1. 运行：`python scripts/make_reference_cases.py`
2. 确认生成：`_Projects/cases/reference_seepage_01/mesh.npz`

## B. 新建工程

1. 启动：`python main.py`
2. `File -> New Project...`
   - Mode：`Plane strain`
   - Template：`Empty project`
3. `File -> Save As...` 保存为 `tutorial_02.geohpem`

> 提示：如果你更喜欢从一个“带默认数据”的工程开始，也可以选 `Sample (unit square)`，但后续需要把材料/分配/阶段都改成渗流所需配置。

## C. 导入网格

1. `File -> Import Mesh...`
2. 选择网格文件（示例）：`_Projects/cases/reference_seepage_01/mesh.npz`
3. 确认导入后观察：
   - Input 中央 `Mesh Preview` 出现网格
   - `Highlight set` 下拉里能看到 `node_set__/edge_set__/elem_set__...`

## D. 选择求解器（ref_seepage）

1. `Solve -> Select Solver...`
2. 选择 `Reference Seepage (built-in)`（即 `ref_seepage`），点击 OK

## E. 配置材料与分配（ref_seepage 必需）

1. 在左侧 `Project` 展开 `Materials`
2. 新建一个材料（渗透系数）：
   - 选中 `Materials`，右键 `Add material...`（或 `Edit -> Add Material...`）
   - Material ID：`mat_k`
3. 选中 `mat_k`，在右侧 `Properties` 设置：
   - `Model Name`：`darcy`
   - `parameters`（JSON，示例）：`{"k": 1.0e-6}`
   - 点击 `Apply`
4. 配置分配：
   - 在左侧 `Project` 选中 `Assignments`
   - 点 `Add`，设置：`element_set=soil`，`cell_type=tri3`，`material_id=mat_k`
   - 点击 `Apply`

## F. 配置阶段（渗流边界/输出）

> 说明：参考网格 `reference_seepage_01/mesh.npz` 已自带边界 sets：`top/bottom/left/right`，可直接引用。

1. 在左侧 `Project` 选中 `Stages -> stage_1`
2. 在右侧 `Properties` 设置：
   - `analysis_type`：`seepage_steady`
   - `num_steps`：例如 `5`（便于观察 Step/Probe/History）
   - `dt`：例如 `1.0`
3. 在 `Stage BCs` 表格点 `Add` 一行（示例）：
   - `type=p`，`set=top`，`value=100000.0`
4. 在 `Stage Loads` 表格点 `Add` 一行（示例）：
   - `type=flux`，`set=bottom`，`value=-1.0e-6`
5. 在 `Stage output_requests` 表格点 `Add` 一行：
   - `p` / `node` / `every_n=1`
6. 点击 `Apply`

## G. 校验与运行

1. `Tools -> Validate Inputs... (F7)`（确认没有 ERROR）
2. `Solve -> Run (...)`（应显示 `Run (ref_seepage)`）

## H. Output 后处理（同教程 01）

1. 选字段（Registry：`p (node)`）与步号（Step）查看云图
2. Probe + Pin
3. 左侧 `Profiles/Pins` 标签页：`Profile line...` / `Time history...`
4. `Export image...` / `Export steps -> PNG...`

## I. 保存归档

1. `File -> Save` 保存工程（包含 UI state：Profiles/Pins）
2. （可选）`File -> Export Case Folder...` 导出给 solver 团队

---

## 附：sets 选集（工程常用）

在 Input 中央 `Mesh Preview`（可选练习）：

- 边界自动提取（最常用）：`Boundary helpers (auto) -> Bottom/Top/Left/Right` → `Create edge set...`
- 框选/刷选（批量选择）：`B`/`Shift+B` 进入 Box；`Brush` 连续框选；`Replace`/`Subtract` 控制集合运算；`Esc` 退出
- 沿边刷选（polyline）：`Polyline` → 点击若干点 → `Finish` → `Create edge set...`
