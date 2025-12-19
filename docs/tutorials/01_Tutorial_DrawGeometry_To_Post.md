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

## E. 配置阶段与输出请求

1. 在左侧 Dock 选择 `Stages`
2. 选中 `stage_1`（或你当前的第一个 stage）
3. 在右侧 `Properties`（若未显示：`View -> Properties` 打开；选中 stage 会自动切到 Properties）：
   - `analysis_type`：`static`
   - `num_steps`：例如 `10`
   - `dt`：例如 `1.0`
4. 在 `Stage output_requests` 表格中 `Add` 三行（示例）：
   - `u` / `node` / `every_n=1`
   - `p` / `node` / `every_n=1`
   - `vm` / `element` / `every_n=1`
5. 点击 `Apply`

## F. 校验与运行

1. `Tools -> Validate Inputs... (F7)`
   - 若有 WARN 可先继续；若有 ERROR 需要先修正（例如引用了不存在的 set）
2. `Solve -> Run (...)`
   - solver 选 `fake` 即可
3. 成功后会自动切到 Output 工作区（或点 Input 面板里的 `Go to Output`）

## G. Output 后处理（必做）

在 Output 工作区：

1. 左侧 `Registry` 选择一个字段（例如 `p (node)` 或 `vm (element)`）
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
