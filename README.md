# GeoHPEM（GeoHPEM_NEW）

GeoHPEM_NEW 是一个面向岩土 2D（平面应变/轴对称）的“工程/前后处理平台 + 求解编排器”，类 PLAXIS 2D。

- 平台负责：几何/网格（导入 + pygmsh 网格化）、材料/边界/荷载/阶段配置、调用 solver（Python 包 submodule）、结果可视化与后处理、工程文件与可复现。
- solver 负责：数值求解（含本构、HPEM、多物理耦合等），按平台约定的 Contract（JSON + NPZ）读写数据。

架构设计文档：`docs/2025121714_GeoHPEM_软件架构设计.md`

