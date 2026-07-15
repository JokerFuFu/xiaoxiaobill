# XiaoxiaoBill (小小账单)

> Privacy-first personal bill analysis tool. All data is processed locally, nothing is uploaded to any server.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-brightgreen.svg)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

English | [简体中文](README.md)

> 🍴 **Lineage**: XiaoxiaoBill is a heavily-extended fork of [dtsola/xiaoyaoprivatebill](https://github.com/dtsola/xiaoyaoprivatebill) (Xiaoyao Bill Assistant, MIT), which itself was rebuilt from [Hessel2333/alipay_record_analysis](https://github.com/Hessel2333/alipay_record_analysis). See [Acknowledgments](#acknowledgments). All code remains under the MIT license.

---

## Introduction

XiaoxiaoBill imports your Alipay / WeChat / bank statement files locally, parses and deduplicates them across sources, and produces multi-dimensional visual analytics (yearly, monthly, category, time, channel, insights) — with an optional AI assistant on top.

**Key features**:
- 🔒 **Privacy first** - All data is processed locally; nothing is uploaded to any server
- 📁 **Multiple sources** - Alipay CSV, WeChat CSV/XLSX, bank PDF statements (CMBC/ABC/BOC), MYbank XLSX
- ♻️ **Cross-source dedup** - Transaction-level deduplication; platform auto-debits are excluded from totals to avoid double counting
- 📊 **Multi-dimensional analysis** - Yearly, monthly, category, time, channel, insights, income
- 🔀 **Transfer semantics** - Income / expense / transfer-in / transfer-out / excluded, with a dedicated Transfers page
- 👨‍👩‍👧 **Multi-user & members** - Login-based auth, per-user data isolation, family member attribution
- 🤖 **Optional AI assistant** - Chat over your transactions, smart bill recognition & import, per-dimension analysis reports; all analytics work without any AI key
- 📬 **Mailbox auto-import** - Fetch bill emails via IMAP, decrypt zip/PDF attachments, scheduled import
- 💰 **Net worth & reconciliation** - Balance snapshots, reconciliation center, fund-nature rules
- 🚀 **One-click deployment** - Docker Compose, ready out of the box

---

## Quick Start (Docker)

```bash
# 1. Clone
git clone https://github.com/JokerFuFu/xiaoxiaobill.git
cd xiaoyaoprivatebill

# 2. (Optional) copy the env template and adjust admin password / AI key
cp .env.example .env

# 3. Start
docker-compose up -d

# 4. Open http://localhost:8888
```

First login: `admin` / `admin12345` (change it under **Settings → Account** right away), or click "Just looking (demo data)" on the login page to explore with sample data.

The AI assistant is optional — leave `ANTHROPIC_API_KEY` empty and every analytics feature still works. Any Anthropic-compatible endpoint is supported (Kimi by default), configurable via `.env` or **Settings → AI & Models**.

### Local development

```bash
# Backend (http://localhost:5000)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py

# Frontend (http://localhost:3000, in another terminal)
cd frontend
npm install
npm run dev
```

Tests: `cd backend && pytest` · `cd frontend && npm run test`

---

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| Backend | Python 3.10+, Flask, Flask-Login/Session, Pandas, pdfplumber/pikepdf, APScheduler |
| Frontend | Vue 3.4, Vite 5, Vue Router 4, Pinia 2, ECharts 5 |
| Deployment | Docker Compose, Nginx (multi-stage build) |
| Storage | No database — plain files under `backend/data/`, per-user isolation |

---

## Acknowledgments

XiaoxiaoBill stands on the shoulders of two open-source authors:

> **Hessel2333** ([alipay_record_analysis](https://github.com/Hessel2333/alipay_record_analysis), the original inspiration and code base) → **dtsola** ([xiaoyaoprivatebill / Xiaoyao Bill Assistant](https://github.com/dtsola/xiaoyaoprivatebill), the direct upstream of this project — Vue 3 + Flask rewrite, modular blueprint architecture, Docker deployment) → **XiaoxiaoBill** (this project, maintained by JokerFuFu).

Original author dtsola: [dtsola.com](https://www.dtsola.com) · [Bilibili](https://space.bilibili.com/736015)

Main evolutions in this project on top of the upstream: bank PDF ingestion with cross-source dedup, transfer semantics, channel analysis, multi-user auth with data isolation, family members, AI assistant (chat / recognition / analysis), IMAP auto-import, net worth & reconciliation, income analysis, and large-scale refactoring with test coverage.

---

## License

[MIT](LICENSE) — copyright is stacked: the original work is © **dtsola**, and the additions/modifications in this project are © **JokerFuFu**. Please keep the full copyright and permission notices when reusing.
