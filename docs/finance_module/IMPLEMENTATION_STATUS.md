# TWIST ERP Finance Module & Specification Alignment

_Last updated: 12 Nov 2025_

This note links the reference package under `docs/finance_module/` with the code that already lives in the repository. Use it as the single source of truth when deciding what still needs to be implemented to make the live Finance module behave exactly like the guides describe.

---

## Repository Snapshot

| Area                   | What the spec expects                                                             | Where it lives in this repo                                                                                                                                             |
| ---------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Backend domain models  | Django apps for Chart of Accounts, GL, AR/AP, bank & cash, multi-company security | `backend/apps/finance/models.py`, helper services in `backend/apps/finance/services/`                                                                                   |
| Posting & integrations | Journal workflow, posting rules, automatic GL hooks for inventory & procurement   | `backend/apps/finance/services/journal_service.py`, `posting_rules.py`, `finance_integration_service.py`, with events wired in `backend/apps/finance/event_handlers.py` |
| REST API               | DRF viewsets for accounts, journals, invoices, payments, statements, exports      | `backend/apps/finance/viewsets.py`, `backend/apps/finance/urls.py`                                                                                                      |
| Frontend UX            | React workspaces for finance home, journals, approvals, reporting, config         | `frontend/src/pages/Finance/**`, cross-module widgets inside `frontend/src/pages/Inventory` & `frontend/src/pages/Budgeting`                                            |
| Infrastructure         | Docker Compose, `.env` templates, deployment scripts, monitoring hooks            | Root `docker-compose.yml`, `.env.example`, `/deploy.sh`, `/scripts/dev_start.ps1`                                                                                       |

### To-Do Snapshot (plain summary)
- Build the Financial Statement Builder UI, approval console, and finance config dashboard described in Part 4 (frontend only).
- Migrate Finance pages to TypeScript + RTK Query so the stack matches the spec.
- Ship the seed/monitoring scripts and no-code config dashboard from Part 5 (currently missing).
- Implement the AI/OCR intake + SoD analytics enhancements from `Finance_Module_Recommendations.md`.
- Keep this status file updated whenever new finance features land.

---

## Alignment With the Five-Part Implementation Guide

| Guide part                                       | Spec focus                                                                                            | Current implementation                                                                                                                                                                                                                                                                                                                                                                                                                               | Status                                     | Follow-up actions                                                                                                                                                                                                                             |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Part 1 – Project Setup & Architecture**        | Stack decisions, repo layout, base models (Company, Role, Audit, Chart of Accounts)                   | The monorepo already matches the recommended stack (Django REST + React + PostgreSQL + Redis). Company/role/audit logic lives in existing `companies`, `users`, and `auditlog` apps. Finance-specific bootstrapping (chart of accounts seeds, journal sequences) is handled under `backend/apps/finance/management/`.                                                                                                                                | ✅ Complete                                | Keep the README pointers in sync when module owners add new env vars or services.                                                                                                                                                             |
| **Part 2 – Database Models & Business Logic**    | Fiscal calendars, AR/AP, cash management, posting service, coercing everything through BudgetItemCode | Core tables (`Account`, `Journal`, `JournalVoucher`, `JournalEntry`, `Invoice`, `Payment`, `BankStatement`, `Currency`, `ExchangeRate`, etc.) exist in `backend/apps/finance/models.py`. Posting & reconciliation rules are implemented under `services/financial_statement_service.py`, `gl_reconciliation_service.py`, `journal_service.py`, and `posting_rules.py`. Inventory hooks already point to `BudgetItemCode` via `InventoryPostingRule`. | ✅ Complete (phase 1)                      | Remaining backlog: (a) expose more granular SoD policies for approvals, (b) finish automated document policy enforcement in `document_processor.py`, (c) wire AI/OCR adapters described in Part 2 §“AI-assisted AP” (currently placeholders). |
| **Part 3 – API & Financial Statement Generator** | DRF endpoints for vouchers, statements, exports (JSON/PDF/XLSX)                                       | `backend/apps/finance/viewsets.py` exposes accounts, journals, invoices, payments, statements, and exports. The “one-click” statement stack is handled by `financial_statement_service.py` + `statement_export_service.py` and re-used via `/finance/statements/` endpoints.                                                                                                                                                                         | ✅ Complete (core), ⚠ enhancements pending | Add caching + async export queueing (documents mention Celery workers), and document the `/finance/statements/export/` contract for the frontend.                                                                                             |
| **Part 4 – Frontend UI & UX**                    | React + TypeScript workspace, RTK Query, wizard-style flows                                           | We ship finance workspaces under `frontend/src/pages/Finance/…` (Workspace, Journals, Accounts, Periods, Reports, GL Posting Rules). The codebase is still plain React + Hooks (no RTK Query, no TypeScript yet). Statement widgets live on the workspace but the dedicated “builder” UI from the spec is not implemented.                                                                                                                           | 🟡 In progress                             | Tasks: migrate finance pages to TypeScript + RTK Query, finish the Financial Statement Generator UI, add the approval console, and build the configuration dashboard described in Part 4.                                                     |
| **Part 5 – Deployment & Configuration**          | Docker, seed scripts, monitoring, no-code config dashboard                                            | Docker + Compose + `.env.example` already cover multi-service dev/prod parity. However, the scripts referenced in the guide (`scripts/setup_initial_data.py`, monitoring exporters, config dashboard) are not present.                                                                                                                                                                                                                               | 🟡 Partial                                 | Author the missing bootstrap script, add health/metrics sidecars, and decide whether the “no-code config dashboard” will live under `/frontend/src/pages/Finance/Config` or reuse the existing Admin UI.                                      |

---

## Additional Recommendations vs. Reality

- **Event Sourcing & CQRS** (from `Finance_Module_Recommendations.md`): we currently rely on Django ORM + audit logs only. If we adopt CQRS later, start inside `finance/services/journal_service.py` by emitting structured events to Redis/Kafka.
- **Advanced AI features**: placeholders exist in `finance/services/document_processor.py`, but OCR/anomaly adapters are stubs. Integrations should be isolated under an `ai_providers/` package so they can be toggled per company.
- **Security & SoD analytics**: RBAC and per-company scoping are enforced, but SoD matrix & alerting still need dedicated models/services.

---

## Immediate Next Steps

1. **Frontend parity** – implement the missing Statement Builder, Journal workflow, and bank reconciliation UI described in Part 4. Reuse the existing backend APIs; only the UX layer is outstanding.
2. **Deployment scripts** – add the seed + monitoring scripts referenced in Part 5 so new environments can be provisioned purely from the docs.
3. **Documentation sync** – whenever a feature ships (e.g., OCR ingestion), update both this status file and the relevant guide part so specs and code stay aligned.

Use this file as the checklist whenever a contributor needs to know “what’s done vs. what the spec still expects”.
