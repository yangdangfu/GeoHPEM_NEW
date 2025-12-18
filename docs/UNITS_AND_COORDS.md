# 单位与坐标约定（M7）

本文件定义 GeoHPEM 平台内部与对外（solver contract / UI 展示）的单位与坐标约定，避免后处理标尺/探针/对标出现歧义。

## 1) 坐标系（2D）

- 全局坐标：`X` 向右，`Y` 向上
- 重力：默认 `gravity = [0, -9.81]`（沿 `-Y`）
- 2D 模式：
  - `plane_strain`：平面应变（`X-Y` 平面），`Z` 为外法向（仅用于符号约定/三维扩展）
  - `axisymmetric`：轴对称（约定 `X` 为径向 `r`，`Y` 为轴向 `z`；`r>=0` 区域）

## 2) 单位策略（Contract v0.1）

### 2.1 `request.unit_system`

`request.json` 中的 `unit_system` 用于声明该工程“输入/输出数值所采用的工程单位”，例如：

```json
{"force":"kN","length":"m","time":"s","pressure":"kPa"}
```

### 2.2 v0.1 实现策略（当前）

- **数据存储与 solver 输入输出**：平台当前按 `request.unit_system` 的含义“原样透传”给 solver（即 request/mesh/结果数值以该单位体系理解）。
- **UI 展示单位（Display Units）**：支持用户选择“显示单位”，平台将对坐标读数/探针/云图数值做换算展示（不改变底层数据）。

在 GUI 中通过菜单 `View -> Display Units...` 设置显示单位（目前最小支持：长度/压强）。

> 后续如果需要“内部统一 SI 并对外转换”，建议在 Contract v0.2 引入更明确的字段并提供迁移；当前以“不破坏既有工程数据 + 可用闭环”为第一优先。

## 3) 应力/应变符号（预留）

为对标一致性，建议 solver 团队明确：

- 应力正负号：压正 / 拉正
- 分量顺序：`xx, yy, xy[, zz]` 等
- 轴对称额外分量的定义

该部分将随 solver 输出规范进一步固化。

