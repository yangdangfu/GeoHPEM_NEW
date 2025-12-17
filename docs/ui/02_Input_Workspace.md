# Input 工作区（建模）规格（MVP）

## 模块
- Geometry（预留）：几何编辑树、图层、物理组
- Mesh：导入网格 / pygmsh 网格化（后续）；当前 MVP 先支持“读取 mesh.npz”
- Sets：Node/Edge/Element sets 管理（从导入/选择生成，后续）
- Materials：材料列表（model_name + parameters 透传）
- Stages：阶段列表与阶段属性（analysis_type、num_steps、dt、激活/停用引用）
- Output Requests：输出请求（name/location/every_n 等）
- Solver Settings：solver selector、容差/迭代等透传设置

## 交互
- 项目树选择对象 → 属性面板编辑
- Stage Manager 选择阶段 → Properties 显示该阶段

