# 教程 02：导入现成网格（Import Mesh）→ 求解 → 后处理

目标：走“导入现成网格”路线，并学会用 Mesh Preview 做 sets 选集（box/brush/polyline/boundary）。

> 说明：当前版本 `Import Mesh...` 支持：
> - 通用网格格式（依赖 meshio）：`.msh/.vtk/.vtu/.xdmf/...`
> - Contract 格式：`.npz`（例如 case folder 的 `mesh.npz`）

## A. 准备一个可导入的网格文件

推荐直接用仓库自带测试算例的网格：
- `_Projects/cases/realistic_case_01/mesh.npz`

如果没有该目录：
1. 运行：`python scripts/make_realistic_case.py`
2. 确认生成：`_Projects/cases/realistic_case_01/mesh.npz`

## B. 新建工程（用 Sample 模板更省事）

1. 启动：`python main.py`
2. `File -> New Project...`
   - Mode：`Plane strain`
   - Template：`Sample (unit square)`
3. `File -> Save As...` 保存为 `tutorial_02.geohpem`

> 选择 Sample 模板的原因：它自带一个 stage 与最小配置；后续只替换 mesh。

## C. 导入网格

1. `File -> Import Mesh...`
2. 选择网格文件（示例）：`_Projects/cases/realistic_case_01/mesh.npz`
3. 确认导入后观察：
   - Input 中央 `Mesh Preview` 出现网格
   - `Highlight set` 下拉里能看到 `node_set__/edge_set__/elem_set__...`

## D. sets 选集（工程常用）

在 Input 中央 `Mesh Preview`：

### D1. 边界自动提取（最常用）
1. `Boundary helpers (auto) -> Bottom`
2. 点 `Create edge set...`，命名为 `bottom_fix`

### D2. 框选/刷选（批量选择）
1. 勾选/取消：
   - `Replace`：替换当前选择
   - `Subtract`：从当前选择中删除（与 Replace 互斥）
   - `Brush`：保持 box 模式，连续多次拖框
2. 快捷键：
   - `B`：Box nodes
   - `Shift+B`：Box elems
   - `C`：清空选择
   - `Esc`：退出 box 模式

### D3. 沿边刷选（polyline）
1. 点 `Polyline`
2. 在边界附近依次点击几个点（支持吸附），会自动沿边界补齐边
3. 点 `Finish`
4. 点 `Create edge set...` 保存为 `wall_line`（示例）

## E. 校验与运行

1. `Tools -> Validate Inputs... (F7)`（确认没有 ERROR）
2. `Solve -> Run (...)`（solver 用 `fake` 即可）

## F. Output 后处理（同教程 01）

1. 选字段（Registry）与步号（Step）查看云图
2. Probe + Pin
3. 左侧 `Profiles/Pins` 标签页：`Profile line...` / `Time history...`
4. `Export image...` / `Export steps -> PNG...`

## G. 保存归档

1. `File -> Save` 保存工程（包含 UI state：Profiles/Pins）
2. （可选）`File -> Export Case Folder...` 导出给 solver 团队
