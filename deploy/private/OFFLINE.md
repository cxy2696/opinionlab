# 私有化离线交付包 / Air-gapped private delivery

## 组成 / Contents
- `images/*.tar`：api、worker、postgres、redis、minio 镜像（`docker save` 导出）。
- `packages/hnle-*.whl`：可离线 `pip install` 的引擎与 CLI。
- `scenarios/`、`migrations/`、`docker-compose.yml`、`.env.example`。
- 校验清单 `SHA256SUMS`。

## 步骤 / Steps
1. 在联网机器执行 `docker compose build && docker save ...`，连同 `uv build packages/hnle` 一起刻盘。
2. 客户内网执行 `docker load -i images/*.tar`，`pip install packages/hnle-*.whl`。
3. 复制 `.env.example` 为 `.env`，替换全部 `CHANGE_ME`（数据库密码、JWT、HMAC 根密钥、S3）。
4. `docker compose up -d`；`alembic upgrade head` 已由 api 容器启动命令执行。
5. 无公网时可全离线运行：引擎只依赖 numpy/scipy/pandas，报告为单文件 HTML。

## 校验 / Verification
- `sha256sum -c SHA256SUMS`
- `docker compose ps` 全部 healthy
- `curl http://localhost:8000/health` 返回 `{"status":"ok"}`
- 离线跑一次：`hnle simulate --spec scenarios/s2_rumor_debon_timing.yaml --repeats 5 --out-dir runs`

## 回滚 / Rollback
- 保留上一版本镜像 tag；`docker compose down` 后用旧 tag 重新 `up -d`。
- 数据库迁移仅允许可逆版本回退（`alembic downgrade -1`），并在维护窗口执行。
