# Solver Submodule 接入规范（给 solver 团队）

本规范用于约定 GeoHPEM 平台与 solver 团队的协作边界：**平台负责建模/项目/前后处理；solver 负责求解**。solver 将以 **Python 包（repo 子模块）** 的形式嵌入本仓库，通过 `capabilities()/solve()` 与 **Contract v0.1（JSON + NPZ）** 对接。

## 1. 推荐的仓库组织方式

- 建议把 solver 作为 git submodule 放在仓库内，例如：
  - `solvers/geohpem_solver_fem/`（FEM）
  - `solvers/geohpem_solver_hpem/`（HPEM）
- 每个 solver 子模块应当是一个**可 import 的 Python 包**（推荐带 `pyproject.toml`），并在开发环境中以 editable 方式安装：
  - `pip install -e solvers/geohpem_solver_fem`
- 平台侧通过 GUI/CLI 以 selector 选择 solver：
  - `fake`（内置）
  - `python:<module>`（外部模块），例如：`python:geohpem_solver_fem`

> 平台不强依赖“必须 pip 安装”，但为了稳定性/可复现，强烈建议 solver 包可被 `pip install -e` 安装。

## 2. API 约定（必须）

solver Python 包需暴露以下入口之一（平台侧 loader 会自动识别）：

- `get_solver() -> SolverProtocol`（推荐）
- 或 `Solver` 类（可无参构造）：`Solver()`

接口定义见 `src/geohpem/contract/types.py` 与 `documentation/for-developers/06-solver-adapter-module.md`。

### 2.1 capabilities()

必须返回 dict，建议包含：

```json
{
  "name": "geohpem_solver_fem",
  "version": "0.1.0",
  "contract": {"min": "0.1", "max": "0.1"},
  "modes": ["plane_strain", "axisymmetric"],
  "analysis_types": ["static"],
  "fields": ["u", "p"],
  "results": ["u", "p"]
}
```

平台侧会据此：
- 灰置/限制 UI（`mode`、`analysis_type`、输出字段）
- 在运行前做 precheck 校验（不支持即 ERROR）

### 2.2 solve(request, mesh, callbacks=None)

- 输入：
  - `request`: JSON dict（Contract v0.1）
  - `mesh`: dict[str, np.ndarray]（NPZ 内容）
  - `callbacks`（可选）：
    - `on_progress(progress: float, message: str, stage_id: str, step: int)`
    - `on_log(level: str, msg: str)`
    - `should_cancel() -> bool`（best-effort，需 solver 主动轮询）
- 输出：`(result_meta, result_arrays)`
  - `result_meta`: dict（含 `registry`）
  - `result_arrays`: dict[str, np.ndarray]（NPZ keys 与 registry 对应）

## 3. 错误与错误码（必须/强烈建议）

为支持平台侧统一错误展示、批量回归统计、诊断包收集，solver 在抛异常时建议提供：

- `code` 或 `error_code`：字符串（例如 `CONVERGENCE_FAILED`、`SINGULAR_MATRIX`）
- `details` 或 `payload`：dict（可选，结构化信息）

平台侧会将异常映射为标准错误码，并写入：
- GUI 失败弹窗信息（前缀 `[{CODE}] ...`）
- `_diagnostics/diag_*.zip` 的 `diag/meta.json` 中的 `error_code/error_details`
- `batch_report.json` 的 `error_code`

平台内置映射（平台侧兜底）：
- `CancelledError` -> `CANCELED`
- `ContractError` -> `CONTRACT`
- `ImportError/ModuleNotFoundError` -> `SOLVER_IMPORT`
- 其他未知异常 -> `SOLVER_RUNTIME`

## 4. 结果输出约定（建议）

平台通过 `result.json:registry` 驱动可视化/对标，因此 solver 需要保证：
- `registry` 中的每个条目都有：
  - `name`（例如 `u`、`p`、`stress`）
  - `location`（`node`/`element`/`ip`）
  - `shape`（例如 `scalar`/`vector2`/`tensor_voigt`）
  - `npz_pattern`（例如 `nodal__p__step{step:06d}`）
- 对同一字段，步号格式保持一致（推荐 `step{step:06d}`）

## 5. 最小联调建议（平台侧/solver 侧）

平台侧可以用 GUI 的：
- `File -> Export Case Folder...` 导出 `request.json + mesh.npz` 给 solver 团队
- solver 团队用脚本加载并运行 `solve()`，确认 `result.json/result.npz` 能被平台 `Open Output Folder...` 打开

建议 solver 团队维护一个最小算例集用于回归：
- `examples/solver_smoke_cases/<case_name>/request.json + mesh.npz`

