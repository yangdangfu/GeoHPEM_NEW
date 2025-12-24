# GeoHPEM_NEW 开发计划与 Checklist（可迭代调整）

本文件用于把“软件可用闭环”拆解成可执行步骤。每个条目都有 **Definition of Done（DoD）**，完成后在方括号中打勾。

> 术语：
> - **Case Folder**：包含 `request.json + mesh.npz` 的算例目录（可带 `out/`）。
> - **Contract**：平台与 solver 的数据契约（JSON + NPZ）与 `capabilities()/solve()` API。
> - **Registry**：`result.json` 中的结果项索引，驱动后处理 UI。

---

## 使用流程（强调合理性/适用性，GUI 要花功夫）
目标是把“工程建模 → 求解 → 后处理/对标 → 归档复用”做成顺畅闭环，既适合科研快速迭代，也适合工程规范交付。

**范围澄清（重要）**
- 本项目不追求复刻 PLAXIS 的全部功能；只需要“类似 FEM 的流程”与工程化体验：建模数据准备 → 调用 solver → 后处理。
- 最终 solver 将是自研 **PFEM / HPEM（Particle Finite Element Method / Hybrid Element Particle Method）**；平台要做到：
  - Contract / API 设计从一开始就能承载 PFEM/HPEM 的真实输入与输出（可以分小步落地，但不走“先做一个临时简化契约、再推翻重来”的路线）。
  - GUI/Domain 的数据结构与交互围绕“可驱动 solver、可对标输出”组织，不做无意义的功能堆叠。
- 开发阶段**不要求跨版本兼容**：工程文件/contract/schema 可以迭代变更；但要预留扩展点（例如 schema_version 字段、migrations 入口），等正式版再收敛兼容策略。

**主流程（MVP 必须顺滑）**
1) `File -> New Project...`（或 Open Project / Open Case Folder）
2) 选择路线：
   - Route A：`File -> Import Mesh...` → `Edit -> Manage Sets...`
   - Route B：`Geometry` 画几何 → `Generate Mesh...`（自动生成 sets）
3) `Model/Materials/Assignments/Stages` 配置（Properties 表单化）
4) `Tools -> Validate Inputs... (F7)`：尽早发现 contract/schema/precheck 问题
5) `Solve -> Run (...)`：后台运行 + Cancel + diagnostics zip
6) Output 工作区：云图 + Probe/拾取 + 剖面线/时程曲线/导出图像（对标所需）
7) `File -> Save/Save As...` 归档工程；必要时 `File -> Export Case Folder...` 给 solver 团队/批量回归
8) 对标回归：`Tools -> Batch Run...` / `Tools -> Compare Outputs...` / `Tools -> Open Batch Report...`

**GUI 重点（避免后期返工）**
- 统一的“编辑-校验-运行-查看结果”节奏：每一步都有明确入口、可见状态与可恢复性（Recent Projects/Solvers、工作目录、诊断包路径）。
- Output 交互必须“所见即所得”：时间轴、步号语义、probe/剖面/时程结果要可复用/可导出。
- 可扩展：未来支持多几何、多区域、多场（u/p/应力/应变），不推翻现有 UI/数据结构。

## M0：基座（已完成）

- [x] 架构设计文档：`docs/2025121714_GeoHPEM_软件架构设计.md`
- [x] UI 规格（MVP）：`docs/ui/*`
- [x] Contract v0.1（JSON+NPZ）读写与基础校验：`src/geohpem/contract/*`
- [x] Fake solver 闭环：`python -m geohpem.cli run <case_dir> --solver fake`
- [x] GUI 骨架：Dock + 工作区 + 后台求解 + registry 浏览（占位）

---

## M1：工程文件与“打开/保存”闭环（已完成）

- [x] `.geohpem` 单文件包：`docs/PROJECT_FILE_FORMAT.md`、`src/geohpem/project/package.py`
  - DoD：Open/Save/Save As 可用；可选保存 `out/` 结果。
- [x] 版本迁移框架（migrations）：`src/geohpem/project/migrations/*`
  - DoD：具备迁移入口（预留）；开发期可不承诺跨版本加载成功，正式版再定义兼容策略。
