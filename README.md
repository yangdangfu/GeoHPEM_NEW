# GeoHPEM（GeoHPEM_NEW）

GeoHPEM_NEW 是一个面向岩土 2D（平面应变/轴对称）的“工程/前后处理平台 + 求解编排器”，类 PLAXIS 2D。

- 平台负责：几何/网格（导入 + pygmsh 网格化）、材料/边界/荷载/阶段配置、调用 solver（Python 包 submodule）、结果可视化与后处理、工程文件与可复现。
- solver 负责：数值求解（含本构、HPEM、多物理耦合等），按平台约定的 Contract（JSON + NPZ）读写数据。

架构设计文档：`docs/2025121714_GeoHPEM_软件架构设计.md`

## 快速开始（当前骨架）

CLI（不依赖 GUI）：
- `python -m geohpem.cli about`
- `python -m geohpem.cli contract-example`
- `python -m geohpem.cli run examples\\contract_v0_1_minimal --solver fake`

GUI（需要 PySide6）：
- `python main.py --open examples\\contract_v0_1_minimal`
- 或 `python -m geohpem --open examples\\contract_v0_1_minimal`

开发环境建议见：`docs/DEV_SETUP.md`
