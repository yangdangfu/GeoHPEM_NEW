# GeoHPEM_NEW 开发计划与 Checklist

本文件用于把“软件可用闭环”拆解成可执行的步骤。每个条目都有 **Definition of Done（DoD）**，完成后在方括号中打勾。

> 术语：
> - **Case Folder**：包含 `request.json + mesh.npz` 的算例目录（可带 `out/`）。
> - **Contract**：平台与 solver 的数据契约（JSON + NPZ）与 `capabilities()/solve()` API。
> - **Registry**：`result.json` 中的结果项索引，驱动后处理 UI。

---

## M0：当前状态（已具备的基座）

- [x] 架构设计文档落地：`docs/2025121714_GeoHPEM_软件架构设计.md`
  - DoD：文档包含分层、Contract v0.1、里程碑与目录建议。
- [x] UI 规格（MVP）文档：`docs/ui/*`
  - DoD：主窗口/工作区/对话框/交互模型均有页面说明。
- [x] Contract v0.1 读写（JSON+NPZ）与基础校验：`src/geohpem/contract/*`
  - DoD：能读写 case folder；错误输入能给出可理解的报错。
- [x] Fake solver + CLI 闭环跑通：`python -m geohpem.cli run <case_dir> --solver fake`
  - DoD：生成 `out/result.json + out/result.npz`。
- [x] GUI 骨架：Dock + 工作区切换 + 后台求解线程（fake）+ registry 浏览占位
  - DoD：在安装 PySide6 的环境中可启动，能打开 case folder，点击 Run 生成 out 并在 Output 工作区看到 registry 列表。

---

## M1：工程文件与“打开/保存”闭环（强烈建议先做）

- [x] 引入工程文件格式 `.geohpem`（单文件包）
  - 内容建议：`manifest.json`（元数据/版本/最近运行信息） + `request.json` + `mesh.npz` + `out/*`（可选） + `attachments/`
  - DoD：能 Save/Save As 生成单文件；Open 能解包到临时目录或内存加载。
- [x] 工程版本迁移框架（migrations）
  - 规则：只向前兼容；每次 schema 变更有迁移脚本；旧工程打开时自动升级并提示
  - DoD：至少提供 `0.1 -> 0.1` 的框架示例（空迁移也行），并在代码里有入口。
- [x] 最近项目与崩溃恢复（轻量）
  - DoD：记录最近打开的工程；未保存修改提示；异常退出后给出“恢复上次会话”入口（先仅记录路径）。

---

## M2：Input 工作区 MVP（可编辑的建模数据）

> 当前 Input Workspace 是占位。此里程碑目标是：不依赖几何绘制，先把“导入网格 + 配置阶段/边界/材料/输出”做成可用 UI。

- [x] Project Explorer：对象树结构化（按 Geometry/Mesh/Sets/Materials/Stages/Results）
  - DoD：树节点与 request 数据同步；支持右键新增/删除/复制（MVP 可只实现新增/删除）。
- [x] Properties：从“只读 JSON”升级为“表单化编辑（最小集）”
  - 最小集：`model.mode`、`gravity`、stage 的 `analysis_type/num_steps/dt`、材料 `model_name/parameters`（JSON编辑器即可）、输出请求（列表编辑）
  - DoD：修改后能写回内存模型，并能导出/保存成 `request.json`。
- [x] Stage Manager：阶段列表 + 阶段变更摘要（相对上一阶段）
  - DoD：选择阶段时，显示该阶段与上阶段差异（启用/停用 sets、BC/Load 变化）。
- [x] Pre-check 面板（基础）
  - 检查项：schema_version、stages 非空、mesh 至少包含 points 与一种 cells、assignments 与 set 引用存在性
  - DoD：Run 前弹窗展示检查结果；严重错误阻止运行。

---

## M3：网格导入与 sets 管理（“导入现成网格”路线）

- [x] Mesh Import Dialog（gmsh/meshio）
  - 输入：`.msh` / 其他 meshio 支持格式
  - 行为：导入 points/cells；从物理组生成 sets（若存在）；保存为 `mesh.npz`
  - DoD：至少能导入一个 gmsh msh 并生成可运行 case folder。
- [x] Sets Editor（NodeSet/EdgeSet/ElementSet）
  - 功能：创建/重命名/删除；从选择生成；显示元素数量；高亮显示（后续接 Viewport）
  - DoD：能在 UI 中创建一个 node_set 并被 BC 引用；保存后再打开不丢失。
- [x] Mesh 质量检查（基础指标）
  - 2D 三角形：最小角、长宽比；四边形：扭曲度/长宽比（先做三角形也可）
  - DoD：质量面板能列出统计，并能定位“最差的 N 个单元”（先在列表中展示索引即可）。

---

## M4：几何绘制 + pygmsh 网格化（“画几何→网格化”路线）

> 目标：实现最小几何编辑闭环，不做复杂 CAD 约束，先满足科研/工程常见几何。

