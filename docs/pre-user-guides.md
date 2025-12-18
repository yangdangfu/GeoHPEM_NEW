# GeoHPEM（当前版本）预使用指南

本指南描述当前仓库“已经能做什么、怎么操作”。当前阶段重点是 **导入网格 → 配置阶段 → 运行（fake solver）→ Output 云图/探针 → 保存工程**。

> 说明：Output 已接入 VTK（PyVistaQt）云图渲染与 Probe，并提供 Profile line / Time history / 导出截图（PNG）；动画批量导出等仍在后续里程碑完善。

## 1. 环境准备

- 推荐使用 conda 环境：`environment.yml`
  - 创建：`conda env create -f environment.yml`
  - 激活：`conda activate geohpem`

## 2. 启动

在仓库根目录：
- 启动 GUI：`python main.py`
- 启动并打开工程/算例：
  - `python main.py --open <path>`
  - `<path>` 可以是：
    - `.geohpem` 工程文件
    - case folder（包含 `request.json + mesh.npz` 的目录）

推荐的“更接近实际”的测试算例（已包含多阶段/多 sets/element 字段）：
- `_Projects/cases/realistic_case_01`
  - 生成脚本：`python scripts/make_realistic_case.py`（会同时生成 `out/` 结果，便于直接测试 Output）

## 3. 新建工程

GUI 菜单：
- `File -> New Project...`
  - Mode：Plane strain / Axisymmetric
  - Template：
    - `Empty project`：空工程（mesh 为空，会在 pre-check 提示 warning）
    - `Sample (unit square)`：自带一个最小网格 + stage，可直接跑 fake solver

## 4. 打开/保存工程（单文件）

- 打开：`File -> Open Project...`（`.geohpem`）
- 另存为：`File -> Save As...`（保存为 `.geohpem` 单文件包）
- 导出算例目录：`File -> Export Case Folder...`（写出 `request.json + mesh.npz`，便于给 solver 团队/批量回归）
- 最近项目：`File -> Open Recent`
- 启动恢复：启动时会询问是否恢复上次打开的工程/目录（可选）

工程文件格式说明：`docs/PROJECT_FILE_FORMAT.md`

## 5. 导入现成网格（M3）

前提：安装 `meshio`（见 `environment.yml`）。

- `File -> Import Mesh...`
  - 选择网格文件（推荐 `.msh`）
  - 勾选 `Generate sets from Gmsh physical groups`：
    - 如果网格带 Gmsh 物理组（Physical Groups），将自动生成：
      - `node_set__*`（来自 vertex physical，若存在）
      - `edge_set__*`（来自 line physical）
      - `elem_set__*__tri3/quad4`（来自 triangle/quad physical）

导入后，在左侧 Project Explorer 的 `Sets` 下可以看到生成的集合及数量。

## 6. Sets 管理（重命名/删除/简单创建）

- `Edit -> Manage Sets...`
  - 列表会显示当前 mesh 中的 `node/edge/elem` sets
  - 支持：
    - Delete：删除选中的 set
    - Rename：重命名选中的 set
    - Add：创建新 set（MVP 以手工输入索引为主）
      - Node set：输入节点索引，如 `0,1,5-10`
      - Edge set：输入边的节点对，如 `0-1,1-2,2-3` 或 `0 1; 1 2; 2 3`
      - Element set：选择 tri3/quad4，输入单元索引，如 `0,2,3-20`

> 说明：Input 工作区中央已接入 Mesh Preview（高亮 sets + 点击拾取信息），但目前还不支持“从图形选择生成 set”，后续会补齐。

## 7. 编辑建模数据（Input 工作区 MVP）

左侧 Project Explorer 选择对象，右侧 Properties 可编辑：

> 说明：Input 工作区中间区域包含“流程导航/快捷入口面板”（Quick Actions + Status + 推荐流程）+ “Mesh Preview”（查看网格、sets 高亮、点击拾取节点/单元信息）。核心编辑仍在左右 Dock（Project/Geometry/Properties/Stages）完成。

- `Model`
  - `mode`（plane_strain/axisymmetric）
  - `gravity`（gx/gy）
- `Stages -> <stage>`
  - `analysis_type`、`num_steps`、`dt`
  - `output_requests`：表格编辑 `name/location/every_n`（name 由 solver capabilities 提供下拉，可编辑；不支持字段会提示 WARN）
  - `bcs`：表格编辑（Add/Delete/JSON->Table），`set` 支持下拉选择（可编辑）
  - `loads`：表格编辑（Add/Delete/JSON->Table），`set` 支持下拉选择（可编辑）

> 提示：Stage 编辑现在以 `stage.uid` 为稳定标识（避免增删阶段导致“按索引编辑错对象”的问题）。
- `Materials -> <material_id>`
  - `model_name`
  - `parameters`（JSON object）
- `Assignments`
  - 表格编辑 `element_set / cell_type / material_id`（均支持下拉+可编辑）
  - 用于将材料分配到 element sets（solver-owned，但平台负责提供结构化配置）
- `Global output_requests`
  - 表格编辑 `name/location/every_n`（name 由 solver capabilities 提供下拉，可编辑）

## 7.1 Undo/Redo

- 菜单：`Edit -> Undo / Redo`
- 快捷键：`Ctrl+Z` / `Ctrl+Y`
- 提示：菜单项会显示可撤销动作名；几何连续拖拽编辑会自动合并为更少的 undo 步。

## 8. 网格质量检查（M3）

- `Mesh -> Mesh Quality...`
  - 当前实现：三角形单元（`cells_tri3`）的最小角与长宽比统计
  - 会列出最差的若干三角形索引（后续会做“定位到视图”）

## 9. 运行求解（目前为 fake solver）

