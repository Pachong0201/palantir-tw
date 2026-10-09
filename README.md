# palantir-tw · 台湾开源情报平台

仿 Palantir Gotham 的分析范式：**本体驱动融合 + 断言级证据分级 + 人在回路**。
MVP 域：选举与政治。团队内部平台，Windows 常驻机部署。

设计文档见 `docs/design.md`。

## 本体模型

- `Entity`：person / party / organization / district / election / event / document
- `Assertion`：实体间关系，每条带证据等级（A–E）、来源文档、有效期
- `Candidacy`：参选记录（中选会官方数据，证据 A 级）
- `RawItem`：采集暂存，原样存档 + SHA256 去重

## 快速开始（Linux/macOS）

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/palantir-tw initdb
.venv/bin/palantir-tw seed-cec-2022     # 下载中选会数据包并导入 111 年县市长数据
.venv/bin/palantir-tw serve --port 8000 # http://localhost:8000
```

## 测试

```bash
.venv/bin/python -m pytest
```

## 数据源

| 源 | 状态 | 说明 |
|---|---|---|
| 中选会选举数据库 (data.cec.gov.tw/votedata.zip) | ✅ 已接入 | 111 年地方公职人员选举，22 县市首长 |
| 监察院政治献金/财产申报 | 规划中 (Phase 1) | 多为网页影像，需 OCR 评估 |
| 新闻 RSS | 规划中 (Phase 2) | |

## 部署

Windows 常驻部署见 `deploy/windows.md`。
