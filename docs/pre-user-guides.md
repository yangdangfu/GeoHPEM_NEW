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

- Output 工作区会从 `result.json:registry` 动态列出可用结果项
- 选择条目可查看其 `name/location/shape/unit/npz_pattern` 等元数据

> 说明：云图/剖面/曲线等将在后续里程碑实现（计划见 `docs/plans.md` 的 M6）。