- [x] 最近项目与恢复入口：`src/geohpem/gui/settings.py`
  - DoD：Open Recent 可用；启动询问是否恢复上次会话；关闭时未保存提示。

---

## M2：Input 工作区 MVP（已完成）

- [x] Project Explorer 结构化（Model/Mesh/Sets/Materials/Stages/out）
- [x] Properties 表单化编辑最小集（mode/gravity、stage 核心字段、material JSON）
- [x] Stage Manager（阶段列表 + diff + Add/Copy/Delete）
- [x] Pre-check（基础）+ Run 前弹窗阻止 ERROR
- [x] Input 中央区（Dashboard + Mesh Preview）支持查看网格/高亮 sets/拾取节点与单元信息（为后续“图形选集”打底）

---

## M3：网格导入与 Sets 管理（已完成）

- [x] Mesh Import（meshio）：导入 points/cells，支持从 Gmsh Physical Groups 生成 sets
- [x] Sets Manager：新增/重命名/删除（node/edge/elem sets），MVP 支持索引输入创建
- [x] Mesh Quality（基础）：tri3 最小角/长宽比统计 + 最差单元索引列表

---

## M4：几何绘制 + pygmsh 网格化（已完成）

- [x] Geometry 数据模型（Polygon2D）可序列化进 request
- [x] Geometry Dock：画多边形/拖拽顶点/边标签编辑/网格+坐标参考（缩放/平移/网格/坐标轴）
- [x] 交互绘制预览增强（Polygon/Rectangle）
  - DoD：Polygon 绘制时鼠标移动有预览线段；Rectangle 支持交互两点绘制并有预览矩形（不再固定大小）。
- [x] pygmsh 网格化：从 Polygon2D 生成 tri 网格并生成 edge/elem sets

---

## M5：渲染技术栈定版 + Output 可视化闭环（下一阶段优先）

> 目标：正式确定并落地“Output 用 VTK/PyVistaQt”，把网格与结果云图做成可用（不再是 registry 占位）。

- [x] 技术栈决策（锁定）：Input=Qt2D 编辑；Output=VTK（PyVista+PyVistaQt）
  - DoD：在文档中记录决策与边界（哪些功能放 Qt2D，哪些放 VTK），并固定依赖版本范围。
- [x] Contract Mesh -> VTK 数据转换层
  - DoD：`points + cells_* + (node/elem/ip)` 能转换为 `vtkUnstructuredGrid`（或等价）。
- [x] Result Registry -> 可视化字段选择
  - DoD：从 `result.json:registry` 动态列字段，不硬编码 `stress/p/...`。
- [x] 云图渲染（最小闭环）
  - DoD：能显示网格；能渲染标量场（先 `p`）；有 colorbar；支持变形（按 `u` 缩放，若存在）。
- [x] 探针（Probe）与基本拾取
  - DoD：点击取值（至少 node 标量）；显示当前位置与数值。
- [x] Output 后处理（剖面线/时程曲线/导出图像，MVP）
  - DoD：支持 Profile line（线采样 + 曲线 + CSV 导出）；Time history（点/单元时程 + 曲线 + CSV 导出）；Viewport 截图导出 PNG。
- [x] Output UX 增强（GUI 花功夫，避免返工）
  - DoD：交互式剖面线（视窗两点/拖拽创建）；Probe/曲线对象管理（可 pin/复用/导出）；时间轴标准化（global_steps），动画/时程不依赖猜测。
  - [x] M5.ux.1：时间轴标准化（`result.json:global_steps`）并在 UI 显示 stage/time 信息
- [x] M5.ux.2：交互式剖面线（Pick 2 points）+ Profiles 列表管理（Plot/Remove）
- [x] M5.ux.3：Probe Pin/复用：Pinned Nodes/Elements 列表 + Time history 可选来源（而非“最后一次拾取”）
- [x] M5.ux.4：交互式剖面线（拖拽/编辑/多条 overlay）+ 保存到工程（随 project 保存：`ui_state.json`）
- [x] M5.ux.5：批量导出（MVP）：steps → PNG（保持当前相机视角；GIF/MP4 后续可选）
- [x] M5.ux.6：Output 面板重排（减少上下移动）
  - DoD：左侧按“Field / Profiles / Pins”分组（Profiles/Pins 使用标签页），常用动作就近（Profile/Time history/Pin/Export），并保留右键菜单快捷入口。

