# Contract v0.2（平台 ↔ Solver 数据契约）

本文件定义 **GeoHPEM 平台与 Solver** 的最小可执行数据契约（JSON + NPZ）。目标是：
- 平台能以“真实参数（材料/边界/荷载/阶段）”驱动求解；
- Solver 团队能照此实现 `capabilities()/solve()`，并产出平台可视化/对标所需的 `result.json + arrays.npz`。

> v0.2 以 **可执行** 为第一优先：字段尽量少、语义清晰、可扩展但不强行一次到位。
> 开发阶段不承诺跨版本兼容：schema/字段可能调整；但会保留 `schema_version` 与扩展点，正式版再收敛兼容策略。

---

## 1. 目录结构（Case Folder）

一个 Case Folder 最少包含：
- `request.json`：建模与求解配置（本文件）
- `mesh.npz`：网格与 sets（NPZ 二进制）

求解输出约定写入：
- `out/result.json`
- `out/result.npz`

平台 GUI 支持：
- `File -> Export Case Folder...` 导出 request+mesh
- `File -> Open Case Folder...` 打开并在存在 `out/` 时自动进入 Output

---

## 2. mesh.npz（Contract Mesh）

NPZ 中的关键数组（最小集）：
- `points`：`float64 (N,2)`，节点坐标（base units）
- `cells_tri3`：`int64 (Nt,3)`，三角形单元连接
- `cells_quad4`：`int64 (Nq,4)`，四边形单元连接（可选）

Sets 的命名约定（由平台生成/导入）：
- `node_set__<name>`：`int64 (K,)`，节点索引（0-based）
- `edge_set__<name>`：**推荐** 用边对 `(n1,n2)`：`int64 (K,2)`（顺序可忽略）
- `elem_set__<name>__tri3`：`int64 (K,)`（tri3 的 local cell id）
- `elem_set__<name>__quad4`：`int64 (K,)`（quad4 的 local cell id）

> 说明：平台在 VTK 转换时会将不同 cell blocks 拼成一个 `grid.n_cells`；因此 element set 需要带 cell_type 才能稳定映射。

---

## 3. request.json（SolveRequest v0.2）

### 3.1 顶层结构

```json
{
  "schema_version": "0.2",
  "unit_system": { "length": "m", "pressure": "Pa" },
  "model": { "dimension": 2, "mode": "plane_strain", "gravity": [0, -9.81] },
  "materials": { "...": { "model_name": "...", "parameters": { } } },
  "assignments": [ ... ],
  "stages": [ ... ],
  "output_requests": [ ... ]
}
```

### 3.2 model

- `dimension`：固定为 `2`
- `mode`：`plane_strain | plane_stress | axisymmetric`
- `gravity`：`[gx, gy]`（base units），可选；若缺省视为 `[0, 0]`

### 3.3 materials（材料库）

最小可执行材料类型（v0.2 要求至少支持 1 个）：

#### linear_elastic（线弹性，各向同性）

```json
"materials": {
  "mat_soil": {
    "model_name": "linear_elastic",
    "parameters": { "E": 3.0e7, "nu": 0.30, "rho": 1800.0 }
  }
}
```

参数建议：
- `E`：Young’s modulus（Pa）
- `nu`：Poisson ratio
- `rho`：density（kg/m³，可选；用于 gravity）

> 平台不负责本构实现；但 v0.2 的参考求解器会实现线弹性，作为接口样板与对标基线。

#### darcy（渗流/孔压：各向同性 Darcy）

用于 `analysis_type=seepage_steady` 的参考求解器：

```json
"materials": {
  "mat_k": { "model_name": "darcy", "parameters": { "k": 1.0e-6 } }
}
```

参数建议：
- `k`：渗透系数（单位由 solver 约定；平台只负责透传与显示单位）

### 3.4 assignments（材料分配）

最小形式：按 element_set 分配材料：

