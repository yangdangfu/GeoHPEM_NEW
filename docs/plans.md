# GeoHPEM_NEW 计划（精简版）

目标：在保持“FEM 类流程 + 工业化体验”的前提下，把现有功能收敛为可交付版本，并为 PFEM/HPEM 后续集成保留扩展点。

---

## 一、范围与交付标准

**范围澄清**
- 不复刻 PLAXIS 全功能，仅覆盖：建模数据准备 → 调用 solver → 后处理。
- Contract/数据结构为 PFEM/HPEM 预留扩展能力，但当前只追求“工程级稳定可用”。
- 开发阶段不做跨版本兼容，保留 `schema_version` 入口即可。

**上线门槛（必须达成）**
- UI 交互清晰：输入、求解、后处理流程顺畅；关键入口可发现。
- Property 面板统一风格，编辑/应用不跳项。
- Input/Output 关键功能可用并稳定：导入/生成网格、选择/建集、运行/诊断、云图/剖面/时程/导出。
- Precheck/提示足够“前置”：常见错误能在 Run 前提示清楚。

---

## 二、已完成（冻结）

**架构与工程闭环**
- 工程文件（`.geohpem`）Open/Save/Save As/Recent/恢复入口。
- Contract v0.1/0.2 基本读写与校验入口。
- Fake solver / reference solvers 闭环。

**Input**
- 几何绘制 + pygmsh 网格化，交互预览。
- Mesh 导入 + sets 管理。
- Input 选择/框选/刷选/边界辅助/建集。

**Output**
- VTK/PyVistaQt 可视化闭环。
- Probe/剖面线/时程曲线/导出 PNG。
- Output 面板重排与交互优化。

**GUI 与体验**
- Properties 统一样式与信息结构。
- Material: 行为/模型/模板 + 嵌套参数 Tree/JSON。
- Project 树刷新不丢选中项。
- JSON -> Table/Tree 逻辑补齐。

---

## 三、待完成（必须）

### M16：发布前 GUI/交互/体验收敛（最高优先）
- [x] **Quick Presets（向导式添加）**
  - DoD：Properties 中提供常用按钮：
    - Fix bottom / Fix left-right / Roller
    - Traction on top / Gravity
    - Default outputs（u, vm, p 等）
- [x] **关键错误提示前置**
  - DoD：缺 mesh / 缺 assignment / 输出字段不支持 / sets 缺失 / stage 空配置  
    在 Run 前以明确提示列出，并提供“一键跳转”入口。

---

## 四、可选优化（上线后迭代）

### UI 美化与视觉统一（优先级中）
- [x] **品牌与基础视觉**
  - DoD：统一 App 图标、启动图标与窗口标题图标；提供 `docs/BRANDING.md` 说明来源与版权。
- [x] **图标体系与 Toolbar**
  - DoD：常用操作（New/Open/Save/Run/Import/Validate/Output）用图标 + 文本统一；图标风格一致。
- [x] **主题与配色**
  - DoD：提供轻量 QSS 皮肤（浅色为主）；控件间距、字体层级统一。
- [x] **面板布局与信息密度**
  - DoD：Input/Output 工作区的控件分组、标题、留白一致；避免“过密/过空”。

### 逻辑与布局再梳理（体验修正）
- [x] **工作区顶部状态栏**
  - DoD：显示 project 名称（非全路径）、solver、dirty 状态；按钮布局简洁。
- [x] **Properties 表单布局一致性**
  - DoD：所有页头/分组标题样式一致；表格/树控件高度与滚动策略一致。
- [x] **常见功能入口收敛**
  - DoD：功能不重复散落：菜单/右键/工具栏各司其职（1 主入口 + 1 快捷入口）。

---

## 五、建议执行顺序

1) 完成 M16 两项必做  
2) UI 美化与布局梳理（图标/主题/面板间距）  
3) 快速回归所有教程与 UI 入口  
4) 冻结 UI/Contract，进入对标与交付迭代  

### UX/效率增强
- 新手模式（下一步建议）
- 右键菜单快捷键提示完善
- 选择反馈增强（来源、数量、类型拆分）

### 技术债/结构整理
- 更强 Domain Model 类型化（长期）
- 统一输出对标清单与自动对标报告
- 打包发布（conda/installer）

---
## M17: Configurable Material Catalog (recommended)
- [x] M17.1 Catalog schema
  - DoD: add a `materials_catalog.json` schema for model/behavior/params/meta(tooltips)/grouping, plus a default catalog file.
- [x] M17.2 User catalog merge
  - DoD: support `catalogs/default + catalogs/user` merge with user override and rollback.
- [x] M17.3 UI management
  - DoD: UI supports copy/rename/edit/delete models; parameter Tree/JSON and tooltips stay consistent; save to user catalog.
- [x] M17.4 Validation + safety
  - DoD: validate required fields/types; clear error prompts; keep revision history for user edits.
- [x] M17.5 Solver mapping hooks
  - DoD: provide mapping hook from catalog model/params to solver input without breaking existing cases.

## Progress Updates (UI/UX)
- [x] Context menus show shortcut hints in Input and Output workspaces.
- [x] Selection feedback: Input shows selection counts; Output shows pins/profiles counts.