---

## M6：选择/命中测试与稳定 ID（与可视化同等重要）

> 目标：为后续复杂 UI/撤销重做/引用关系打地基，避免后期返工。

- [x] 稳定 ID 方案（全局唯一，第一版）
  - 覆盖：geometry 实体、sets、materials、stages、loads、bcs、output_requests
  - DoD：`stages/materials/geometry/sets_meta` 自动补 `uid`；旧工程打开不报错且可继续编辑/保存。
- [x] 选择模型（Selection Model，最小版）
  - DoD：Project/Stage 选择统一走 SelectionModel，驱动属性面板与阶段面板。
- [x] Hit-test/拾取策略（Input/Output 分别实现，第一版）
  - DoD：Input（Qt2D）能拾取顶点/边并显示其 uid；Output（VTK）能拾取节点/单元并显示所属 sets 与数值（若有）。
- [x] 迁移旧数据（无 id 的 request）到带 id 的结构（第一版）
  - DoD：加载 `.geohpem`/case folder 时自动补齐 `uid`（保存时写入工程文件）。

---

## M12：交互选集与“从图形创建 sets”（强烈建议尽早补齐）

> 目标：把“手工输入索引创建 set”升级为“拾取/累积选择 → 一键生成 sets”，显著提升建模效率与可用性。
- [x] M12.1：Input Mesh Preview 选择缓存（node/element）
  - DoD：能将“最后一次拾取”的 node/cell 加入选择列表；支持清空；显示数量与类型。
- [x] M12.2：从选择一键创建 sets（写入 mesh + sets_meta）
  - DoD：支持 `node_set__<name>` 与 `elem_set__<name>__<cell_type>`；自动生成/更新 `request.sets_meta` 的 label；Undo/Redo 可回退。
- [x] M12.3：选择高亮与快速校验
  - DoD：创建后可在 Preview 下拉中直接高亮新 set；precheck 对“引用不存在 set”给出更靠前的提示。
- [x] M12.4：从拾取创建 edge sets（用于边界条件/荷载）
  - DoD：支持“最后两次拾取节点组成一条边”→累积多条边→一键创建 `edge_set__<name>`，并可在 Preview 中高亮/显示。
- [x] M12.5：框选/刷选（矩形选择）以批量选择节点/单元（Input Mesh Preview）
  - DoD：支持 Box select nodes / Box select elements；支持“替换/追加”与“刷选模式（保持激活）”；与 selection 叠加显示与 Create set 打通。
- [ ] M12.6：沿边刷选（polyline）/按边界提取整条边界（工程常用）
  - [x] M12.6a：按边界提取整条边界（auto，按外包框极值）
    - DoD：Input Mesh Preview 提供 `Boundary helpers (auto)`（All/Bottom/Top/Left/Right），可一键选中边界边并直接创建 `edge_set__*`。
  - [ ] M12.6b：沿边刷选（polyline）与“按边界提取整条边界（按连通段/按环）”
    - [x] M12.6b1：polyline 沿边刷选（基于边界图最短路径，MVP）
      - DoD：Input Mesh Preview 提供 `Polyline/Finish/Clear`；在 polyline 模式下依次拾取边界节点，会沿边界最短路径补齐中间边并加入 edge 选择；可直接 `Create edge set...`。
    - [x] M12.6b2：按拾取提取边界连通段（component，MVP）
      - DoD：提供 `Component from pick`，基于最后一次拾取节点提取其所在边界连通段并加入 edge 选择。
    - [ ] M12.6b3：吸附与“整条边界环”
      - [x] M12.6b3a：近边界点击吸附（MVP）
        - DoD：polyline/component 支持“点在边界附近”也可自动吸附到最近边界节点（减少精确点选负担）。
      - [ ] M12.6b3b：整条边界环/孔洞边界提取（长期）
        - DoD：支持提取“整个边界环/外边界/孔洞边界”；可选同时生成对应 node_set。

---

## M13：交互可用性增强（选择/右键菜单/快捷键）

> 目标：把“能用”提升到“顺手”，减少鼠标移动与重复操作成本。