```json
"assignments": [
  { "uid": "as_1", "cell_type": "tri3", "element_set": "soil", "material_id": "mat_soil" }
]
```

字段：
- `cell_type`：`tri3 | quad4`
- `element_set`：不含前缀的 set 名（对应 `elem_set__<name>__<cell_type>`）
- `material_id`：materials 的 key

### 3.5 stages（阶段/工况）

最小字段：

```json
"stages": [
  {
    "uid": "S1",
    "name": "S1_initial",
    "analysis_type": "static",
    "num_steps": 10,
    "dt": 1.0,
    "bcs": [ ... ],
    "loads": [ ... ],
    "output_requests": [ ... ]
  }
]
```

#### bcs（边界条件）

最小支持：位移边界（节点集）。

```json
{ "uid": "bc_bottom_fix", "type": "displacement", "set": "bottom", "value": { "ux": 0.0, "uy": 0.0 } }
```

- `set`：优先约定为 `node_set` 名；若传入 `edge_set` 名，平台可（可选）提供“边→节点投影”辅助。
- `value`：允许指定 `ux/uy` 任意子集（只锁一个方向也可）

#### loads（荷载）

最小支持：重力与边界 traction（线力/面力在 2D 等效）。

```json
{ "uid": "ld_gravity", "type": "gravity", "value": [0, -9.81] }
{ "uid": "ld_top_trac", "type": "traction", "set": "top", "value": [0.0, -1.0e5] }
```

- `gravity.value`：可覆盖 model.gravity（若缺省则使用 model.gravity）
- `traction.set`：edge_set 名（对应边界线段集合）
- `traction.value`：`[tx, ty]`（Pa 或 N/m，取决于 solver 约定；建议统一按 Pa，并由 solver 乘以厚度/轴对称体积因子）

**渗流（seepage_steady）最小 BC/Load：**

```json
{ "uid": "bc_p_top", "type": "p", "set": "top", "value": 100000.0 }
{ "uid": "ld_flux",  "type": "flux", "set": "bottom", "value": -1.0e-6 }
```

- `p`：Dirichlet（节点集）
- `flux`：Neumann 通量（边集），符号约定由 solver 定义（平台仅透传）

#### output_requests（阶段输出请求）

与平台 Output “Registry” 一致，最小示例：

```json
{ "uid": "or_u", "name": "u",  "location": "node",    "every_n": 1 }
{ "uid": "or_vm","name": "vm", "location": "element", "every_n": 1 }
```

### 3.6 output_requests（全局输出请求，可选）

若存在，则等价于“所有 stage 都输出这些字段”，stage 内同名会覆盖。

---

## 4. out/result.json（SolveResult）与 out/result.npz

### 4.1 result.json（最小）

- `schema_version`：暂沿用 `0.1`（平台当前已实现）
- `status`：`success | failed | canceled`
- `registry`：结果字段列表（用于 Output UI）
- `global_steps`：可选，但强烈建议提供（time/stage/step 语义）

### 4.2 result.npz（命名约定）

平台当前读取约定：
- `nodal__<name>__step000010`：node arrays（标量或向量）
- `elem__<name>__step000010`：element arrays

建议至少输出：
- `nodal__u__step******`：`(N,2)` 位移
- `elem__vm__step******`：`(Nc,)` von Mises

---

## 5. 参考实现建议（给 solver 团队）

Solver 团队可以按以下结构组织：

```python
def capabilities() -> dict: ...
def solve(request: dict, mesh: dict, *, workdir: str | Path, progress_cb=None, cancel_token=None) -> dict: ...
```

- `mesh`：即 `np.load(mesh.npz)` 的 dict 化结果（平台会负责读取/传入）
- `workdir`：solver 可以在此写出 `out/` 与诊断文件
- 返回值：可返回 `result_meta`（平台也支持仅依赖 `out/` 文件）

---

## 6. 已知未覆盖（v0.3+）