- 选择 solver：`Solve -> Select Solver...`
  - `Fake`：内置的假 solver，用于跑通流程与 UI
  - `Python module`：通过 `python:<module>` 加载外部 solver 包（未来将以 submodule 方式集成）
  - 快速切换：`Solve -> Recent Solvers`（保存最近使用的 solver selector）

- 运行：`Solve -> Run (...)`
  1) 弹出 Pre-check 窗口：包含 contract 基础校验 +（可选）jsonschema 校验 + precheck；有 ERROR 会阻止运行；WARN 允许继续
     - 若所选 solver 的 `capabilities()` 声明不支持当前 `mode`/`analysis_type`，会直接给出 ERROR
  2) 后台运行，底部 Tasks 显示进度，Log 显示日志
  3) 输出写入工作目录的 `out/` 并自动切换到 Output 工作区
  4) Tasks 面板支持 `Cancel`（best-effort：solver 需要在迭代中检查 `callbacks['should_cancel']`）
  5) 若失败/取消，会在工程工作目录生成 `_diagnostics/diag_*.zip` 便于排查/转交 solver 团队

- 仅校验不运行：`Tools -> Validate Inputs...`（快捷键 `F7`）

## 10. 查看结果（Output 工作区 MVP）

- Output 工作区会从 `result.json:registry` 动态列出可用结果项，并用 VTK 渲染网格与云图
- 操作：
  - 左侧选择字段（Registry）与步号（Step）
    - Step 下方会显示 `global_step_id / time / stage`（若 solver 提供 `result.json:global_steps`）
  - 默认显示标量云图（先支持 nodal 标量，如 `p`）
  - 勾选 `Warp by displacement u` 可按位移变形显示（若结果提供 `u`）
  - 在渲染窗口中点击点可 Probe（显示近邻点的数值 + 所属 node sets）
  - 选中单元（若版本支持 cell picking）会显示单元类型/编号 + 所属 element sets
  - `Profile line...`：剖面线（线采样）
    - 推荐方式（更顺手）：点 `Pick 2 points (viewport)` 进入剖面拾取模式，在视窗连续点两次即可自动生成剖面并弹出曲线
    - 也可用旧方式：先在视窗里连续点两次（得到 2 次 Probe），再点 `Use last two picks` 自动填入端点
    - 自动弹出曲线窗口，支持 `Export CSV...` 与 `Save Plot Image...`
  - `Time history...`：时程曲线
    - 弹窗选择来源：`Use last picked` 或 `Use pinned`
    - 对 nodal 字段：先 Probe 一个点（确定 pid）或 `Pin last probe (node)`；对 element 字段：先 pick 一个单元（确定 cell_id）或 `Pin last cell (element)`
    - 自动弹出曲线窗口（横轴优先用 time，否则用 step），支持 `Export CSV...`
  - `Export image...`：导出当前视窗截图（PNG）
  - `View -> Display Units...` 可切换显示单位（目前最小支持：长度/压强；不改变底层数据）

## 11. 画几何 → pygmsh 网格化（M4）

> 目前实现的是 **单一 Polygon2D 域** 的最小几何编辑与网格化闭环。

### 11.1 创建/编辑几何

左侧 Dock（与 Project 同一栏可切 tab）：`Geometry`

- 视图操作：
  - `Ctrl + 鼠标滚轮` 缩放
  - `鼠标中键拖拽` 平移
  - `Fit` 适配视图；`Reset View` 重置缩放
  - 背景网格与坐标轴用于尺度参考（左下角坐标实时显示）

- `Rectangle`：生成一个默认矩形（带边界标签 bottom/right/top/left）
- `Draw Polygon`：进入绘制模式
  - 左键依次点击添加顶点
  - 右键或 `Finish` 结束并闭合为多边形
- 拖拽顶点：可直接拖动白色节点点位修改几何
- `Edge Labels...`：编辑每条边的标签（用于生成 edge sets）

### 11.2 网格化

- `Generate Mesh...`
  - 设置 `mesh_size`
  - 成功后会更新项目的 `mesh`，并根据边标签/区域名自动生成 sets：
    - `edge_set__<label>`
    - `elem_set__<region_name>__tri3`

## 12. 批量跑算例（高级/工程化）

用于回归/对标：对一个目录下的多个 case folder 批量运行 solver，并输出汇总报告。

- 命令：`python -m geohpem.cli batch-run <cases_root> --solver fake`
  - 开发态（无需安装包）也可用：`python geohpem_cli.py batch-run <cases_root> --solver fake`
  - `<cases_root>`：包含多个 case folder 的目录（每个子目录含 `request.json + mesh.npz`）
  - 输出：默认写到 `<cases_root>/batch_report.json`
  - 失败会生成 `_diagnostics/diag_*.zip`（每个 case 自己的工作目录里）
  - 可选对比：`--baseline <baseline_root>`（要求基准结果位于 `<baseline_root>/<case_name>/out`）

GUI 入口（MVP）：
- `Tools -> Batch Run...`：选择 cases root / solver / baseline / report，并显示进度与日志（Cancel 为 best-effort）。
- `Tools -> Open Batch Report...`：打开 `batch_report.json`，以表格方式浏览 success/failed/canceled、耗时、内存、最大差值，并可一键打开 case/out/diagnostics。
  - 报告会记录 `error_code`（若失败/取消），便于对标/回归统计与归因。

## 13. 结果对比（差值云图/曲线，MVP）

- `Tools -> Compare Outputs...`
  - 选择 A 与 B（可以选择 case folder 或 `out/` 目录）
  - 左侧选择字段（交集）与步号（Step）
  - `View` 可切换：`Diff (A-B)` / `A` / `B`
  - `Export step-curve CSV...`：导出该字段随 step 的统计（min/max/mean）到 CSV，便于对标与回归分析
