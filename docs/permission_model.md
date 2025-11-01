Break it into:

1. Architecture overview
2. Backend (Django) design
3. Permission resolution & runtime checks
4. Frontend behavior (React/Vue/HTMX style)
5. Admin UI (how to manage roles, scopes, users)
6. Developer workflow (how to add new permissions)
7. Audit, SoD, and AI interaction
8. Rollout/staging plan

Let’s go.

---

## 1. Architecture Overview

**Goal:** One permission system that:

- is declared in code (no manual DB inserts),
- supports scopes (company, cost center, branch, grant, project, HR),
- can be assigned to roles, groups, or directly to users,
- is enforced by backend APIs,
- is respected by frontend (hide/disable),
- is manageable by admin through UI.

**Core idea:**
**Code declares → system auto-registers → admin assigns → backend enforces → frontend reacts.**

---

## 2. Backend (Django) Design

### 2.1 Models

Create a `security` (or `access_control`) app.

**a) `SecPermission`**

- `id`
- `code` (unique, e.g. `procurement_create_pr`)
- `description`
- `category` (finance, procurement, microfinance, ngo, hr, system…)
- `scope_required` (bool)
- `is_sensitive` (bool)
- `is_assignable` (bool, default True)
- timestamps

**b) `SecRole`**

- `id`
- `name` (“Procurement Officer”, “MF Branch Manager”)
- `code` (for seeding, e.g. `r_procurement_officer`)
- `description`
- `is_system` (bool)
- `tenant_cluster_id`

**c) `SecRolePermission`**

- FK `role` → `SecRole`
- FK `permission` → `SecPermission`
- optional: `amount_limit`, `percent_limit`, `conditions` (JSON) — for approval-type perms

**d) `SecScope`**
Generic scope row.

- `id`
- `scope_type` (company / cost_center / branch / plant / grant / project / hr_group / sla_queue)
- `object_id` (id of actual company/cost center/branch…)
- `name`
- `tenant_cluster_id`

**e) `SecUserRole` (a.k.a. `SecUserRoleAssignment`)**

- `id`
- FK `user`
- FK `role`
- timestamps
- `valid_from`, `valid_to`
- `is_delegated`
- `delegated_by_user_id`

**f) `SecUserRoleScope`**

- FK `user_role`
- FK `scope`

This is how we say: _this user has this role in these scopes._

**g) `SecSoDRule`**

- `name`
- `first_action_code`
- `second_action_code`
- `enforcement` (`block`/`warn`)
- optional: `scope_type`

**h) (optional) `SecUserDirectPermission`**
For one-off overrides:

- FK `user`
- FK `permission`
- FK `scope` (nullable)
- `valid_from`, `valid_to`

---

### 2.2 Permission Registry (auto creation)

- Global file: `security/permission_registry.py`
- Each app has `permissions.py` and calls `register_permissions()` in `apps.py`.
- Management command `python manage.py sync_permissions` writes them to DB.

This solves “how will system identify permissions while I am developing?”.

---

### 2.3 Runtime Services

Create `security/services/permission_service.py` with:

1. `get_user_effective_permissions(user) -> dict[perm_code -> set(scope_ids)]`

   - load all user roles
   - for each role load role permissions
   - for each role load role scopes
   - build a map:

     ```python
     {
       "create_loan_account": {scope1, scope2},
       "approve_loan_disbursement": {branch3},
       "procurement_create_pr": {"*"}  # if no scope required / global
     }
     ```

2. `user_has_permission(user, perm_code, record_scope=None) -> bool`

   - if `user.is_superuser`: True
   - fetch perm map from cache
   - if perm not present: False
   - if perm doesn’t need scope: True
   - if perm needs scope: check intersection between user’s scopes for that perm and `record_scope`
   - check SoD rules (see below)

3. `resolve_record_scope(record)` (or `resolve_scope_from_request(request, **kwargs)`)

   - looks at model fields: `company_id`, `cost_center_id`, `branch_id`, `grant_id`, etc.
   - returns list of `SecScope` IDs

4. `check_sod(user, perm_code, record) -> (ok, reason)`

---

### 2.4 Middleware

Add a middleware that, for authenticated user:

- loads (or lazy-loads) `effective_permissions` into `request.user._perm_ctx`
- OR stores a token to fetch later
- sets current tenant_cluster

This avoids re-computing for each view.

---

### 2.5 Decorators / DRF Permissions

For classic Django views:

```python
from security.decorators import require_permission

@require_permission("procurement_create_pr")
def create_pr(request):
    ...
```

For DRF:

