# 教程 01：从零开始（画几何 → 网格化 → 求解 → 后处理）

目标：不依赖外部网格文件，完整走一遍“建模闭环”，并熟悉 Output 的 Probe/Profile/Time history/导出。

## A. 新建工程

1. 启动：`python main.py`
2. `File -> New Project...`
   - Mode：`Plane strain`
   - Template：`Empty project`
3. `File -> Save As...` 保存为 `tutorial_01.geohpem`（建议新建一个工作目录）

## B. 画几何（Rectangle + 标签）

1. 在左侧 Dock 选择 `Geometry`
2. 点击 `Rectangle`
   - 进入“交互绘制矩形”模式：左键点第一个角点，再点第二个角点完成（鼠标移动有预览）
3. （可选）点击 `Edge Labels...` 确认四条边分别是 `bottom/right/top/left`

## C. 网格化（pygmsh）

1. 在 `Geometry` Dock 点击 `Generate Mesh...`
2. 设置 `mesh_size`（例如 `0.5` 或 `1.0`），确定
   - `mesh_size` 的单位与当前显示长度单位一致（对话框里会标注，例如 `m/km`）；内部会自动换算到工程单位
3. 观察：
   - Input 中央 `Mesh Preview (Input)` 出现网格
   - 若 mesh 中已有 sets，会在 `Highlight set` 下拉中出现 `node_set__/edge_set__/elem_set__...`
   - 若没有边界 sets（常见）：下一步用 `Boundary helpers (auto)` 自动创建 `bottom/top/left/right`

## D. 图形选集与 sets（推荐做：后续施加边界条件/荷载会用到）

在 Input 中央 `Mesh Preview (Input)`：

1. 右键打开菜单（或使用按钮）
2. 依次创建 3 个边界 set（教程最小集）：
   - `Auto boundary -> Bottom` → `Create edge set...` 命名 `bottom`
   - `Auto boundary -> Left` → `Create edge set...` 命名 `left`
   - `Auto boundary -> Top` → `Create edge set...` 命名 `top`
3. 在 `Highlight set` 下拉中验证边界高亮是否正确

> 是否需要创建 4 条边界？
> - 本教程为了演示 BC + 竖向荷载，只要求 `bottom/left/top`。
> - 真实工程通常也会创建 `right`（例如水平位移约束/侧向荷载/渗流边界）。

> 提示：也可以 `Polyline` 沿边刷选；或 `Box nodes/Box elems` 批量选择后创建 set。

## E. 选择求解器（ref_elastic）

1. `Solve -> Select Solver...`
2. 选择 `Reference Elastic (built-in)`（即 `ref_elastic`），点击 OK

## F. 配置材料与分配（ref_elastic 必需）

> 说明：平台只负责把 `mesh/materials/assignments/bcs/loads/output_requests...` 交给 solver；材料本构由 solver 解释与计算。

1. 在左侧 `Project`（Project Explorer）展开 `Materials`
2. 新建一个材料：
   - 方式 A（推荐）：选中 `Materials`，右键 `Add material...`
   - 方式 B：`Edit -> Add Material...`
   - Material ID：`mat_soil`
3. 选中 `mat_soil`，在右侧 `Properties` 设置：
   - `Model Name`：`linear_elastic`
   - `parameters`（JSON，示例）：
     - `{"E": 3.0e7, "nu": 0.3, "rho": 1800.0}`
   - 点击 `Apply`
4. 配置分配（element_set → material）：
   - 在左侧 `Project` 选中 `Assignments`
   - 在右侧 `Properties` 的 Assignments 表格点 `Add`
   - 设置：`element_set=domain`，`cell_type=tri3`（或你的网格类型），`material_id=mat_soil`
     - 若 `element_set` 下拉为空：可以直接手动输入 `domain`（该下拉是可编辑的）；同时确认你已经完成了 `Generate Mesh...`（mesh 生成后会自动创建 `elem_set__domain__tri3`）
   - 点击 `Apply`

## G. 配置阶段（BC/Loads/Outputs）

1. 在左侧 `Project` 选中 `Stages -> stage_1`
2. 在右侧 `Properties`（若未显示：`View -> Properties` 打开）：
   - `analysis_type`：`static`
   - `num_steps`：例如 `8`
   - `dt`：例如 `1.0`
3. 在 `Stage BCs` 表格中 `Add` 两行（示例）：
   - `type=displacement`，`set=bottom`，`value={"ux":0.0,"uy":0.0}`
   - `type=displacement`，`set=left`，`value={"ux":0.0}`
4. 在 `Stage Loads` 表格中 `Add` 一行（示例）：
   - `type=traction`，`set=top`，`value=[0.0,-1.0e5]`
5. 在 `Stage output_requests` 表格中 `Add` 两行（示例）：
   - `u` / `node` / `every_n=1`
   - `vm` / `element` / `every_n=1`
6. 点击 `Apply`

> 关于 `Stage BCs/Loads` 表格里的 `field/type/set/value`：
> - `type`：边界/荷载“类型”（建议从下拉选择；会随 solver capabilities 变化）。例如 `displacement`/`traction`/`p`/`flux`。
> - `set`：作用的集合名（来自 mesh 的 `node_set__/edge_set__/elem_set__`）。
> - `value`：**JSON 值**（不是随意字符串）。可以是数字、数组或对象：
>   - 位移（displacement）：`{"ux":0.0,"uy":0.0}` 或 `{"ux":0.0}`
>   - 面力（traction）：`[0.0, -1.0e5]`
>   - 给定孔压（p）：`100000.0`
>   - 通量（flux）：`-1.0e-6`
> - `field`：目标物理量名（开发期为可选/预留字段；当前参考 solver 主要以 `type` 解释含义）。UI 会根据 `type` 自动填入常见的 `u/p`。

## H. 校验与运行

1. `Tools -> Validate Inputs... (F7)`
   - 若有 WARN 可先继续；若有 ERROR 需要先修正（例如引用了不存在的 set）
2. `Solve -> Run (...)`（应显示 `Run (ref_elastic)`）
3. 成功后会自动切到 Output 工作区（或点 Input 面板里的 `Go to Output`）

## G. Output 后处理（必做）

在 Output 工作区：

1. 左侧 `Registry` 选择一个字段（例如 `u (node)` 或 `vm (element)`）
2. `Step` 选择不同步号，观察云图变化
3. Probe：在渲染窗口左键点击，观察上方 Probe 文本更新
4. Pin：
   - Probe 一个点后点击 `Pin last probe (node)`
   - 选单元：`Shift + 左键` 点击单元后点击 `Pin last cell (element)`
5. Profile line：
   - 切到左侧 `Profiles` 标签页，点击 `Profile line...`（或直接 `Pick 2 points (viewport)`）
   - `Profile line...` 默认勾选 `Save to Profiles list`，生成的 profile 会出现在 Profiles 列表中，便于后续编辑/导出
   - 推荐用 `Pick 2 points (viewport)`，在视窗里连续点两次
   - 弹出的曲线窗口里可 `Export CSV...` / `Save Plot Image...`
6. Time history：
   - 切到左侧 `Pins` 标签页，点击 `Time history...`
   - 选择 `Use pinned`（或 `Use last picked`）生成时程曲线
7. 导出：
   - `Export image...` 导出当前视窗
   - `Export steps -> PNG...` 批量导出序列

## H. 保存归档

1. `File -> Save` 保存工程（包含 `ui_state`：Profiles/Pins 等）
2. （可选）`File -> Export Case Folder...` 导出 `request.json + mesh.npz` 给 solver 团队
