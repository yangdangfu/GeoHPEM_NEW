# GeoHPEM 工程文件格式（`.geohpem`）

`.geohpem` 是一个 **zip 单文件包**，用于保存工程输入、（可选）求解输出、附件与元数据。

## 目标
- 单文件分享与归档（便于传递给 solver 团队/对标/复现）。
- 支持版本演进（manifest/request/result 的 `schema_version` 与迁移）。
- 支持大数据（mesh/result 使用二进制 NPZ）。

## 包内结构（v0.1）

```
project.geohpem  (zip)
  manifest.json
  request.json
  mesh.npz
  out/
    result.json        (可选)
    result.npz         (可选)
  attachments/         (可选)
    ...
```

## manifest.json（建议字段）
- `schema_version`: `"0.1"`
- `created_at`: ISO 时间
- `app`: `{ "name": "geohpem", "version": "..." }`
- `contract`: `{ "request": "0.1", "result": "0.1" }`
- `notes`: 可选备注

> 平台在打开工程时应允许 manifest 有未知字段（向前兼容）。

## request.json / mesh.npz / out/*

遵循 Contract 约定（详见 `docs/2025121714_GeoHPEM_软件架构设计.md`）：
- 输入：`request.json + mesh.npz`
- 输出：`out/result.json + out/result.npz`（可选）

