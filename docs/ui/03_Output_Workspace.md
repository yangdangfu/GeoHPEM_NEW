# Output 工作区（后处理）规格（MVP）

## 模块
- Result Browser：选择结果集/阶段/步
- Field Selector：从 `result.json:registry` 动态列出可显示字段
- Color Map：范围、色标、单位显示（先占位）
- Viewport：显示云图/网格（MVP 先占位，后续接入 VTK/PyVistaQt）
- Probe/Section（后续）：点查询、剖面线曲线

## 数据驱动规则
- 字段、位置、单位与数组键完全由 registry 决定
- UI 不写死应力/应变/孔压名称，只提供“registry 浏览器”

