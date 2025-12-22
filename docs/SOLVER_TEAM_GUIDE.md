# Solver 团队接入指南（GeoHPEM Contract v0.2）

本文面向“只写算法、不擅长封装”的 solver 团队：目标是在不理解 GUI/工程文件细节的前提下，按固定接口把算法接入 GeoHPEM 平台，并能被 GUI/CLI 驱动、输出结果用于后处理与对标。

## 1. 你需要实现什么（最小闭环）

你们提供一个 **Python 包/子模块**（建议作为 git submodule 放进主仓库），对外暴露一个“求解器对象”，至少实现：

- `capabilities() -> dict`
- `solve(request: dict, mesh: dict, *, callbacks: dict | None = None) -> tuple[meta: dict, arrays: dict]`

平台侧负责：
- 读写工程文件（`.geohpem`）与 case folder（`request.json + mesh.npz`）
- GUI 里编辑 `request`（材料/分配/阶段/输出请求）
- 调用 solver 的 `solve()`，把结果写到 `out/result.json + out/result.npz`
- Output 里做云图/探针/剖面线/时程曲线/导出

你们负责：
- 解释 `request.json` 中与你们算法相关的字段
- 基于 `mesh.npz` 的网格/集合信息，组装方程、施加 BC/Load、求解
- 生成平台可识别的结果数组（写进 `result.npz`）

## 2. 输入数据（request.json + mesh.npz）

### 2.1 request.json（Contract v0.2）

规范文档：
- `docs/CONTRACT_V0_2.md`

关键点：
- 当前开发期不要求跨版本兼容，但 **请以 v0.2 为主**（平台同时接受 `0.1/0.2` 便于过渡）。
- 平台不会求值表达式/脚本：如果你们需要时变或表达式，按 v0.2 的“透传对象 value”自行解释即可。

你们通常会用到：
- `model.mode`：`plane_strain | plane_stress | axisymmetric`
- `materials{}`：材料表（`model_name + parameters`，语义由 solver 决定）
- `assignments[]`：把 `element_set + cell_type` 映射到 `material_id`
- `stages[]`：阶段序列（每阶段 `analysis_type / bcs / loads / output_requests`）

### 2.2 mesh.npz（Contract mesh dict）

mesh 是一个 dict（由 npz 读取），常见字段：
- `points`: `(N,2)` 节点坐标
- `cells_tri3`: `(Nt,3)` / `cells_quad4`: `(Nq,4)` 单元连接
- sets（平台约定）：
  - `node_set__NAME`: `(k,)` 节点 id
  - `edge_set__NAME`: `(m,2)` 边（节点对）
  - `elem_set__NAME__tri3` / `elem_set__NAME__quad4`: `(e,)` 对应 cell_type 下的局部单元 id

你们可以完全忽略 GUI 如何生成这些 sets；只要按 key 读出来用即可。

## 3. 输出数据（out/result.json + out/result.npz）

平台的 Output Workspace 依赖两部分：

### 3.1 result.json（meta）

meta 里最重要的是 registry（字段注册表），告诉平台：
- 有哪些可视化字段（位移/应力/孔压…）
- 每个字段在 `result.npz` 里的 key 命名模式（`npz_pattern`）
- 字段位置：`node` 或 `element`
- 字段形状：`scalar` / `vector2`（二维）

参考实现（直接照抄结构即可）：
- `src/geohpem/solver_adapter/reference_elastic.py`：`capabilities()` + `solve()` 写 `u/sx/sy/sxy/vm`
- `src/geohpem/solver_adapter/reference_seepage.py`：`capabilities()` + `solve()` 写 `p`

### 3.2 result.npz（arrays）

数组命名约定（当前平台默认约定）：
- 节点场：`nodal__{name}__step{step:06d}`
- 单元场：`elem__{name}__step{step:06d}`

例如：
- `nodal__u__step000001` 形状 `(N,2)`
- `nodal__p__step000010` 形状 `(N,)`
- `elem__vm__step000008` 形状 `(Ne,)`（对应某一种 cell_type 的单元数）

> 说明：平台的 “Step slider” 来自 `result.json` 的 steps/global_steps（或从 npz keys 推断）。你们可以输出多个 step 来支持过程可视化与时程曲线。

## 4. 代码在哪里（你可以复制的模板）

强烈建议你们从以下模板复制改造：

- 线弹性参考求解器（FEM assembly + BC/Load + 输出）：  
  - `src/geohpem/solver_adapter/reference_elastic.py`
- 稳态渗流参考求解器（Poisson/Darcy + BC/flux + 输出）：  
  - `src/geohpem/solver_adapter/reference_seepage.py`
- 求解器加载器（selector → solver 实例）：  
  - `src/geohpem/solver_adapter/loader.py`

这些模板的价值：
- “接口怎么写、meta 怎么组织、数组怎么命名”已经被平台验证
- 你们只需要替换“组装方程/求解/写出字段”部分

## 5. 高层原理（给算法同学的共识）

### 5.1 reference_elastic（线弹性 FEM）

核心流程（非常标准）：
1. 从 mesh 得到单元连接与坐标
2. 读取材料参数（`E, nu` 等）并按 `assignments` 映射到单元
3. 组装全局刚度矩阵 `K` 与载荷向量 `f`
4. 施加 Dirichlet（位移）边界条件、Neumann（面力/体力）等
5. 解线性方程 `K u = f`
6. 后处理计算应力分量与 `von Mises`（`vm`），写入 `result.npz`

### 5.2 reference_seepage（稳态渗流）

核心流程：
1. 读取渗透系数 `k`（各向同性最简）
2. 组装 Poisson/Darcy 离散方程（`A p = b`）
3. 施加：
   - Dirichlet（给定 `p`）
   - Neumann/flux（给定通量）
4. 解 `p`，写入 `result.npz`

## 6. 如何在平台里调用你们的 solver

平台的 solver 选择器支持两类：

1) 内置（当前已有）：`fake` / `ref_elastic` / `ref_seepage`  
2) 外部模块：`python:<module>`（例如 `python:geohpem_solver`）

你们只需要保证 `python:<module>` 能 import 成功，并能返回 solver 对象。

对接细节见：
- `docs/SOLVER_SUBMODULE_INTEGRATION.md`

## 7. 你们如何自测（推荐流程）

生成参考 case（包含 request+mesh）：
- `python scripts/make_reference_cases.py`

运行求解写出 out（CLI，便于回归）：
- `python geohpem_cli.py run _Projects/cases/reference_elastic_01 --solver ref_elastic`
- `python geohpem_cli.py run _Projects/cases/reference_seepage_01 --solver ref_seepage`

GUI 打开 `out/` 看可视化：
- `python main.py --open _Projects/cases/reference_elastic_01`

你们新 solver 的回归建议：
- 复制 `reference_elastic.py` → 改为你们算法 → 注册为新 selector
- 用同一套 case（或你们专用 case）跑通：precheck → run → Output 可视化

## 8. PFEM / HEPM（面向未来的“从一开始就对齐”）

平台在 v0.2 里预留了 PFEM/HEPM 相关扩展点（开发期不强校验）：
- `docs/CONTRACT_V0_2.md` 的第 7 节（frames/events，多载体 mesh/particles）
- `docs/PFEM_HEPM_Design_Notes.md`

你们需要记住的最小约束：
- 可以在 `solve()` 中通过 `callbacks["on_frame"]` 把每一帧（或子步）的 meta/arrays（可选）回调给平台（流式可视化/日志/调试）
- 如果有粒子场，请用命名空间区分（建议 `particles__*`），mesh remesh 则用 `mesh__*`；平台后续会补齐统一转换层

