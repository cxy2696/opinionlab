# 合规说明 / Compliance

## 区域 / Regions
- `REGION=cn` 或 `global` 决定数据驻留与合规模板；跨区租户数据访问返回 `403 REGION_MISMATCH`。
- `REGION=cn|global` controls data residency; cross-region tenant access returns 403.

## 用途审批 / Use-case review
- `USE_CASE_REVIEW_ENABLED=true` 时，G5 选举类模板需 org_admin 提交用途声明、platform_admin 审核。
- 未批准的 G5 克隆返回 `403 USE_CASE_NOT_APPROVED`。
- G5-class election templates require an org_admin declaration and platform_admin approval.
- Unapproved clones return `403 USE_CASE_NOT_APPROVED`.

## 数据最小化与删除 / Minimisation & deletion
- 只接收结构性输入，拒绝手机号/身份证/邮箱/昵称原文列。
- dataset 删除级联清理 graph_snapshots、runs、artifacts 与共享映射；场景保留但解除关联。
- Only structural inputs; raw phone/ID/email/nickname columns are rejected.
- Dataset deletion cascades graph snapshots, runs, artifacts and shares.

## 日志与留存 / Logging & retention
- 审计日志只追加、默认留存 ≥180 天。
- 日志脱敏：邮箱掩码、HMAC 仅前 8 位、description 截断 200 字符，不记录正文。
- Audit logs are append-only with ≥180-day retention.
- Logs mask emails, keep only 8 HMAC chars, truncate descriptions at 200 chars.

## 可选生成式辅助 / Optional generative assist
- Ollama 辅助解读默认关闭，需 `OLLAMA_ENABLED=true`；不用于指标、结论或个体预测。
- 输出必须标注“AI 辅助解释，不是结论”，并保留引擎数字与免责声明。
- 不向第三方发送数据；默认仅连接本机 `127.0.0.1:11434`。

## 红线 / Red lines
- 任何接口不得返回单节点立场轨迹（`NODE_TRACE_FORBIDDEN`）。
- 报告必须带固定免责声明，缺失即 `DISCLAIMER_MISSING`。
- No endpoint may return single-node opinion trajectories.
- Reports must carry the fixed disclaimer or fail with `DISCLAIMER_MISSING`.
