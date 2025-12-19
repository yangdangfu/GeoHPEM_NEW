# PFEM / HPEM（PFEM / Hybrid Element Particle Method）对平台契约与后处理的影响（设计笔记）

本文件不是算法教材，而是“**把 PFEM/HPEM 接进平台**”所需的工程化抽象：输入/输出/时间轴/可视化载体应该如何设计，避免后续返工。

> 适用范围：2D（plane strain/stress/axisymmetric）为主，未来可扩展。

---

## 1. PFEM（Particle Finite Element Method）常见工程特性（平台视角）

不同团队的 PFEM 细节会不同，但从平台/契约角度，通常会出现以下“共性需求”：

1) **拉格朗日运动 + 大变形**
- 节点/粒子随材料运动，几何会显著变化（位移不再是小扰动）

2) **重网格化/拓扑变化（频率可变）**
- 为保证网格质量，需要周期性重网格化（每步/每若干子步/自适应触发）
- 重网格化导致：`points/cells` 可能随时间变化，且每个时间点的 `n_points/n_cells` 可能不同

3) **场变量“搬运/映射”**
- 重网格化后需要把状态量（位移/速度/应力/孔压/内部变量等）从旧离散体映射到新离散体
- 这会产生“映射质量/误差/守恒量”的诊断输出需求（对标/调参非常有用）

4) **自由面/接触/多体**
- PFEM 常用于自由表面流固耦合、开挖塌落、颗粒堆积等
- 结果上通常需要输出：自由面轮廓、接触力、材料边界演化

> 结论（平台侧）：必须从一开始就支持“**可变输出频率 + 可变拓扑**”，并能承载“事件与诊断信息”。

---

## 2. HPEM/HEPM（Hybrid Element Particle Method）常见工程特性（平台视角）

HPEM/HEPM 名称在不同团队里可能代表不同实现，但“Hybrid Element + Particle”的核心通常意味着：

- 同时存在 **连续体网格**（elements）与 **离散粒子**（particles）
- 两者之间存在耦合：粒子可能承载部分自由度或状态变量，网格用于求解场/约束，或用于局部区域
- 可能出现“区域切换”：某些区域从网格转为粒子，或相反

> 结论：平台契约与结果载体需要支持 **多载体输出**（mesh + particles），并且在时间轴上可追踪“何时发生了切换/重构”。

---

## 3. 对平台契约（Contract）的直接要求

### 3.1 输入侧（request.json）建议稳定扩展点

建议在 v0.2 上增加（可选字段，开发期不强校验，但语义先定）：

- `discretization`：
  - `type`: `"mesh" | "particles" | "hybrid"`
  - `particles`（可选）：粒子生成/导入策略（seed、密度、初始粒子集）
  - `remeshing`（可选）：重网格化策略描述（触发阈值、最小网格尺寸等）

### 3.2 输出侧（out/result.json + out/result.npz）必须支持的能力

1) **帧（frame）/子步（substep）时间轴**
- solver 输出频率必须可变（你反馈“频率灵活即可”）
- 推荐 `result.json` 提供：
  - `frames[]`（或扩展 `global_steps[]`）：
    - `id`（int，全局唯一，等价于 platform Step slider 的索引）
    - `time`（float，物理时间；若无则可用 step 替代）
    - `stage_id / stage_step / substep`
    - `events[]`（见下）

2) **事件（events）**
用于解释“为什么发生变化”，并为对标/调参提供线索：
- `remesh`：重网格化发生（可含原因与质量指标）
- `particle_resample`：粒子重采样/重分布
- `contact_state_change`：接触状态变化
- `mapping`：字段映射完成（可含误差指标）

3) **多载体数据（mesh / particles / hybrid）**

推荐 result.npz 的命名空间（示例）：
- Mesh（可选，若 mesh 不变则只需输出一次）：
  - `mesh__points__frame000123`  `(N,2)`
  - `mesh__cells_tri3__frame000123` `(Nt,3)`
  - `mesh__cells_quad4__frame000123` `(Nq,4)`
- Particles：
  - `particles__x__frame000123` `(Np,2)`
  - `particles__v__frame000123` `(Np,2)`
  - `particles__p__frame000123` `(Np,)`（孔压/压力/任意标量）
- Fields（沿用现有 registry 机制即可）：
  - `nodal__u__frame000123` / `elem__vm__frame000123`

> 注意：平台当前实现用 `step{step:06d}` 命名；建议后续统一抽象为 `{frame:06d}`，并在 registry 里提供 `npz_pattern`。

---

## 4. 后处理（Output）对 PFEM/HPEM 的“必须项”

为了对标与工程可用性，建议平台从一开始按下述优先级建设：

1) **Frame 播放与语义显示**
- Step slider 对应 `frame id`
- 显示：time / stage / substep / events（remesh 次数等）

2) **云图（mesh fields）+ 粒子叠加（particle fields）**
- mesh fields：u、应力、应变、孔压等（既有能力）
- particle overlay：点渲染 + 按标量着色（例如速度大小/压力）

3) **探针/剖面/时程：支持“mesh 与 particles”**
- probe：点选后返回最近 node/element/particle 的值
- profile：对 mesh 可 sample_over_line；对 particles 可做邻域插值/核平滑（先做最小可用）
- history：node/cell/particle 的时程

4) **导出（对标交付）**
- 每帧截图/序列导出
- 剖面与时程 CSV
- 诊断包：包含 events 与映射指标

---

## 5. 需要 solver 团队尽早对齐的“接口姿势”

即使算法细节未定，以下姿势建议从第一天就统一：

- `capabilities()` 中明确：
  - 是否会输出可变拓扑 mesh
  - 是否会输出 particles
  - 是否会输出 frames/events

- `solve()` 输出中：
  - `result.json` 必须给出 `registry` 与 frame/step 映射（平台才能后处理）
  - `result.npz` 的键命名要稳定（pattern 驱动）

---

## 6. 仍需你确认的最小信息（不需要懂算法细节）

你只需要从“平台能否承载”的角度给出倾向即可：

1) PFEM/HPEM 输出更偏向：
   - A：主要在 **mesh fields** 上对标（particles 只是内部手段）
   - B：必须对外提供 **particles 的可视化与对标**（粒子轨迹/自由面等）
2) 重网格化会导致 mesh 拓扑随时间变化吗？（是/否/可能）
3) 首批对标你最关心的 3 类输出是什么？（例如：云图、自由面、反力/能量、时程等）