```python
from rest_framework.permissions import BasePermission
from security.services import user_has_permission, resolve_record_scope

class HasERPPermission(BasePermission):
    def __init__(self, perm_code):
        self.perm_code = perm_code

    def has_permission(self, request, view):
        # for list/create
        return user_has_permission(request.user, self.perm_code)

    def has_object_permission(self, request, view, obj):
        # for retrieve/update
        scope = resolve_record_scope(obj)
        return user_has_permission(request.user, self.perm_code, scope)
```

Then:

```python
class POViewSet(ModelViewSet):
    permission_classes = [HasERPPermission("procurement_view_po")]
```

---

### 2.6 Query Filtering

For list endpoints, we must auto-filter by scope.

Option 1: per-view mixin

```python
class ScopedQuerysetMixin:
    scope_map = {"company_id": "company", "cost_center_id": "cost_center"}

    def get_queryset(self):
        qs = super().get_queryset()
        return filter_queryset_by_user_scopes(qs, self.request.user, self.scope_map)
```

This prevents “I can see other company’s POs”.

---

### 2.7 SoD (Segregation of Duties)

In `user_has_permission`:

1. Find SoD rules where `second_action_code == perm_code`
2. For each rule: check whether this same user already did `first_action_code` on this record (we must store audit per record)
3. If yes:

   - if rule.enforcement == "block": return False
   - if "warn": allow but log / return flag to UI

We need audit tables to know who did what (you already planned audit).

---

## 3. Frontend Behavior

Let’s assume React, but same idea in Vue.

### 3.1 Fetch permissions after login

When user logs in, call:

`GET /api/me/permissions/`

Backend returns:

```json
{
	"user": {
		"id": 7,
		"name": "Safa",
		"tenant_cluster_id": 1
	},
	"permissions": [
		{
			"code": "procurement_create_pr",
			"scopes": ["company:1", "cost_center:210"]
		},
		{
			"code": "approve_loan_disbursement",
			"scopes": ["branch:3"]
		},
		{
			"code": "inventory_view_stock",
			"scopes": ["company:1"]
		}
	]
}
```

Store this in a **PermissionContext** (React context) or Pinia/Vuex.

### 3.2 Component-level guards

Create a small helper:

```javascript
function useCan(permCode, scope = null) {
	const { permissions } = usePermissionContext();
	// if super: return true
	const perm = permissions.find((p) => p.code === permCode);
	if (!perm) return false;
	if (!scope) return true;
	return perm.scopes.includes(scope) || perm.scopes.includes("*");
}
```

Then in components:

```jsx
{
	useCan("procurement_create_pr") && (
		<Button onClick={openPRForm}>New Purchase Requisition</Button>
	);
}
```

This hides UI for unauthorized users.

### 3.3 Route guards

When defining routes:

```jsx
<Route
	path="/procurement/pr"
	element={
		<RequirePermission code="procurement_view_pr">
			<PRList />
		</RequirePermission>
	}
/>
```

`RequirePermission` checks context, if fail → show 403 page.

### 3.4 Action-level disable

Sometimes you want to **show** but **disable**:

- show PO line, but disable “Approve” button with tooltip “You don’t have approve permission in this company/cost center.”
- particularly useful for training Phase 7

```jsx
<Button
	disabled={!useCan("procurement_approve_po", currentScope)}
	title={
		!useCan("procurement_approve_po", currentScope)
			? "No approval permission"
			: ""
	}
>
	Approve
</Button>
```

### 3.5 Notifications & Task panel

When bell shows a notification, and user clicks:

- Frontend calls API of that target entity
- If backend returns 403 (permission removed), show “You no longer have access to this item.”

So **frontend hides**, **backend enforces**.

---

## 4. Admin UI (Backoffice)

We need 5 admin screens.

### 4.1 Permissions Catalog

**Purpose:** see all permissions auto-created by modules.

List view:

- Filters: by module/category, by text
- Columns: Code | Description | Category | Scope required | Sensitive
- Row action: “Mark unassignable” (for internal perms)
- Read-only for normal admins

### 4.2 Roles

List:

- Role name
- Description
- # of permissions
- # of users
- Industry pack tag (`manufacturing`, `ngo`, `microfinance`)

Detail/edit:

- Left panel: role info
- Middle: list of permissions (with category sections)
- Right: rule config (amount limit for approve perms)

Buttons:

- “Add permission”
- “Remove permission”
- “Clone role” (to create a variant)

### 4.3 Scopes

Tree/table showing:

- Tenant

  - Company

    - Cost centers
    - Plants
    - Branches
    - Grants / Programs

Admin can create scopes here (if dynamic). But in many cases, scopes will be auto-created from master data (company created → scope row created).

### 4.4 Users & Assignments

User detail page:

