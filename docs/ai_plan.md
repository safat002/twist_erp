Short version:
A persistent conversational AI assistant becomes a core platform layer, not a feature. It touches auth, data access, audit, UI, performance, onboarding, and even legal/compliance. So we have to design for it early.

Let’s go step by step.

1. What “continue regular conversation” actually means in product terms

When you say “continue regular conversation,” that implies these abilities:

Memory of context across turns

User: “Show me pending POs above 10k.”

AI: [shows list]

User: “Okay approve #3 and #5.”

AI understands “#3 and #5” refers to the last list.
This means the AI keeps short-term working memory inside that chat session.

Memory of user preferences / company environment

User: “From now on, show cash in BDT, not USD.”

Next day, AI follows that automatically.
That means you’re saving some long-term per-user “preferences” or per-company “policy notes.”

Natural language to action

“Create a PO for Vendor ABC for 500 units of Item 123 at 7.5 USD.”
AI should draft that PO in the system and ask for confirmation.
This means the AI isn’t only answering questions — it’s controlling the ERP.

Cross-module reasoning

“Why is our cash low this week?”
AI might pull AP due dates (Finance), unpaid AR (Sales), slow-moving inventory (Inventory), and approval bottlenecks (Workflow).
This is not just “chat.” This is cross-module analysis.

That is not just Q&A. That’s an operator/assistant that can drive the system.

So we need to treat the AI assistant like:

a user with a role,

an integration layer,

a compliance surface.

Now let’s see how that affects your system.

2. Security & RBAC impact

This is the #1 impact.

2.1 The AI must act under a role

When someone chats with the AI inside Twist ERP, the AI can’t just “see everything.”
The AI must inherit the session context:

user_id

active_company_id

active_company_group_id

roles and field-level visibility of that user

So if a warehouse manager asks:

“Show me employee salaries,”
the AI must refuse, because that role cannot view salary fields.

If the Group CFO asks:

“Show me consolidated cash position across all companies,”
the AI is allowed, because that role has multi-company visibility.

What this means for you:

The AI layer is not global. It is always running “as the user.”

Every AI call must contain the same RBAC/field masking logic you already built in Phase 0/1.

This is good news: you’ve already designed RBAC, company scoping, and field-level access. So we reuse that foundation.

2.2 Audit trail

Anything the AI reveals or does must be logged in AuditLog.

Examples:

User: “Approve PO 9812.”
AI: approves PO 9812 using workflow rules.

That has legal impact. So you must log:

user_id who requested it,

action_type="AI_ACTION_APPROVAL",

which record was touched,

timestamp,

old status → new status,

which workflow rule allowed it.

So Phase 2 audit and Phase 1 workflow engine become mandatory gatekeepers for AI actions. That’s good — we already planned that.

3. Data access layer impact

To answer natural questions like “What’s hurting our cash?”, the AI needs to query data from Finance, Procurement, AR, AP, Inventory, Workflows.
That means you need a query abstraction layer in the backend.

Right now, without AI, your UI will fetch specific pages via specific endpoints (e.g. /api/ap/aging, /api/inventory/stock). That’s fine for humans.

But for AI:

You’ll need endpoints/services that can answer flexible data questions:

“top unpaid supplier bills by due date”

“list of POs stuck in approval >48h”

“stock quantity of SKU BOLT-10 in Warehouse Main”

So you’ll build something like an internal “Data Service Layer” that:

Takes structured requests (e.g. { metric: "AP_AGING", company_id: X, bucket: ">30d" })

Runs the correct SQL/logic

Returns clean structured data with labels

The AI will call these building blocks to form answers.

Effect on project:

You need a stable library of “business queries” (AP aging, AR aging, stock levels, cash summary, etc.)

That library must respect company_id scoping, role permissions, field masks

That library becomes reusable for:

Dashboard Builder (Phase 4)

AI assistant (Phase 5)