- [x] Geometry Layer（数据模型）
  - 支持：点、线段、圆弧/样条（可延后）、多边形域、孔洞、分区、物理组标签
  - DoD：几何能序列化进工程文件；能从几何生成 pygmsh 输入。
- [x] 几何编辑器（MVP 工具）
  - 工具：画多边形、拖拽点、捕捉、删除、闭合检查
  - DoD：能画一个矩形域并定义边界物理组（bottom/left/right/top）。
- [x] pygmsh 网格化对话框
  - 参数：全局尺寸、局部尺寸（按边/域）、生长率；输出单元类型（tri/quad 优先 tri）
  - DoD：一键生成 mesh.npz，并可直接求解（fake）。

---

## M5：求解器集成（真实 solver 接入前的“契约固化”）

- [ ] Solver Manager（选择/显示 capabilities）
  - 支持：`fake`、`python:<module>`；展示 capabilities 并缓存
  - DoD：UI 能看到 solver 支持的 analysis_types/fields/results。
- [ ] Capabilities 驱动 UI 的灰置/提示
  - 例：solver 不支持 `axisymmetric` 时禁止选择；不支持 `p` 字段时孔压 BC/输出不可选
  - DoD：至少实现 3 个关键灰置规则（mode、analysis_type、输出字段）。
- [ ] 求解运行监视（Run Monitor）
  - 内容：进度、阶段/步、日志、取消按钮
  - DoD：fake solver 进度能实时更新；取消（先平台级）能停止等待并标记 canceled（fake 可模拟）。
- [ ] 诊断包导出（Debug Bundle）
  - 内容：request/mesh、solver capabilities、运行日志、异常堆栈（若有）
  - DoD：失败时一键导出 zip，并提示保存位置。

---

## M6：Output 工作区 MVP（应力/应变/孔压云图与过程浏览）

> 目标：把 registry→显示字段→选择步→渲染 云图这条链打通。渲染建议 PyVistaQt（VTK）。

- [ ] Result Browser：阶段/步/时间选择
  - DoD：能选择 step 并驱动渲染刷新（即使先渲染占位也要联动）。
- [ ] Field Selector：从 registry 动态生成字段列表
  - DoD：无硬编码字段名；registry 改变后列表自动更新。
- [ ] Color Map 面板（基础）
  - 功能：自动/手动范围、色带、单位显示、缺失值处理
  - DoD：至少对 `p` 标量场生效。
- [ ] 2D 渲染管线（首选 PyVistaQt）
  - 能力：显示网格、叠加标量场、简单变形（按 u 缩放）
  - DoD：能在示例 case 上显示 `p` 的颜色映射；能切换显示 `u_mag`（若平台派生或 solver 输出）。
- [ ] 探针与剖面线（基础）
  - 探针：点击取值；剖面：两点定义线，沿线采样输出曲线
  - DoD：至少实现探针；剖面可作为下一小步。

---

## M7：数据模型与编辑一致性（从“编辑 JSON”走向“强类型域模型”）

> 当前可先用 dict 驱动 MVP，但中期必须收敛为稳定的 Domain Model，以支撑复杂 UI、撤销/重做、阶段差异等。

- [ ] 建立 Domain Model（dataclasses/pydantic 二选一）
  - 对象：Project、Mesh、Sets、Material、Stage、BC、Load、OutputRequest
  - DoD：UI 不直接编辑原始 dict，而是编辑 domain；导出时生成 request/mesh dict。
- [ ] Undo/Redo（命令栈）
  - DoD：至少支持“修改属性/新增删除阶段/新增删除材料”的撤销重做。

---

## M8：对标与回归（工程化保障）

- [ ] Case Runner（批量跑算例）
  - DoD：指定目录批量运行，输出汇总表（成功/失败/耗时/最大位移等）。
- [ ] 结果对比（Compare）最小工具
  - DoD：同一 case 不同 solver/版本输出的 `p/u` 做差值统计与简单可视化（哪怕先 CSV）。
- [ ] 基准与性能（可选）
  - DoD：记录关键 case 的运行时间与内存（先粗略）。

---

## M9：交付与插件化（面向 solver submodule/HPEM 的长期演进）

- [ ] solver submodule 接入规范文档（给 solver 团队）
  - DoD：包含 API、Contract、capabilities 示例、错误码与进度回调规范。
- [ ] 插件机制（可选）
  - DoD：允许多个 solver 并存（FEM/HPEM/实验分支），并在 UI 中选择。
- [ ] 打包与发布（内部）
  - DoD：可生成可运行包/安装包（后续确定分发方式：conda/zip/installer）。

---

## 建议的执行顺序（最短路径到“可用软件闭环”）

1) **M1 工程文件**（打开/保存稳定）  
2) **M2 Input 可编辑**（能配阶段/边界/输出）  
3) **M3 网格导入 + sets**（真实数据来源）  
4) **M5 solver 集成增强**（capabilities 驱动 UI，诊断包）  
5) **M6 Output 云图**（应力/应变/孔压可视化）  
6) 再补 **M4 几何网格化** 与 **M7 强类型/撤销重做**