- [x] M13.1：VTK 右键上下文菜单（Input/Output）
  - DoD：右键弹出菜单（清空选择、创建 set、Fit、切换 Replace/Brush、导出图像、Profile/History、Pin 等），与当前工作区语义一致。
- [ ] M13.2：选择集合运算（Replace/Add/Subtract/Invert）
  - [x] M13.2a：Input 选择运算（Replace/Add/Subtract）
    - DoD：Box/边界/Polyline 都支持 Add/Replace/Subtract（以 `Replace/Subtract` 控件为入口）；行为一致且可预期。
  - [x] M13.2b：Input Invert（nodes/elems/edges）
    - DoD：Mesh Preview 右键菜单提供 `Invert nodes/elements/edges`，用于快速反选。
  - [ ] M13.2c：更强的选择运算与快捷键（长期）
    - DoD：支持 Subtract 的快捷键/修饰键（如按住 Alt 拖框）；支持 Invert 的快捷键；可配置默认行为。
- [ ] M13.3：常用快捷键与 Esc 取消
  - [x] M13.3a：`Esc` 取消（Input/Output）与 `C` 清空（Input）
    - DoD：Input 的 box/polyline 可用 `Esc` 退出；Output 的 profile edit 可用 `Esc` 取消；Input 支持 `C` 清空选择。
  - [ ] M13.3b：`B` 进入 box 与菜单快捷键展示
    - DoD：`B` 快速进入 Box nodes，`Shift+B` 进入 Box elems；右键菜单项展示快捷键（如 `B`、`Shift+B`、`C`、`Esc`）。
- [ ] M13.4：选择反馈增强
  - DoD：状态栏/面板显示“当前选中数量 + 类型拆分 + 来源（拾取/框选/边界）”；高亮对比度在深浅主题下都清晰。

---

## M14：用户教程与可用性收敛（面向交付）

> 目标：让新用户不看代码也能跑通闭环；把“容易踩坑”的点前置消解。

- [x] M14.1：2-3 个 step-by-step 案例教程（从创建项目到后处理）
  - DoD：提供三篇教程覆盖“画几何→网格化”“导入现成网格（含 npz）”“打开 case folder 专注后处理”；教程可按步骤复现。
- [x] M14.2：补齐 `.npz` 网格导入（Import Mesh 支持 Contract mesh.npz）
  - DoD：`File -> Import Mesh...` 可直接选择 `.npz`（contract mesh），并正确生成导入报告与 sets；无需用户绕路 Open Case Folder。
- [ ] M14.3：新手模式（长期，可选）
  - DoD：提供“下一步建议/缺失项提示”（例如缺少 mesh/缺少 output_requests/缺少 stages），并可一键跳转到对应面板。

---

## M7：单位与坐标约定（必须提前锁定）

> 目标：内部统一、显示可切换，避免后处理标尺/探针/输出对标混乱。

- [x] 单位体系约定（内部/显示）
  - DoD：`docs/UNITS_AND_COORDS.md` 明确 `request.unit_system` 的含义与 v0.1 透传策略；UI 支持显示单位切换。
- [x] 坐标与符号约定（2D）
  - DoD：`docs/UNITS_AND_COORDS.md` 明确全局坐标（X/Y）、重力方向默认、axisymmetric 轴线约定（应力符号预留）。
- [x] 单位换算工具与 UI 展示（最小）
  - DoD：`View -> Display Units...` 可切换长度/压强显示单位；Geometry 坐标读数与 Output Probe/色标随之更新。

---

## M8：域模型与命令体系（在 M6 之后推进）

