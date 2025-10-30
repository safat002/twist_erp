Awesome. Let’s lock this down as an actual implementation plan so it’s buildable.

These “additional features” are:

1. Unified Task & To-Do System
2. Calendar Integration (push ERP tasks/reminders into Outlook calendar)
3. Email Awareness Integration (ERP shows “you have X unread emails”)
4. Notification System (bell + full Notification Center with status, grouping, audit)
5. AI Assistant Operational Nudging

Below is the final plan with scope, data model, backend, frontend, security, audit, rollout order.

---

## 1. Unified Task & To-Do System (“Workboard”)

### 1.1 Goal

Give every user one place to see:

- Tasks assigned to them by others (system tasks, accountable)
- Tasks/to-dos they create for themselves (personal reminders)

Tie tasks to ERP records (PO, CAPA, SLA ticket, donor report, loan follow-up, payroll, etc.). Sync due dates to calendar. Drive KPIs for critical tasks.

### 1.2 Core Object: `TaskItem`

Fields:

- `task_id`

- `type`:

  - `"system"` → assigned by someone else / by ERP workflow
  - `"personal"` → created by the user for themselves

- `title`

- `description`

- `assigned_to_user_id`

- `assigned_by_user_id` (self for personal)

- `due_date` (optional for personal, required for critical system tasks)

- `priority` (`low` / `normal` / `high` / `critical`)

- `status` (`not_started` / `in_progress` / `blocked` / `done` / `overdue`)

- `linked_entity_type` (optional, e.g. `PO`, `OutOfBudgetApproval`, `CAPA`, `SLA_Ticket`, `LoanAccount`, `GrantReport`, `PayrollRun`)

- `linked_entity_id` (optional)

- `visibility_scope`:

  - `"private"` → only the user sees it
  - `"manager_visible"` → the assigner & the assignee’s manager can see status
  - `"team_visible"` → cost center / branch / project-level visibility (for escalations & compliance work)
  - `"exec_visible"` → for escalated/high-risk items (safety NCR, donor breach, SLA breach)

- audit timestamps

### 1.3 Behavior

- Manager can create a system task for a subordinate or function owner.

- User can create their own personal to-do task.

- Both appear in the same “My Tasks” list for the user.

- For system tasks:

  - If overdue and high/critical, Workflow Studio can escalate.
  - Escalations update `visibility_scope` automatically (ex: goes from manager_visible → exec_visible).
  - Certain system tasks can impact KPI if missed (CAPA, donor report deadlines, SLA fix, payroll close).

- For personal tasks:

  - No KPI.
  - Never escalates automatically.
  - Never forced visible to manager unless user voluntarily shares.

### 1.4 UI

#### “My Tasks” panel:

- Shown on homepage dashboard.
- Shows tasks sorted: overdue critical → due today → due tomorrow → upcoming → no due date.
- Each row shows:

  - checkbox/status chip,
  - title,
  - due marker (“today 17:00”),
  - small icon if linked to ERP object.

- Inline quick actions:

  - Mark in progress
  - Mark blocked
  - Mark done
  - Snooze / move due_date (if allowed)

#### “Team Tasks” / “Delegated Tasks”

- For managers / owners of scopes.
- Shows tasks they assigned to others.
- Shows status, overdue warnings.
- Lets them nudge or escalate.

### 1.5 Backend / Services

- CRUD API for TaskItem.
- Status update endpoint.
- Escalation trigger (calls Workflow Studio when rule matches, e.g. overdue + priority=critical).
- Calendar sync trigger (see Section 2).
- Permission enforcement:

  - User can always see their own tasks.
  - Manager can see system tasks they assigned.
  - Higher roles can see tasks whose `visibility_scope` escalated to them.
  - Private/personal tasks are never shown to anyone else.

### 1.6 Security & RBAC

- We reuse the permission model:

  - `create_task_for_other_user` (scoped by cost_center/branch/grant/project)
  - `view_team_tasks`
  - `escalate_task`
  - `close_task_requires_authority` (for compliance tasks)

- We check both:

  - role permissions,
  - data scope (you can’t assign tasks in a branch you don’t control).

### 1.7 Audit & KPI

