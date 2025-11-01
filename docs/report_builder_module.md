# Report Builder Module

## Overview

The metadata-driven Report Builder enables no-code users to assemble tabular reports that honour the ERP's role-based permissions. Reports reference scoped datasets (dynamic entities or static Django models) and store their definitions in the central metadata registry (`MetadataDefinition`, kind `REPORT`).

### Highlights
- Dedicated Django app `apps.report_builder` with `ReportDefinition` model.
- Query engine layers (`backend/modules/report_builder`) for filters, sorting, dataset preparation, and calculated fields.
- REST endpoints under `/api/v1/report-builder/definitions/` secured by the new permission `can_build_reports`.
- React workspace (`/reports`) integrated into the No-Code tools menu with dataset picker, field selection, filters, sorting, calculated fields, and preview table.

## Backend Structure

- `ReportDefinition`: scoped (company/group/global) metadata-backed entity with JSON payload describing data source, fields, filters, sorts, and calculations.
- Metadata sync: every save/publish writes a new `MetadataDefinition` version (`kind="REPORT"`) ensuring full history and alignment with the ERP master plan.
- Query engine: `ReportQueryEngine` orchestrates dataset resolution, applies filters/sorting (`modules/report_builder/filters|sorting`), materialises data (`data_prep`), and evaluates expressions (`calculations`).
- Dataset registry: dynamic entities auto-exposed; static datasets can be added via `STATIC_DATASETS`.
- Preview endpoint returns rows, field metadata, and summarised totals for the React preview grid.

## Frontend Workspace

- Located at `frontend/src/pages/ReportBuilder/ReportBuilder.jsx`.
- Modular components in `frontend/src/components/ReportBuilder/` covering dataset selection, field configuration, filter/sort builders, calculated fields editor, and preview.
- Menu integration: "Report Builder" appears within the No-Code Tools cluster; route `/reports`.
- Builder enforces permission tags; datasets inherit additional requirements where supplied.

## Permission Model

- New permission code `can_build_reports` provided via migration `backend/apps/permissions/migrations/0003_add_report_builder_permission.py`.
- API views require both authentication and company context (`HasPermission`).
- Dataset access can be further constrained with per-dataset permission lists.

## Next Steps / Extensions

- Populate `STATIC_DATASETS` for high-value core modules (Finance, Inventory, Procurement) with curated field maps.
- Support joins across related entities (metadata relationship graph).
- Add grouping/aggregation layers and export endpoints (CSV, Excel, PDF).
- Expand calculated field sandbox to include reusable functions/macros and validation hints.
- Surface report definitions inside dashboard widgets once analytics module is extended.

## Verification

- `venv/Scripts/python.exe -m compileall apps/report_builder modules/report_builder` confirms backend syntax.
- Manual smoke of builder UI recommended (`npm run dev`) once company context and auth tokens are available.
