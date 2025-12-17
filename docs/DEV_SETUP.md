# 开发环境建议（Windows / conda）

本仓库默认以 `src/` 布局运行（无需先安装包，也可 editable install）。

## 1) conda 环境（建议）

仓库提供 `environment.yml`（可按需调整版本）：
- 创建：`conda env create -f environment.yml`
- 激活：`conda activate geohpem`

## 2) 运行（开发态）

在仓库根目录：
- CLI：`python -m geohpem about`
- 生成示例：`python -m geohpem contract-example`
- 运行假求解：`python -m geohpem run examples\\contract_v0_1_minimal --solver fake`
- GUI：`python main.py --open examples\\contract_v0_1_minimal`

说明：
- 当前 `python -m geohpem` 默认启动 GUI（等价于 `geohpem.main`）
- CLI 入口为 `python -m geohpem.cli ...`

## 3) 外部 solver 包接入（约定）

后续 solver submodule 需提供：
- `capabilities() -> dict`
- `solve(request: dict, mesh: dict, callbacks: Optional[dict]) -> (result_meta: dict, result_arrays: dict)`

详见：`docs/2025121714_GeoHPEM_软件架构设计.md`