- [ ] Domain Model 收敛（替代散落 dict，建议分阶段推进）
  - [x] M8.1：以稳定 uid 为中心的编辑入口
    - DoD：Stage 编辑不再依赖 index；统一使用 `stage.uid`（避免增删阶段后的引用漂移）。
  - [x] M8.2：Domain ops（纯函数）覆盖核心变更
    - DoD：model/material/stage/sets 的主要修改都有对应 `domain/*` helper，ProjectModel/SetsDialog 不直接散写 dict；复制阶段会重置嵌套对象 uid。
  - [ ] M8.3：UI 表单化与强类型对象（可选，长期）
    - [x] M8.3.1：BC/Load 表格编辑器（最小可用）
      - DoD：stage.bcs / stage.loads 支持表格增删改；保持 `uid` 稳定；可从 sets 下拉选择 set 名称；支持 JSON->Table 导入以保留高级用法。
    - [x] M8.3.2：Assignments 表单化（材料分配）
      - DoD：element_set/cell_type/material_id 可下拉选择；缺失引用给出即时提示。
    - [x] M8.3.3：Output Requests 表单化（阶段/全局）
      - DoD：支持基于 capabilities 的字段/位置选择；every_n 等参数表单化；仍允许高级用户直接编辑 JSON（可切换）。
    - [x] M8.3.4：校验与导出一致性
      - DoD：`Tools -> Validate Inputs...` 提供 precheck + schema 校验；`Solve -> Run` 运行前同样校验；`File -> Export Case Folder...` 与保存/运行前均自动 normalize（ids/sets_meta）。
- [x] Undo/Redo（基础版，已实现）
  - DoD：至少覆盖 model/gravity、stage 增删改、material 改、geometry 改、mesh 改。
- [x] Undo/Redo（增强：细粒度 + 合并策略）
  - DoD：拖拽顶点/批量编辑可合并为单条命令；Redo/Undo 状态与菜单/工具栏一致。

---

## M9：solver 集成增强（capabilities 驱动）

- [x] Solver Manager（选择/显示 capabilities，缓存）
  - DoD：GUI 可选择 solver（fake / python:<module>），可检查并展示 `solver.capabilities()`，运行时使用所选 solver。
- [x] capabilities 驱动 UI 灰置/提示（mode/analysis_type/输出字段，MVP）
  - DoD：根据 capabilities 灰置 `mode` 与 `analysis_type` 的不支持选项；Run 前 precheck 会对不支持项给出 ERROR 并阻止运行；`output_requests` 中不支持字段给出 WARN，并提供 “Add Output Requests...” 快捷添加。
- [x] 运行监视增强（取消 + 诊断包 zip，MVP）
  - DoD：Tasks 面板可 Cancel（best-effort）；失败/取消时自动生成 `_diagnostics/diag_*.zip` 并在弹窗与 Log 中提示路径。
- [x] 错误码映射（可选，后续增强）
  - DoD：将 solver 的错误类型/错误码映射为标准化错误列表，并支持“一键打包上传”。

---

## M10：对标与回归（工程化保障）

- [x] 批量跑算例（Case Runner，MVP）
  - DoD：`python geohpem_cli.py batch-run <root> --solver ...` 可批量运行并输出 `batch_report.json`（含成功/失败/耗时/诊断包路径）；可选 `--baseline <root>` 写入末步数组差异统计。
- [x] GUI 批量跑算例（Batch Run，MVP）
  - DoD：GUI 菜单提供 `Tools -> Batch Run...`，可选择 root/solver/baseline/report，显示进度，支持 Cancel（best-effort），并提示报告路径。
- [x] 结果对比（差值云图/曲线/统计，MVP）
  - DoD：GUI 提供 `Tools -> Compare Outputs...`，可打开 A/B 输出（或 case folder），显示差值云图（A-B），并可导出 step-curve CSV（mean/min/max）。
- [x] 基准性能记录（耗时/内存，MVP）
  - DoD：`batch_report.json` 记录 `elapsed_s`，并在可用时记录 `rss_start_mb/rss_end_mb`（psutil 可选）。
- [x] Batch Report 浏览器（GUI，MVP）
  - DoD：GUI 提供 `Tools -> Open Batch Report...`，可加载 `batch_report.json` 并表格浏览/筛选/打开路径。

---

## M11：交付与插件化（长期）

- [x] solver submodule 接入规范文档（给 solver 团队）：`docs/SOLVER_SUBMODULE_INTEGRATION.md`
- [x] 多 solver 并存与选择（FEM/HPEM/实验分支，MVP：Recent Solvers 快捷切换）
- [ ] 打包与发布（conda/zip/installer，待定）

---

## M15：真实求解闭环（Contract v0.2 + Reference Solvers）