以下将作为后续版本扩展，不阻塞 v0.2：
- 本构：Mohr-Coulomb/Hardening soil 等
- 多相耦合：u-p（Biot）、渗流-固结
- 接触/结构单元、接口单元
- 多阶段激活/卸载的细粒度控制（目前按 stage 序列简化）

---

## 7. PFEM/HPEM 扩展点（开发期：可选字段，但建议从一开始对齐）

本节给出“可承载 PFEM/HPEM”的扩展点草案（不会阻塞 v0.2 的 FE/渗流参考求解器）。

### 7.1 request.json 扩展

```json
{
  "discretization": {
    "type": "mesh",
    "particles": { "source": "from_mesh", "density": 1.0 },
    "remeshing": { "enabled": true, "trigger": "quality", "h_min": 0.1 }
  }
}
```

- `discretization.type`：`mesh | particles | hybrid`
- `particles`：粒子生成/导入策略（可后续细化为 seed/sets）
- `remeshing`：重网格化策略描述（触发与控制参数）

#### 7.1.1 可变随时间参数（可选，建议仅透传给 solver）

参考 `GeoHPEM_reference/src/solver/case_*.py` 里的 `Expression`（例如 `"10000 * i"`）做法：
- 平台侧不负责表达式求值（避免安全/可重复性问题）
- Contract 允许将 `value` 写成对象，由 solver 决定如何解释：

```json
{ "type": "traction", "set": "top", "value": { "expr": "-1.0e5 * t", "vars": ["t"] } }
```

建议变量：
- `t`：物理时间
- `k`：global frame/step id
- `stage_step` / `substep`

> 说明：这一条是“扩展点”，开发期不强校验；正式版再收敛安全执行与可复现实验策略。

### 7.2 out/result.json 扩展（frames/events）

建议用 `frames[]` 承载可变输出频率（每步/每子步/任意），并附带事件：

```json
{
  "frames": [
    {
      "id": 1,
      "time": 0.01,
      "stage_id": "S1",
      "stage_step": 0,
      "substep": 3,
      "events": [{"type": "remesh", "reason": "min_angle"}]
    }
  ]
}
```

> 平台侧 Output 的 Step slider 可以绑定 `frames[].id`，从而不强制 solver 固定输出节奏。

### 7.3 out/result.npz 扩展（多载体：mesh/particles）

建议使用命名空间：
- `mesh__*__frame{frame:06d}`：每帧可变拓扑 mesh
- `particles__*__frame{frame:06d}`：每帧粒子状态
- 现有 `nodal__/elem__` 也可改为 `__frame`（与 registry 的 `npz_pattern` 对齐）

---

## 8. 参考实现对照（从 GeoHPEM_reference 到 Contract v0.2）

`GeoHPEM_reference/src/solver/FEMSimulation.py` 的入口形态更偏“科研脚本式”：case_*.py 在 solver 内部生成网格、按 range 定义 sets、用字符串 Expression 表示时变荷载，并在求解中进行 remesh 与 VTK 导出。

本平台前期的决策（建议 solver 团队按此对齐）：
1) **网格/sets 由平台生成**：solver 只接收 `mesh.npz`（points/cells/sets），不再内部 `build_in_rectangle()` 或按 range 再造 sets。
2) **BC/Load/Materials 由 Contract 明确类型**：`type + set + value`，避免到处散落 `Nset/Sset/Eset/Direction/Expression`。
3) **重网格化作为“可变拓扑输出”处理**：
   - solver 内部可以重网格化
   - 但输出要通过 `frames/events` + `mesh__*__frame******`（或 `step******`）传回平台，平台负责可视化与对标导出。
4) **实时回调（可选）**：参考 FEMSimulation 的 `step_once/on_frame`，solver 可用 `callbacks['on_frame']` 做实时帧回调；平台开发期不强依赖，但建议接口预留。
