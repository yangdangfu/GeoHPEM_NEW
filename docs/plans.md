# GeoHPEM_NEW 开发计划与 Checklist（可迭代调整）

本文件用于把“软件可用闭环”拆解成可执行步骤。每个条目都有 **Definition of Done（DoD）**，完成后在方括号中打勾。

> 术语：
> - **Case Folder**：包含 `request.json + mesh.npz` 的算例目录（可带 `out/`）。
> - **Contract**：平台与 solver 的数据契约（JSON + NPZ）与 `capabilities()/solve()` API。
> - **Registry**：`result.json` 中的结果项索引，驱动后处理 UI。

---

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
  - DoD：具备迁移入口；对未知版本给出明确错误。
- [x] 最近项目与恢复入口：`src/geohpem/gui/settings.py`
  - DoD：Open Recent 可用；启动询问是否恢复上次会话；关闭时未保存提示。

---

## M2：Input 工作区 MVP（已完成）

- [x] Project Explorer 结构化（Model/Mesh/Sets/Materials/Stages/out）
- [x] Properties 表单化编辑最小集（mode/gravity、stage 核心字段、material JSON）
- [x] Stage Manager（阶段列表 + diff + Add/Copy/Delete）
- [x] Pre-check（基础）+ Run 前弹窗阻止 ERROR

---

## M3：网格导入与 Sets 管理（已完成）

- [x] Mesh Import（meshio）：导入 points/cells，支持从 Gmsh Physical Groups 生成 sets
- [x] Sets Manager：新增/重命名/删除（node/edge/elem sets），MVP 支持索引输入创建
- [x] Mesh Quality（基础）：tri3 最小角/长宽比统计 + 最差单元索引列表

---

## M4：几何绘制 + pygmsh 网格化（已完成）

- [x] Geometry 数据模型（Polygon2D）可序列化进 request
- [x] Geometry Dock：画多边形/拖拽顶点/边标签编辑/网格+坐标参考（缩放/平移/网格/坐标轴）
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

- [ ] Domain Model 收敛（替代散落 dict）
  - DoD：UI 编辑 domain 对象；导出时生成 request/mesh dict；序列化稳定。
- [x] Undo/Redo（基础版，已实现）
  - DoD：至少覆盖 model/gravity、stage 增删改、material 改、geometry 改、mesh 改。
- [ ] Undo/Redo（增强：细粒度 + 合并策略）
  - DoD：拖拽顶点/批量编辑可合并为单条命令；Redo/Undo 状态与菜单/工具栏一致。

---

## M9：solver 集成增强（capabilities 驱动）

- [x] Solver Manager（选择/显示 capabilities，缓存）
  - DoD：GUI 可选择 solver（fake / python:<module>），可检查并展示 `solver.capabilities()`，运行时使用所选 solver。
- [x] capabilities 驱动 UI 灰置/提示（mode/analysis_type/输出字段，MVP）
  - DoD：根据 capabilities 灰置 `mode` 与 `analysis_type` 的不支持选项；Run 前 precheck 会对不支持项给出 ERROR 并阻止运行；`output_requests` 中不支持字段给出 WARN，并提供 “Add Output Requests...” 快捷添加。
- [x] 运行监视增强（取消 + 诊断包 zip，MVP）
  - DoD：Tasks 面板可 Cancel（best-effort）；失败/取消时自动生成 `_diagnostics/diag_*.zip` 并在弹窗与 Log 中提示路径。
- [ ] 错误码映射（可选，后续增强）
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

---

## M11：交付与插件化（长期）

- [ ] solver submodule 接入规范文档（给 solver 团队）
- [ ] 多 solver 并存与选择（FEM/HPEM/实验分支）
- [ ] 打包与发布（conda/zip/installer，待定）

---

## 建议执行顺序（最短路径到“可用软件闭环”）

1) **M5**（先把 Output 可视化闭环做实：VTK/PyVistaQt）  
2) **M6**（稳定 ID + 选择/拾取模型，避免后期返工）  
3) **M7**（单位/坐标约定，保证探针/色标/对标一致）  
4) **M9**（真实 solver 接入与 capabilities 驱动 UI）  
5) **M10**（对标/回归，工程化收口）  
6) 再逐步收敛 **M8 Domain Model** 与 UI 细节完善
