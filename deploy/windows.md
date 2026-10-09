# Windows 常驻部署

团队在 Windows 常驻机上运行。推荐方案：NSSM 托管 API 进程 + Task Scheduler 定时采集。

## 1. 环境

- 安装 Python 3.11+（python.org 安装包，勾选 Add to PATH）
- （可选）PostgreSQL 16 for Windows；轻量起步可直接用 SQLite（默认配置即可，数据文件在 `data/`）

```powershell
cd C:\apps\palantir-tw
python -m venv .venv
.venv\Scripts\pip install -e .
.venv\Scripts\palantir-tw initdb
.venv\Scripts\palantir-tw seed-cec-2022
```

## 2. NSSM 托管 API

```powershell
# 下载 nssm: https://nssm.cc/download
nssm install palantir-tw-api "C:\apps\palantir-tw\.venv\Scripts\palantir-tw.exe" serve --port 8000
nssm set palantir-tw-api AppDirectory "C:\apps\palantir-tw"
nssm set palantir-tw-api AppStdout "C:\apps\palantir-tw\logs\api.out.log"
nssm set palantir-tw-api AppStderr "C:\apps\palantir-tw\logs\api.err.log"
nssm start palantir-tw-api
```

## 3. 定时采集（Task Scheduler）

Phase 2 采集器上线后，用 Task Scheduler 建任务：
- 触发器：每小时 / 每日
- 操作：`.venv\Scripts\palantir-tw.exe ingest-run --source news`

## 4. 数据与备份

- SQLite：备份 `data\palantir_tw.db` 单文件即可
- 原始采集件在 `data\raw\`（按源分目录，SHA256 命名），建议纳入定期备份