- Every system task creation → AuditLog entry (who created, who assigned, what entity it’s tied to).
- On overdue for critical category (CAPA, SLA, donor compliance, payroll close, etc.) → KPI penalty recorded for that cost center / branch / function.
- Personal tasks do NOT generate KPI.

---

## 2. Calendar Integration (Outlook Push)

### 2.1 Goal

Keep people honest with time. Due dates in ERP should exist on the user’s real calendar so no one can say “I forgot.”

### 2.2 Behavior

- Any `TaskItem` with:

  - an `assigned_to_user_id` = current user
  - AND a `due_date`
    → creates (or updates) an Outlook calendar reminder for that user.

- If task is rescheduled, ERP updates that Outlook event (using stored calendar event ID).

- When task is completed, ERP may:

  - optionally rename the calendar event with “[Done] …”
  - or mark it internally and leave Outlook alone (implementation detail decision; safe default is mark internally only).

- For workflow-driven events (like “Payroll approval cutoff today at 17:00”), ERP can also create events directly for approvers.

- For multi-person approvals (Capex board, PAR review, donor report review), Workflow Studio can generate group calendar events for all approvers.

### 2.3 UI

Homepage “My Day” tile:

- Shows “Next event starting in 15 minutes: Payroll Approval Board”.
- Shows “Budget Submission Review at 16:30 with CFO”.
- Clicking opens system calendar app (Outlook), not our own calendar UI.

### 2.4 Security

- We only push ERP obligations → Outlook.
- We do NOT pull personal/private meetings from Outlook → ERP.
- We do NOT show other people’s calendars internally.

---

## 3. Email Awareness Integration

### 3.1 Goal

ERP is not an email client. ERP just says: “You’ve got mail relevant to your responsibilities.”

### 3.2 Behavior

- ERP periodically checks (metadata only) for unread relevant emails for the current user.

  - “Relevant” means connected to ERP work: workflow approvals, escalations, SLA escalations, finance cutoffs, donor queries, etc. (This will be filtered by sender/subject rules we control.)

- If there is exactly 1 new relevant unread email:

  - Show in notification bell:

    - `New email from: [Sender Name] — "[Subject]"`.

  - Clicking opens Outlook directly to that email.

- If there are multiple unread relevant emails:

  - Show one grouped notification:

    - `You have 7 unread important emails in your inbox.`

  - Clicking opens Outlook inbox (or filtered folder if we set one up later).

- We do NOT display the full email body or inbox content inside ERP.

### 3.3 Security

- We never store email bodies in ERP.
- We never expose salary, donor confidential info, branch-sensitive borrower info in the ERP UI unless the user already has permission.
- We do not let a user without payroll scope see “Payroll approval reminder” mail details.

---

## 4. Notification System

### 4.1 Goal

Provide a consistent, auditable “inbox” for ERP events:

- Approvals you owe
- Tasks assigned to you
- Escalations and SLA/fire-risk
- AI nudges (time-sensitive reminders)
- Email awareness

This drives accountability and compliance.

### 4.2 Core Object: `Notification`

Fields:

- `notification_id`
- `timestamp`
- `type`

  - `approval_required`
  - `task_assigned`
  - `task_overdue`
  - `escalation`
  - `email_alert`
  - `time_alert` (meeting soon / deadline soon)
  - `ai_tip`

- `module` (Finance, Procurement, HR, SLA, Production, QC, Microfinance, Grant, etc.)
- `title` (short label)

  - Example: `GRN #123 requires approval`
  - Example: `Out-of-Budget request for Cost Center 210`
  - Example: `CAPA NCR-009 overdue`
  - Example: `SLA ticket #884 at risk`
  - Example: `Payroll sign-off due today`
  - Example: `You have 5 approvals waiting`
  - Example: `You have 10 unread relevant emails`

- `details` (short structured info, permission-filtered; for email_alert with >1 email we don’t include details per email)
- `status`

  - `pending`
  - `approved`
  - `rejected`
  - `resolved`
  - `cancelled`
  - `escalated`
  - `expired`

- `severity`

  - `info`
  - `normal`
  - `urgent`
  - `critical` (e.g. SLA about to breach, payroll cutoff today)