- Basic info
- **Effective roles** (with scope chips)

  - e.g. “Procurement Officer (Company:1, CC:210)”
  - e.g. “MF Branch Manager (Branch:3)”

- **Direct permissions** (if any)
- **Delegations** (active, future)
- Buttons:

  - “Assign new role” → opens modal:

    - select role
    - select scopes (multi)
    - set validity (from, to)

  - “Add direct permission” → only for emergencies

Also we add a “Simulate” button:

- “Show what this user can do” → calls backend to compute effective perms & scopes, shows nicely.

### 4.5 SoD Rules

Table:

- Name
- Action A
- Action B
- Enforcement (block/warn)
- Active? yes/no

Admin can add:

- “If user creates AP bill → cannot approve same AP bill”
- “If user raises out-of-budget → cannot approve that out-of-budget”
- “If user creates PO → cannot GRN it”

---

## 5. How Admin Will Manage This (Flow)

1. **System boot / development time**

   - You run `python manage.py sync_permissions`
   - All perms appear in “Permissions Catalog”

2. **Admin creates roles**

   - “Microfinance Branch Officer”
   - “Microfinance Approver”
   - “NGO Finance”
   - “Plant Store Keeper”
   - “Procurement Manager”

   and attaches relevant permissions.

3. **Admin defines scopes**

   - Company A
   - Company B
   - Cost center 210
   - Branch Sylhet
   - Grant “GB-2025-Edu”
     (or they get auto-created from master)

4. **Admin assigns roles to users WITH scopes**

   - User: Rafiq → Role: Microfinance Branch Officer → Scope: Branch Sylhet
   - User: Arif → Role: Procurement Manager → Scope: Company A

5. **Admin tests**

   - Uses the simulator screen to see what Arif can do
   - If OK → save

6. **User logs in**

   - Frontend fetches `/api/me/permissions/`
   - Hides buttons, protects routes
   - Backend still checks on every sensitive action

---

## 6. Developer Workflow

While developing new modules:

1. Add new permission defs in `app/permissions.py`:

   ```python
   PERMISSIONS = [
       {"code": "production_create_work_order", "description": "...", "category": "production", "scope_required": True},
   ]
   ```

2. Import in `apps.py` → `register_permissions(PERMISSIONS)`

3. Run `python manage.py sync_permissions`

4. Use it in view:

   ```python
   @require_permission("production_create_work_order")
   def create_wo(...):
       ...
   ```

5. For now, develop as superuser → bypass

6. Later, admin can see it and add to roles.

This is repeatable, low friction.

---

## 7. Audit, SoD, AI

### 7.1 Audit

Every “sensitive” permission (where `is_sensitive=True`) → log to `AuditLog`:

- user
- action (perm_code)
- target (model, id)
- scopes
- source (web / api / ai)
- timestamp

### 7.2 SoD

When user calls an approve endpoint:

- service checks SoD
- if conflict:

  - return 403 with message `"You were involved earlier in this transaction; approval blocked by policy."`
  - log to AuditLog

### 7.3 AI

When AI asks: “Show overdue CAPA for Plant B”:

- AI handler calls same permission resolver
- if user has `view_capa` in Plant B → return data
- else → return generic: “You don’t have access to CAPA for Plant B.”

When AI tries to act (“approve this PO”):

- call normal approve endpoint
- it runs through `user_has_permission` + SoD
- store `via_ai: true` in audit

So AI never bypasses.

---

## 8. Rollout / Staging Plan

1. **Phase A (dev)**

   - Build models
   - Build permission registry
   - Build `sync_permissions`
   - Add decorators to a few views (procurement, microfinance)
   - Return `/api/me/permissions/`
   - Frontend hides buttons

2. **Phase B (admin)**

   - Build Permissions Catalog page
   - Build Roles page (create, edit, attach perms)
   - Build User Assignments page (assign role + scope)
   - Build Scope view

3. **Phase C (enforcement)**

   - Turn on actual backend checks (no more “superuser always true” except for real superuser)
   - Add query scoping to list APIs
   - Add SoD checks

4. **Phase D (polish)**

   - Add “simulate user” screen
   - Add “why access denied?” message
   - Add export of role→perm matrix

---

## Final recap

- **Backend**: Django models for permission, role, scope, user-role-scope, SoD; service to resolve effective permissions; decorators/DRF permissions; query scoping; auto-registration from code.
- **Frontend**: fetch current user’s permissions once → store in context → hide/disable UI → protect routes → recheck on click.
- **Admin**: see all auto-created permissions, create/edit roles, assign roles to users with scopes, define SoD rules, simulate user.
- **Dev**: just declare permissions in module → run sync → use decorator.

That’s the complete implementation plan.
