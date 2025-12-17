# 交互模型（Interaction Model）

## Undo/Redo
- MVP：仅 UI 级别（属性编辑）可撤销（后续实现命令栈）

## 任务与线程
- 求解运行必须后台线程执行（QThread/QRunnable），UI 通过 signal 更新进度/日志
- 取消：UI 设置 cancel flag，solver 通过 callbacks `should_cancel()` 协作取消

## 输入检查（Pre-check）
- MVP：仅做 Contract 基础校验（schema_version/model/stages 非空）
- 后续：网格质量、未赋值域、阶段冲突、输出请求有效性等