- `linked_entity_type` / `linked_entity_id`
- `action_url` (where click goes: ERP approval screen, TaskItem detail, Outlook email, etc.)
- `read_state` (`unread` / `read`)
- `cleared_state` (`active` / `cleared_by_user`)

### 4.3 Live status sync

Notification status updates automatically as real work is done:

- If you approve GRN #123, that notification becomes `status=approved`.
- If CAPA NCR-009 is finally closed, that notification becomes `status=resolved`.
- If the request was cancelled upstream, notification becomes `cancelled`.

This turns the notification center into an audit trail of “what happened / who acted / when.”

### 4.4 Bell Dropdown Behavior

The bell (top-right header) shows:

- Latest ~10 notifications.
- Grouped by type:

  - **Approvals (2 pending)**

    - “Out-of-Budget request: Maintenance”
    - “Capex request: Forklift”

  - **Tasks (3 new assigned to you)**
  - **Escalations (1 critical NCR overdue)**
  - **Email (You have 7 unread important emails)**
  - **Time Alerts (Budget Review meeting in 15 min)**

Within each section:

- We can show either a combined summary (“You have 5 approvals waiting”) or show top 1-2 most urgent items.
- Each section visually carries severity color (e.g. red chip for “critical today”).

Click behavior:

- Clicking a line routes to `action_url`:

  - Approvals → ERP approval list
  - Task block → My Tasks page
  - Email alert → Outlook
  - Escalation → escalation view
  - Time alert → Outlook calendar entry / ERP task

Also include a button at the bottom: **“View all notifications”** → full Notification Center.

### 4.5 Full Notification Center Page

This is a full-screen page with filters:

- Filter by Type (Approvals / Tasks / Escalations / Email / Time Alerts / AI Tips / All)
- Filter by Status (Pending / Approved / Resolved / Cleared)
- Filter by Time (Today / 7 days / 30 days / All)

Columns:

- Timestamp
- Module
- Title
- Status chip
- Severity chip
- Action button (Open)
- Clear button (which sets `cleared_state=cleared_by_user` but keeps the row forever for audit)

### 4.6 Snooze / Remind Me Later

From the bell or the full page:

- User can snooze certain notifications (e.g. “Remind me in 1 hour,” “Remind me tomorrow morning”).
- System will resurface it as a fresh notification when time hits.
- Snooze does NOT mark as “approved” or “cleared,” it just delays nagging.

### 4.7 One-click “Assign Follow-up Task”

For certain notifications (escalations, overdue CAPA, SLA at risk, donor compliance alert, etc.):

- Add button: “Assign task”
- Clicking creates a new `TaskItem` assigned to a subordinate, linked to that event.
- That task shows up in the subordinate’s My Tasks and syncs into their calendar.

This connects:
**Notification → Action → Accountability**, in one step.

---

## 5. AI Assistant Operational Nudging

### 5.1 Goal

AI is not chat for fun. AI is the operations coordinator. It surfaces urgency.

### 5.2 Behaviors

- “Your budget review meeting starts in 15 minutes. Want to open the agenda?”
- “You have 2 pending approvals. One is payroll cut-off today (critical).”
- “CAPA NCR-009 is overdue. If it’s not closed today, Plant A will take a compliance KPI hit.”
- “You assigned 3 tasks to Rafiq yesterday. All still ‘not_started’. Escalate to his manager or snooze?”

### 5.3 Actions AI can offer

- “Open approval list”
- “Open My Tasks”
- “Snooze this reminder 1 hour”
- “Assign escalation task to supervisor”
- “Mark task in progress / done”

Every AI-triggered action:

- Respects permission and data scope.
- Writes AuditLog with `via_ai: true`.

### 5.4 Access control

AI only references:

- Tasks and notifications the user is authorized to see.
- It summarizes, but never leaks restricted data (like another branch’s delinquent borrowers or HR payroll numbers if the user lacks payroll permission).

---

## 6. Security, RBAC, Segregation of Duties Integration

We integrate all new pieces into the same permission model you already approved:

- New permissions:

  - `view_notification_center`
  - `view_my_tasks`
  - `assign_task_to_subordinate`
  - `escalate_task`
  - `snooze_notification`
  - `clear_notification`
  - `approve_out_of_budget_for_cost_center`
  - `approve_over_tolerance_price`
  - `approve_unplanned_capex`
  - `approve_payroll_run`
  - `approve_quarantine_release`
  - etc.

- All those are scope-bound:

  - By company
  - By cost center / branch / plant
  - By program/grant (NGO)
  - By HR payroll scope
    So a plant manager can’t see HR payroll alerts. A loan officer can’t see donor escalations for a grant they don’t work on.

- Segregation of duties continues to apply:

  - You cannot approve your own Out-of-Budget request.
  - You cannot post/pay the same AP Bill you created.
  - You cannot approve payroll run if you prepared it.
  - You cannot assign a CAPA task to yourself and also close it as “done” without review if policy says two-person check.

  These SoD checks run before allowing “approve” or “close” actions from notifications.

---

## 7. Rollout Order (How to Build This Safely)

**Step 1: Task/To-Do module (Workboard)**

- Implement `TaskItem`.
- Build My Tasks UI + Team Tasks UI.
- Add calendar push for due_date.
- Respect visibility_scope, KPI flagging for system tasks only.

**Step 2: Notification Center core**

- Implement `Notification` model.
- Build bell dropdown (last ~10, grouped by type).
- Build Notification Center page with filters, status, clear.
- Hook notifications into Workflow Studio events (new approval, escalation, overdue task).

**Step 3: Email awareness integration**

- Add “You have X unread relevant emails” notification type.
- Single message if multiple unread emails.
- Sender+subject preview if only one.
- On click, launch Outlook directly.

**Step 4: AI assistant nudging**

- AI reads the user’s tasks + upcoming due + urgent notifications.
- AI surfaces: next meeting, overdue critical, approvals that have KPI impact today.
- AI offers snooze / escalate / open.

**Step 5: Severity, snooze, assign-from-notification**

- Add severity to notifications.
- Add snooze/remind-me-later.
- Add “Assign follow-up task” button from escalation-type notifications (ties notification flow to accountability downstream).

This order works because:

- Step 1 makes ERP usable daily (people start living in My Tasks).
- Step 2 adds visibility/accountability (notifications + audit trail).
- Step 3 plugs in mail awareness without storing private email.
- Step 4 makes AI helpful, not just pretty.
- Step 5 adds polish and management pressure tools.

---

## 8. What We Get After Implementing This

- Homepage becomes true “My Day”:

  - Next calendar items (from ERP calendar pushes),
  - My Tasks / To-Dos (both personal and assigned),
  - My Approvals,
  - Critical Alerts / Escalations,
  - Email awareness (“you have 7 important unread emails”).

- Notification Bell becomes mission control:

  - Grouped notifications so users aren’t spammed.
  - High-risk stuff is visually prioritized.
  - Urgent approvals and SLA fires are obvious.
  - Clicking jumps directly into the action screen (or Outlook).

- Notification Center becomes legal memory:

  - We can prove we notified you.
  - We can prove you approved.
  - We can prove when it escalated, who it escalated to, and when it was resolved.
  - We can show management who keeps ignoring critical items.

- Tasks become the enforcement layer below management:

  - You assign work directly from a notification (e.g. CAPA overdue).
  - Your subordinates see it in ERP, in Outlook, and in AI reminders.
  - KPI impact ties non-completion to that cost center / branch.

- AI becomes the “operations assistant”:

  - “This is what matters in the next hour.”
  - “This will damage KPI if you ignore it.”
  - “Do you want me to escalate or snooze?”

---

This is the final implementation plan for the additional features:

- Unified Task/To-Do module
- Calendar push
- Email awareness
- Notification bell + Notification Center
- AI nudging
- RBAC + SoD integration
- KPI and audit linkage

This fits cleanly into Phase 7 rollout because Phase 7 is where we train real users and enforce accountability. After Phase 7, going into Phase 8 pilot, managers will already be used to:

- checking their homepage,
- watching the bell,
- clearing notifications,
- acting on assigned tasks,
- and responding to AI nudges.

That’s exactly the behavior we want before pilot go-live.
