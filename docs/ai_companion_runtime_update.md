## AI Companion Runtime Update — October 2025

This note captures the current implementation status of the Twist ERP AI stack and how it aligns with the expansion blueprint.

### Orchestrator & Skill SDK
- `AIOrchestrator` now coordinates modular skills, records usage metrics, persists conversations, and routes failures to a legacy RAG chain.
- Skill contract (`BaseSkill`) exposes `is_authorised` so that domain assistants can enforce RBAC-aware access before surfacing data.
- Data Migration, Reporting, and Policy skills include role heuristics plus better task actions (run validation, commit, open dashboards).

### Context & Memory Hub
- `ContextBuilder` enriches every request with:
  - Short-term context: active page, derived user roles, company metadata, and up to three pending migration jobs.
  - Long-term memory snapshots: last five user, company, and global memories.
  - Recent telemetry extracted from the feature store.
- `MemoryRecord` bug fixed so user/company scope is honoured when saving.
- `/api/v1/ai/chat/` responses now return a `context` payload so the frontend can surface what the assistant is seeing.

### Telemetry & Knowledge Loops
- New `AITelemetryEvent` model and `TelemetryService` capture chat activity, auto-suggestions, and feedback interactions.
- `compile_training_dataset` Celery task exports up to 200 approved prompt/completion pairs for downstream fine-tuning jobs.
- Thumbs feedback links to the last assistant message and generates `AITrainingExample` rows with status workflow (approved/review/rejected).
- Data migration status transitions emit telemetry events so proactive skills can spot stalled imports without polling.

### Conversation Continuity & Plan Guidance
- AI conversations now hydrate from server history, resume where the user left off, and surface short-term context (roles, pending migrations) alongside replies.
- A dedicated `PlanSkill` routes roadmap and strategy questions to the embedded `docs/ai_plan.md` corpus so the assistant can quote the canonical implementation plan.

### Responsible AI Controls
- Vector search is tenant-aware: each company can be indexed into `VECTOR_DB_PATH/<company_id>/faiss`, with fall back to the global corpus.
- Skills degrade gracefully if the caller lacks the right role (e.g., analytics limited to finance/executive, migration to data admins).
- Feedback records include structured payloads for auditability.
- Telemetry snapshots keep per-user trails for future privacy review dashboards.

### Model & Index Configuration
- Default models remain `mistralai/Mistral-7B-Instruct-v0.1` (LLM) and `sentence-transformers/all-MiniLM-L6-v2` (embeddings). The management commands accept a `--company-id` flag for scoped indexing.
- Vector indices save under `./chroma_db/<index>/faiss` so that backups can segregate global vs. tenant knowledge.

### Frontend Assistant Enhancements
- The side-panel now displays recent roles and pending migrations for assistant replies, and accepts memory saves via `/remember`.
- Encodings fixed (no en-dash artefacts) and skill badges remain readable.

### Operations Console
- System admins have an “AI Ops → Training Review” workspace that lists pending training examples and lets them approve or reject entries before they feed fine-tuning jobs.

### Next Steps
1. Expand telemetry hooks beyond data migration (e.g., workflow bottlenecks, budget breaches) to fuel proactive coaching.
2. Automate policy document ingestion per company and wire to guardrail regression tests.
3. Wire the training dataset export to scheduled LoRA/adapter jobs and surface run-history in the AI Ops workspace.
4. Provide reviewer notes and bulk actions in the training example console to streamline compliance audits.

This implementation closes the outstanding items in the AI expansion blueprint for the current milestone; future increments can build atop the telemetry and training hooks shipped here.
