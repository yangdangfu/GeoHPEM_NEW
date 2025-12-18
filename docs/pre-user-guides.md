# GeoHPEM（当前版本）预使用指南

本指南描述当前仓库“已经能做什么、怎么操作”。当前阶段重点是 **导入网格 → 配置阶段 → 运行（fake solver）→ 浏览结果 registry → 保存工程**。

> 说明：当前 GUI 的 Viewport/云图渲染仍是占位；后处理暂以 `registry` 浏览为主。完整云图/剖面/曲线将在后续里程碑实现。

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

> 说明：由于 Viewport 还未接入，目前还不支持“从图形选择生成 set”，后续会补齐。

## 7. 编辑建模数据（Input 工作区 MVP）

左侧 Project Explorer 选择对象，右侧 Properties 可编辑：

- `Model`
  - `mode`（plane_strain/axisymmetric）
  - `gravity`（gx/gy）
- `Stages -> <stage>`
  - `analysis_type`、`num_steps`、`dt`
  - `output_requests`（JSON list）
  - `bcs`（JSON list，后续会做表单化）
  - `loads`（JSON list，后续会做表单化）
- `Materials -> <material_id>`
  - `model_name`
  - `parameters`（JSON object）

## 7.1 Undo/Redo

- 菜单：`Edit -> Undo / Redo`
- 快捷键：`Ctrl+Z` / `Ctrl+Y`

## 8. 网格质量检查（M3）

- `Mesh -> Mesh Quality...`
  - 当前实现：三角形单元（`cells_tri3`）的最小角与长宽比统计
  - 会列出最差的若干三角形索引（后续会做“定位到视图”）

## 9. 运行求解（目前为 fake solver）

- `Solve -> Run (Fake Solver)`
  1) 弹出 Pre-check 窗口：有 ERROR 会阻止运行；WARN 允许继续
  2) 后台运行，底部 Tasks 显示进度，Log 显示日志
  3) 输出写入工作目录的 `out/` 并自动切换到 Output 工作区

## 10. 查看结果（Output 工作区 MVP）

- Output 工作区会从 `result.json:registry` 动态列出可用结果项，并用 VTK 渲染网格与云图
- 操作：
  - 左侧选择字段（Registry）与步号（Step）
  - 默认显示标量云图（先支持 nodal 标量，如 `p`）
  - 勾选 `Warp by displacement u` 可按位移变形显示（若结果提供 `u`）
  - 在渲染窗口中点击点可 Probe（显示近邻点的数值 + 所属 node sets）
  - 选中单元（若版本支持 cell picking）会显示单元类型/编号 + 所属 element sets

> 说明：剖面线/时程曲线等将在后续里程碑实现（计划见 `docs/plans.md` 的后续条目）。

## 11. 画几何 → pygmsh 网格化（M4）

> 目前实现的是 **单一 Polygon2D 域** 的最小几何编辑与网格化闭环。

### 11.1 创建/编辑几何

左侧 Dock（与 Project 同一栏可切 tab）：`Geometry`

- 视图操作：
  - `Ctrl + 鼠标滚轮` 缩放
  - `鼠标中键拖拽` 平移
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
