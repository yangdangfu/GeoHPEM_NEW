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

- [ ] 稳定 ID 方案（全局唯一）
  - 覆盖：geometry 实体、sets、materials、stages、loads、bcs、output_requests
  - DoD：所有对象都有 `id`；引用只通过 `id`；UI 展示名可变不影响引用。
- [ ] 选择模型（Selection Model）
  - DoD：统一选择事件：选中对象 -> 属性面板；支持多选与高亮（先最小）。
- [ ] Hit-test/拾取策略（Input/Output 分别实现）
  - DoD：Input（Qt2D）能拾取顶点/边/域；Output（VTK）能拾取节点/单元并映射回 sets 或结果值。
- [ ] 迁移旧数据（无 id 的 request）到带 id 的结构
  - DoD：打开旧工程时自动补 id，不破坏兼容。

---

## M7：单位与坐标约定（必须提前锁定）

> 目标：内部统一、显示可切换，避免后处理标尺/探针/输出对标混乱。

- [ ] 单位体系约定（内部/显示）
  - DoD：内部采用统一 SI（或统一基准），`unit_system` 仅用于显示/输入换算；明确压力单位等。
- [ ] 坐标与符号约定（2D）
  - DoD：定义全局坐标（X/Y）、重力方向默认、axisymmetric 轴线约定、应力符号约定（压正/拉正）在文档中明确。
- [ ] 单位换算工具与 UI 展示
  - DoD：Properties/Probe/色标显示支持单位切换（先最小：长度/力/压强）。

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

- [ ] Solver Manager（选择/显示 capabilities，缓存）
- [ ] capabilities 驱动 UI 灰置/提示（mode/analysis_type/输出字段）
- [ ] 运行监视增强（取消协作、错误码映射、诊断包 zip）

---

## M10：对标与回归（工程化保障）

- [ ] 批量跑算例（Case Runner）
- [ ] 结果对比（差值云图/曲线/统计）
- [ ] 基准性能记录（耗时/内存）

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
