# 教程 03：直接打开 Case Folder（含 out）→ 专注 Output 后处理与对标准备

目标：不跑求解也能完整练习 Output（云图/Probe/Profiles/Pins/导出），适合做 UI 回归与对标输出清单确认。

推荐使用参考算例（真实 solver 输出更可对标）：
- `_Projects/cases/reference_elastic_01`
- `_Projects/cases/reference_seepage_01`

如果没有这些目录：
1. 生成 case：`python scripts/make_reference_cases.py`
2. 生成 out（写出 `out/` 结果）：
   - `python geohpem_cli.py run _Projects/cases/reference_elastic_01 --solver ref_elastic`
   - `python geohpem_cli.py run _Projects/cases/reference_seepage_01 --solver ref_seepage`

> 也可以用 `_Projects/cases/realistic_case_01`（`python scripts/make_realistic_case.py`）专门回归 Output UI，但它的 out 不一定来自真实求解器。

## A. 打开 Case Folder

1. 启动：`python main.py`
2. `File -> Open Case Folder...`
3. 选择：`_Projects/cases/reference_elastic_01`（或 `reference_seepage_01`）
4. 观察：
   - 工程加载成功（Project Dock 有结构）
   - 如果存在 `out/`，会自动切换到 Output（或手动 `Workspace -> Output`）

## B. Output：云图/步号/单位

1. 左侧 `Registry`：
   - `reference_elastic_01`：`u (node)`（位移向量，可在 `Field mode` 里选 Magnitude）、`vm (element)`（等效应力）
   - `reference_seepage_01`：`p (node)`（孔压/水头类标量）
2. `Step`：
   - 拖动步号，观察云图随步变化
   - Step 下面会显示 `global_step_id / time / stage`（如果 solver 提供了 `result.json:global_steps`）
3. 单位显示：
   - `View -> Display Units...` 切换长度/压强显示单位，观察 Probe/色标同步变化

## C. Output：Probe + Pin（对标常用）

1. Probe：左键点击网格
2. 右侧（或上方）Probe 文本会显示：
   - pid / 坐标 / 数值 / 所属 sets
3. Pin：
   - 点 `Pin last probe (node)` 固定一个节点
   - 选单元：`Shift + 左键` 点击单元后点 `Pin last cell (element)` 固定一个单元
4. `Time history...`：
   - 切到左侧 `Pins` 标签页，点击 `Time history...`，选择 `Use pinned` 或 `Use last picked`
   - 生成“时程曲线”（横轴优先用 time，否则用 step）

## D. Output：剖面线（Profile line）

1. 切到左侧 `Profiles` 标签页，点击 `Profile line...`
   - 默认勾选 `Save to Profiles list`（推荐），这样 profile 会出现在 Profiles 列表中，后续可重复编辑/导出
2. 推荐方式：`Pick 2 points (viewport)` → 在视窗里连续点两次
3. 自动生成 profile 并弹出曲线窗口（支持 `Export CSV...` / `Save Plot Image...`）
4. Profiles 列表：
   - 选中一条 profile，点 `Edit selected (drag)` 在视窗拖拽端点调整（`Finish/Cancel`）

## E. 导出（对标交付最常用）

1. `Export image...`：导出当前视窗截图（PNG）
2. `Export steps -> PNG...`：导出序列（保持相机视角）
3. （建议对标习惯）建立一套输出命名规则：
   - `caseName_field_stage_step.png`
   - profile/time history CSV 同步命名

## F. 右键菜单与快捷键（提升效率）

1. 在 Output Viewer 右键：
   - `Reset view / Export image / Profile line / Time history / Pin...`
2. `Esc`：
   - 取消 profile edit（或退出当前交互）