Reporting API in the future

So this AI requirement actually pushes you to formalize that query layer earlier, which is healthy.

4. Chat memory impact

You said you want the AI to “continue regular conversation.” That means: context and memory.

We need to divide memory into 2 types:

4.1 Session memory (short-term)

Only lives in the active chat session.

Example: AI remembers which POs it just showed.

You can store this in RAM / Redis / ephemeral table keyed by session_id.

This is relatively easy. It doesn’t permanently change your data model.

4.2 Long-term memory (preferences, working style)

“From now on, always show currency in BDT.”

“Use warehouse ‘Main Dhaka’ as default unless I say otherwise.”

“I care mostly about overdue AR, not AP.”

This becomes persistent. That means you’re now storing personalization info.

You’ll need a table in the CompanyGroup DB something like:

UserAIPreferences

user_id

company_id

preference_key

preference_value (jsonb)

timestamps

Impact:

You’re now storing behavioral data about a specific individual.

That must also be protected by RBAC (another user shouldn’t see my preferences unless they’re an admin).

This table should be included in backup (Phase 0 backup flow).

This table needs to be auditable if it affects business actions (“always auto-approve POs under 5000” is dangerous).

You will need guardrails:

The AI should not accept “remember my CFO password” or “always approve PRs under 2k without asking” without higher-role confirmation. You’ll have to block certain preference types for safety.

5. Workflow / action execution impact

A conversational AI that just answers questions is safe-ish.

A conversational AI that can do things (approve POs, create SOs, post invoices) is powerful but risky. Here’s how it affects you:

5.1 AI as an operator

When the user says:

“Approve PO 123 and send it to the supplier,”

the AI must:

Check workflow: Is this PO awaiting approval? Is the user allowed to approve per Workflow Studio rules?

If not, AI must refuse.

Perform the action through the normal service layer (the same function the normal UI uses).

Record the approval in the workflow instance state.

Post to AuditLog:

action_type="WORKFLOW_APPROVE"

plus flag via_ai: true

You are not creating a secret path. You are just letting AI drive the same API that buttons would drive.

This means that:

Phase 2/4 services (approve PO, post GRN, post ARInvoice, etc.) must be callable in a “headless” mode.

You cannot let the AI “just write SQL.” It must go through the same business logic layer that enforces workflow and roles.

Result: the conversational assistant is not a hack. It is literally another frontend.

5.2 Confirmation model

For safety, define “destructive / financial-impacting actions” that require confirmation:

Posting AP Bill to GL

Issuing Payment

Approving high-value PO

Posting Delivery that reduces inventory

Creating AR Invoice

The AI should:

Draft the action.

Read back a summary.

Ask “Confirm?”.

Only then execute.

This protects you legally and operationally.

6. Compliance / audit / legal impact

This is huge in ERP context.

If AI can answer questions like:

“How much salary did we pay HR team last month?”

“Which donor project is overspent?”

“Which supplier is flagged for compliance?”
…that’s sensitive.

You’ve already planned:

field-level visibility by role,

AuditLog for access,

company isolation.

Now you must extend that to AI chat:

Every time AI returns sensitive values, you log that read in AuditLog the same way you would if the user manually opened that screen.

Why?
Because an auditor later might ask: “Who saw salary data?” and you need to prove it — even if they saw it via chat.

So AI → audit is mandatory.

7. UX / product impact

Once you ship conversational AI:

It becomes the “face” of your product.

Users expect to ask in plain language instead of searching menus.

This lowers training cost, which is great for sales.

But it increases support expectations, because now you are “promising intelligence.”

This means:

Your knowledge model (internal help/article layer, explanations of what PO/GRN/COGS mean in their business) becomes part of onboarding.

You need good, consistent field labels and descriptions in metadata so the AI can explain screens using human language.

Example: FieldDefinition should include a help_text / business_description.

That way AI can say “Credit Limit is the maximum exposure you allow this customer.”

