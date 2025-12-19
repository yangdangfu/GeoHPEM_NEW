# 内置参考求解器（Reference Solvers）

这些求解器用于：
- 给 solver 团队提供“接口/契约/输出”的可运行样板；
- 作为平台回归/对标的基线；
- 在 PFEM/HPEM 完整集成前，先把 **materials/bcs/loads/stages → solve → out → Output 后处理** 的真实数据流跑通。

它们是“真实算法的最小实现”（线弹性/渗流），不是 PLAXIS 全功能复刻。

---

## 1) `ref_elastic`：线弹性静力（plane strain / plane stress）

- 支持：
  - 材料：`linear_elastic`（E, nu, rho 可选）
  - BC：`displacement`（ux/uy，作用于 node_set/edge_set→node）
  - Load：`gravity`、`traction`（作用于 edge_set）
  - 输出：`u (node)`, `sx/sy/sxy/vm (element)`
- selector：`ref_elastic`
- 代码：`src/geohpem/solver_adapter/reference_elastic.py`

## 2) `ref_seepage`：稳态渗流（Poisson/Darcy）

- 支持：
  - 材料：`darcy`（k）
  - BC：`p`（Dirichlet，node_set/edge_set→node）
  - Load：`flux`（Neumann，edge_set）
  - 输出：`p (node)`
- selector：`ref_seepage`
- 代码：`src/geohpem/solver_adapter/reference_seepage.py`

---

## 运行方式

生成参考算例：
- `python scripts/make_reference_cases.py`

运行（会写出 `<case>/out/result.json + <case>/out/result.npz`）：
- `python geohpem_cli.py run _Projects/cases/reference_elastic_01 --solver ref_elastic`
- `python geohpem_cli.py run _Projects/cases/reference_seepage_01 --solver ref_seepage`

GUI 打开：
- `python main.py`
- `File -> Open Case Folder...` 选择对应 case（或打开 `out/`）

---

## PFEM/HPEM 相关（接口样式）

参考求解器内部也预留了 `callbacks['on_frame']` 回调姿势（可选），用于 PFEM/HPEM 的“可变输出频率/事件流”。

对接规范见：
- `docs/CONTRACT_V0_2.md`
- `docs/SOLVER_SUBMODULE_INTEGRATION.md`
- `docs/PFEM_HEPM_Design_Notes.md`

