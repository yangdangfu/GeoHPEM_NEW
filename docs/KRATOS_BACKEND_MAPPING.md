# Kratos 后端接入映射（GeoHPEM → Kratos）

本文作为 M16.1 的落地文档：定义 GeoHPEM 的 `request.json + mesh.npz` 如何映射到 Kratos 模型，以便后续实现真正的 FEM/PFEM 级别求解。

## 1. 选择 Kratos 的理由（面向岩土/PFEM）

- **PFEM 原生支持**：Kratos PFEM2/PFEMFluid/MPM 生态成熟，支持自由面、大变形、重网格。
- **岩土工程能力强**：非线性材料、接触、固结、渗流、动力学等模块齐全。
- **Python 接口完整**：可作为主平台的 solver backend。

结论：**主后端采用 Kratos**；FEniCSx/SfePy 可作为 FEM-only 备选，不作为主线。

## 2. mesh.npz → Kratos ModelPart

GeoHPEM mesh（NPZ）字段：
- `points (N,2)`
- `cells_tri3 (Nt,3)` / `cells_quad4 (Nq,4)`
- `node_set__NAME`
- `edge_set__NAME`
- `elem_set__NAME__tri3/quad4`

映射规则：
- `points` → Kratos `ModelPart.Nodes`
- `cells_tri3` → `Element2D3N`（或 Kratos 的对等单元）
- `cells_quad4` → `Element2D4N`（或等价单元）
- `node_set__NAME` → `SubModelPart[NAME]` 的节点集合
- `edge_set__NAME` → `SubModelPart[NAME]` 的边界（可转为 `Condition`）
- `elem_set__NAME__tri3/quad4` → `SubModelPart[NAME]` 的元素集合

> 注意：Kratos 的边界通常以 Condition 表达。平台侧可根据 `edge_set__*` 自动创建对应 Condition。

## 3. request.json → Kratos 配置

### 3.1 Model
- `model.mode`：`plane_strain / plane_stress / axisymmetric`
- `model.gravity`：映射为 Kratos `GRAVITY`（向量）
- `unit_system`：用于解释材料/载荷数值（平台只做显示单位，求解器使用 base 单位）

### 3.2 Materials & Assignments

+;
- `materials{}`：`model_name + parameters` 由 Kratos Material JSON 或内置材料库解释
- `assignments[]`：`element_set + cell_type` → `material_id`
- 建议：GeoHPEM → Kratos 采用统一的 material map（一个材料可应用多个 set）

### 3.3 Stage / BC / Loads

Stage 采用“序列激活”模式（类似 PLAXIS）：
- `analysis_type`：`static / dynamic / seepage_steady / seepage_transient / consolidation_u_p`
- `num_steps / dt`：用于时间积分/输出步

BC/Loads 映射约定：
- `type=displacement` → Dirichlet BC on `u`（`ux/uy`）
- `type=traction` → Neumann BC on boundary Condition
- `type=gravity` → Body force
- `type=p` → Dirichlet on `p`（渗流/孔压）
- `type=flux` → Neumann on `p`（渗流通量）

## 4. 输出结果（out/result.json + out/result.npz）

Kratos 输出被平台统一写成：
- `result.json`: registry + global_steps/frames
- `result.npz`: `nodal__*__step000123` / `elem__*__step000123`

常用字段建议（岩土）：
- `u`（位移），`strain`，`stress`，`vm`
- `p`（孔压），`u_p`（固结）
- `plastic_strain` / `damage`（若有）

## 5. PFEM/HPEM 扩展点（必须预留）

对 PFEM/HPEM 的要求：
- **可变拓扑**：重网格/重采样时允许输出 mesh 更新
- **粒子场**：结果允许 `particles__*` 命名空间
- **事件/帧**：`result.json` 支持 `frames[]` 或扩展 `global_steps`（带 `events[]`）

建议的 PFEM 结果输出：
- `mesh__points__frame000123`
- `mesh__cells__frame000123`
- `particles__x__frame000123`
- `particles__v__frame000123`

> 平台后处理会优先支持 mesh 结果，粒子结果在后续阶段引入。

## 6. 依赖与落地方式（建议）

建议路径：
1) 先落地 **Kratos Adapter** 骨架（capabilities + solve stub）
2) 先实现最小 FEM：线弹性 + static + traction + displacement
3) 再扩展到 Mohr-Coulomb / Hardening Soil
4) 再扩展 PFEM2 + remeshing