> 背景：Fake solver 已验证了 GUI/IO/可视化闭环，但材料/边界/荷载/阶段对求解器的真实驱动仍缺“可照着做”的样板。
> 本阶段目标是：**一步到位设计“面向 PFEM/HPEM 的可执行契约”**（分小步落地），并提供 2~3 个“参考求解器（reference solvers）”作为 solver 团队的接口范例与回归基准。

### M15.1：Contract v0.2（可执行的最小建模语义）

- [ ] v0.2 schema + 文档（materials/bcs/loads/assignments/stages）
  - DoD：新增 `docs/CONTRACT_V0_2.md`，明确字段、默认值、单位/坐标约定、示例；并在 `src/geohpem/contract/*` 增加 v0.2 校验入口（兼容 v0.1）。
- [ ] BC/Load/Material/Assignment 的最小类型集（先做“能跑通”）
  - DoD：至少支持：
    - Material：`linear_elastic`（E, nu, rho 可选）
    - Assignment：`element_set` → `material_id`（按 set 分配）
    - BC：`displacement`（ux/uy 固定位移 or 约束），作用于 `node_set`（或由 `edge_set` 自动转 node_set）
    - Load：`gravity`（body force）与 `traction`（边界线力），作用于 `edge_set`
    - Stage：`analysis_type=static`、steps/dt（即便 solver 不用 dt，也保留语义）

### M15.1+：PFEM/HPEM “一步到位”扩展点（不要推翻重来）

> 这部分不要求一次性全部实现 UI，但契约与数据结构要先定边界，避免后续返工。

- [ ] 离散化描述统一：Mesh / Particles / Hybrid
  - DoD：Contract 支持声明 `discretization`（mesh-only / particles-only / hybrid），并允许 solver 返回“网格重构/粒子重采样”等事件元数据；事件频率不做限制（每步/每子步/任意），平台按时间轴展示即可。
- [ ] 粒子相关输入（可选字段，但字段与语义先定）
  - DoD：支持粒子生成/导入的描述（seed strategy / initial particles / particle sets），以及与材料/区域/阶段的引用方式（uid 体系稳定）。
- [ ] 大变形/重网格化输出约定（平台侧可视化必须吃得下）
  - DoD：结果允许同时包含：
    - mesh-based fields（u/stress/strain 等）
    - particle-based fields（vp/pp/...）
    - remeshing events（step 内多子步/重建次数）与映射关系（best-effort）

- [ ] 输出“帧/子步”语义统一（适配 PFEM/HPEM 的可变输出频率）
  - DoD：result.json 支持 `frames[]`（或 `global_steps[]` 扩展）携带：`time / stage_id / stage_step / substep / dt / events[] / mesh_ref / particles_ref`；平台 Output 以 frame 为基本播放单位（Step slider 对应 frame index）。

### M15.2：Solver API 规范收敛（给 solver 团队照抄）

- [ ] `capabilities()` 的字段清单与语义（最小）
  - DoD：明确 solver 支持的 `modes`（plane_strain/plane_stress/axisymmetric）、`analysis_types`（static/dynamic 等）、支持的 material/bc/load 类型、输出字段（registry）。
- [ ] `solve(request, mesh, *, workdir, progress_cb)` 约定（最小）
  - DoD：明确输入（内存 dict + np arrays）、输出（`result.json + arrays.npz`）、progress/cancel/异常错误码的约定；给出最小示例实现与“常见错误如何报”。

> 补充：为 PFEM/HPEM 预留“多输出载体”能力（平台不限制 solver 只输出一个网格）：
> - `result.npz` 允许同时包含 `mesh_*` 与 `particles_*` 命名空间（或多个 npz 文件并由 result.json 索引）。

### M15.3：参考求解器 A（开源 FE：线弹性静力，PLAXIS 对标基础）


- [ ] `solver_reference_elastic`（plane strain/stress，tri3/quad4）
  - DoD：支持：
    - 线弹性材料（E, nu）
    - 位移边界（ux/uy fixed 或 prescribed）
    - 重力（rho*g）与边界 traction
    - 基本应力输出（sx/sy/sxy）与 `vm`（element）
    - 输出 `u (node)` + `vm (element)`，并生成 `meta.global_steps`（time/step/stage）