This is a minor content task, but it matters a lot to perceived intelligence.

8. Performance / infra impact

Conversational AI = frequent requests.

What changes:

You’ll call your AI reasoning model a lot to summarize data or interpret intent. That’s CPU/GPU cost or external inference cost.

Each request may also call internal data services (Finance/Inventory queries).

You need rate limiting and session limits per user/company to avoid overload.

Also, the AI may ask follow-up questions internally like:

“Get top 5 overdue AP.”

“Get current cash by bank account.”

“Get items with stock < reorder level.”

You should cache these sub-results per user/session for a short window to avoid hammering Postgres every message.

9. Where this affects your roadmap phases

Let’s map impact to your timeline:

Phase 0 / 1 impact

You’ve already got RBAC, session scoping, audit logging, CompanyGroup isolation.
Good. The AI layer will sit on top of that.

You may want to store UserAIPreferences early (Phase 1 or Phase 5), but at least define the table now so migration is easy later.

Phase 2 impact

You’re building Finance, Procurement, Sales, Inventory logic, approval and posting flows.

You MUST implement these flows as callable services with clean permission checks, not just stitched directly in controller code.

Because the AI in Phase 5 will call those services programmatically.

Example pattern:

approve_purchase_order(po_id, acting_user_id) → returns status

The UI calls that, and the AI can also call that.

If you bury approval logic directly in the UI layer, AI can’t reuse it safely.

Phase 3 impact

Your data migration engine produces structured clean data and creates metadata for custom fields.

The AI can later use that metadata to talk naturally about those custom fields.
(“Show me stock by GSM for dyed fabric batches from last week” only works if GSM is in metadata with a friendly label.)

So in Phase 3, when you add new fields from import, also capture human-readable labels / descriptions. AI will need those.

Phase 4 impact

Form Builder, Custom Module Builder, Workflow Studio, Dashboard Builder all generate metadata.

AI can read that metadata to understand:

what the module is,

what the fields mean,

what workflow is blocking something,

which dashboard KPIs matter.

AI can answer “Why is PO 9987 blocked?” by reading workflow state from Workflow Studio.

AI can navigate custom modules created by customers themselves, because it can inspect EntityDefinition instead of requiring hardcoded logic.

So Phase 4 basically gives AI a map of the system.

Phase 5 (AI Companion) becomes:

Natural language intent parsing → figure out “what user wants.”

RBAC-aware data fetch → run safe queries.

Conversation memory → keep context.

Action execution → call your service layer.

Audit + explain what was done.

With conversational continuity, Phase 5 is not just “chatbot help,” it becomes “voice/assistant operator that drives the ERP.”

10. Summary: How ongoing AI conversation affects Twist ERP

Must-haves now (some start earlier than Phase 5):

RBAC enforcement everywhere
AI must inherit user’s company_id, role, and field visibility. You’ve already designed this correctly — don’t weaken it.

Full audit
Every AI answer and every AI-triggered action must write to AuditLog, same as if the human clicked a button.

Stable business service layer
Approve PO, post GRN, post ARInvoice, run AP aging, etc. must exist as callable backend services with permission checks.
Both UI and AI call those services. No “secret logic in React only.”

Metadata completeness
Field definitions, help text, workflow steps, dashboard metrics — all must live in metadata so the AI can explain them and navigate them, even if they’re custom or per-company.

User AI preferences (long-term memory)
You’ll introduce per-user preference storage (like default currency, default warehouse, reporting style). This will live in Postgres with RBAC and audit.

Data access wrappers
Build a query layer for common operational summaries (AP aging, stock, cash, overdue approvals).
That same layer will power: Dashboard Builder (Phase 4), AI (Phase 5), and CFO views.

If you follow that, adding a conversational AI assistant later is not “bolt-on.” It will feel native, safe, and actually usable by finance and operations — not just a toy chatbot.