- [ ] 参考算例（case folders）+ 基准输出
  - DoD：新增 `_Projects/cases/reference_elastic_*`（例如：悬臂梁、地基受载、重力自重），可一键运行并在 Output 中可视化；提供“解析/文献/数值对比说明”。

### M15.4：参考求解器 B（渗流/孔压：Darcy/Poisson）

- [ ] `solver_reference_seepage`（p 场，2D steady）
  - DoD：支持：
    - 材料渗透系数 k（各向同性先）
    - 边界条件：p=常值（Dirichlet）、通量（Neumann）
    - 输出 `p (node)` + `q (element 或边界)`（至少 p 可云图与 probe）
- [ ] 参考算例（case folders）+ 基准输出
  - DoD：新增 `_Projects/cases/reference_seepage_*`（例如：矩形渗流、分层渗流），具备可对标的边界条件与结果截图/曲线。

### M15.5：参考求解器 C（可选，二选一：动力 or u-p 耦合）

- [ ] C1：动力学（Newmark）最小实现（弹性动力）
  - DoD：支持 `analysis_type=dynamic`，输出 `u(t)`、`v(t)`（至少一个点的时程可对标）。
  - 或：
- [ ] C2：Biot u-p（最小耦合，科研对标基础）
  - DoD：至少实现一个小网格的稳健耦合示例（哪怕是简化版），用于后续 HPEM 对比接口/输出形式。

### M15.6：平台侧配套（让 solver 示例可被 GUI 充分驱动）

- [ ] GUI 表单与预设：Material/BC/Load 的“向导式添加”
  - DoD：`Properties` 里提供 `Add...` 按钮与模板（例如“Fix bottom”、“Traction on top”、“Gravity”），减少用户手写 JSON。
- [ ] Validate 扩展：对 v0.2 语义做更强校验
  - DoD：缺失 assignment/material、引用不存在 sets、BC/Load 类型不支持等给出 ERROR；数值范围给 WARN（例如 nu>0.49）。
- [ ] 输出对标清单 v0（逐步补齐）
  - DoD：`docs/OUTPUT_CHECKLIST.md` 记录“最重要的对标输出”（云图字段、剖面、时程、反力等）并与参考算例绑定。

### 需要你协助确认/讨论的关键点（建议尽快敲定，避免返工）

1) **参考求解器开源依赖是否可接受**：`scikit-fem` / `scipy` / `sfepy` 你更倾向哪套？是否有许可证/离线环境约束？
2) **最小材料模型**：v0.2 是否先只做 `linear_elastic`（对标基础），还是必须同时包含 `mohr_coulomb`（哪怕简化）？
3) **BC/Load 作用域**：默认要求作用于 `node_set` 还是允许 `edge_set` 并由平台自动投影到节点？
4) **符号约定**：压应力正负、重力方向（已在 UNITS_AND_COORDS 写了默认，但求解/对标要严格一致）。
5) **PFEM/HPEM 关键特性清单**（请给“必须从一开始支持”的最小集合）：
   - 是否存在重网格化/拓扑变化？频率大概如何表达（每步一次/每子步多次）？
   - 是否粒子需要 sets（粒子组/材料组）与边界作用（速度/压力/接触）？
   - 输出最希望对标哪些：粒子轨迹、自由面、局部剖面、反力/能量等？

> 当前你的反馈（已采纳）：
> - “部分算法存在，频率可以灵活一点”：平台将以 frame/event 机制承载可变输出频率，不强制 solver 贴合固定步号节奏。
> - “你不懂算法无法准确回答”：平台先给出一套 PFEM/HPEM 友好的契约扩展草案与参考实现样式，solver 团队可在此基础上对齐。

---


## 建议执行顺序（最短路径到“可用软件闭环”）

1) **M5**（先把 Output 可视化闭环做实：VTK/PyVistaQt）  
2) **M6**（稳定 ID + 选择/拾取模型，避免后期返工）  
3) **M7**（单位/坐标约定，保证探针/色标/对标一致）  
4) **M9**（solver manager/capabilities 入口收口）  
5) **M15**（Contract v0.2 + Reference Solvers：让“真实求解闭环”可照抄）  
6) **M10**（对标/回归，工程化收口）  
7) 再逐步收敛 **M8 Domain Model** 与 UI 细节完善
