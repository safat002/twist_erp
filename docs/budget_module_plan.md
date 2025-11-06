Budget Module Workflow Enhancement Plan

     Summary

     Transform the budget module from simple status tracking to a full approval workflow system with:
     - Company-wide budget periods created by module owners
     - Separate entry period (when users add lines) vs active period (when budget tracks expenses)
     - Cost center-wise budget entry by authorized users
     - Two-level approval: Cost Center Owner → Budget Module Owner
     - Comprehensive notification system at each stage

     ---
     PHASE 1: BACKEND CHANGES

     1.1 Model Enhancements (backend/apps/budgeting/models.py)

     Budget Model - Add New Fields:
     # Entry period fields (when users can add/edit lines)
     entry_start_date = DateField()
     entry_end_date = DateField()

     # Active period fields (when budget is in use/tracking expenses)
     budget_active_date = DateField()
     budget_expire_date = DateField()

     # New status values - replace existing STATUS_CHOICES:
     # DRAFT → ENTRY_OPEN → PENDING_CC_APPROVAL → CC_APPROVED →
     # PENDING_FINAL_APPROVAL → APPROVED → ACTIVE → EXPIRED → CLOSED

     New BudgetApproval Model:
     class BudgetApproval(models.Model):
         budget = ForeignKey(Budget, CASCADE, related_name='approvals')
         approver_type = CharField(choices=[
             ('cost_center_owner', 'Cost Center Owner'),
             ('budget_module_owner', 'Budget Module Owner')
         ])
         cost_center = ForeignKey(CostCenter, null=True)  # Which CC for CC owner approvals
         approver = ForeignKey(User)
         status = CharField(choices=[
             ('pending', 'Pending'),
             ('approved', 'Approved'),
             ('rejected', 'Rejected'),
             ('sent_back', 'Sent Back for Review')
         ])
         decision_date = DateTimeField(auto_now_add=True)
         comments = TextField()
         modifications_made = JSONField(default=dict)  # Track CC owner changes

     Add CostCenter Field:
     # Add to CostCenter model
     budget_entry_users = ManyToManyField(User, related_name='budget_entry_cost_centers')

     Budget Model - New Methods:
     def is_entry_period_active(self):
         """Check if current date is within entry period"""

     def can_user_enter_budget(self, user, cost_center):
         """Check if user can enter budget for specific cost center"""

     def submit_for_approval(self, user):
         """Submit budget for cost center owner approvals"""

     def get_pending_cost_center_approvals(self):
         """Get list of cost centers pending approval"""

     1.2 Services Layer (backend/apps/budgeting/services.py - NEW FILE)

     BudgetNotificationService Class:
     def notify_budget_created(budget)
     def notify_entry_period_started(budget)
     def notify_entry_period_ending(budget, days_remaining)
     def notify_entry_period_ended(budget)
     def notify_approval_requested(budget, cost_center, approver)
     def notify_approval_decision(budget, cost_center, status, comments)
     def notify_budget_active(budget)

     BudgetApprovalService Class:
     def request_cost_center_approvals(budget)
     def approve_by_cost_center_owner(budget, cost_center, user, comments, modifications)
     def reject_by_cost_center_owner(budget, cost_center, user, comments)
     def request_final_approval(budget)
     def approve_by_module_owner(budget, user, comments)
     def reject_by_module_owner(budget, user, comments)
     def send_back_to_cost_center(budget, cost_center, user, comments)

     BudgetPermissionService Class:
     def user_can_create_budget(user, company)
     def user_can_enter_for_cost_center(user, cost_center)
     def user_is_cost_center_owner(user, cost_center)
     def user_is_budget_module_owner(user, company)

     1.3 Serializers Update (backend/apps/budgeting/serializers.py)

     Add to BudgetSerializer:
     entry_start_date = DateField()
     entry_end_date = DateField()
     budget_active_date = DateField()
     budget_expire_date = DateField()
     is_entry_period_active = SerializerMethodField()
     pending_approvals = SerializerMethodField()  # List of pending CC approvals
     user_can_enter = SerializerMethodField()  # Can current user enter budget

     New BudgetApprovalSerializer:
     class BudgetApprovalSerializer(serializers.ModelSerializer):
         approver_name = SerializerMethodField()
         cost_center_name = SerializerMethodField()
         class Meta:
             model = BudgetApproval
             fields = '__all__'

     1.4 ViewSet Updates (backend/apps/budgeting/views.py)

     BudgetViewSet - New Custom Actions:
     @action(methods=['POST'], detail=True)
     def submit_for_approval(self, request, pk=None):
         """Submit budget for cost center owner approvals"""

     @action(methods=['POST'], detail=True)
     def approve_cost_center(self, request, pk=None):
         """Cost center owner approves (with optional modifications)"""
         # Body: {cost_center_id, comments, modifications}

     @action(methods=['POST'], detail=True)
     def reject_cost_center(self, request, pk=None):
         """Cost center owner rejects"""
         # Body: {cost_center_id, comments}

     @action(methods=['POST'], detail=True)
     def approve_final(self, request, pk=None):
         """Budget module owner final approval"""
         # Body: {comments}

     @action(methods=['POST'], detail=True)
     def reject_final(self, request, pk=None):
         """Budget module owner rejects"""
         # Body: {comments}

     @action(methods=['POST'], detail=True)
     def send_back_for_review(self, request, pk=None):
         """Budget owner sends back to specific cost center owner"""
         # Body: {cost_center_id, comments}

     @action(methods=['GET'], detail=True)
     def approval_history(self, request, pk=None):
         """Get approval history for budget"""

     BudgetLineViewSet - Update create/update:
     def create(self, request, *args, **kwargs):
         # Check if entry period is active
         # Check if user has permission for cost_center
         # Check if budget status allows entry (ENTRY_OPEN)

     New BudgetApprovalQueueView:
     class BudgetApprovalQueueView(APIView):
         """Get pending approvals for current user"""
         # Returns budgets pending user's approval as CC owner or module owner

     1.5 Permissions Enhancement (backend/apps/budgeting/permissions.py)

     Add New Permissions:
     'budgeting_entry_budget': 'Can enter budget lines'
     'budgeting_approve_cost_center_budget': 'Can approve as cost center owner'
     'budgeting_approve_final_budget': 'Can approve as budget module owner'

     Custom Permission Classes:
     class CanEnterBudgetLine(BasePermission):
         """Check if user can enter budget for specific cost center"""

     class IsCostCenterOwner(BasePermission):
         """Check if user is owner/deputy of cost center"""

     class IsBudgetModuleOwner(BasePermission):
         """Check if user has budgeting_approve_final_budget permission"""

     1.6 Signals (backend/apps/budgeting/signals.py)

     Add Signal Handlers:
     @receiver(post_save, sender=Budget)
     def on_budget_created(sender, instance, created, **kwargs):
         """Send notification to all cost center owners"""

     @receiver(post_save, sender=Budget)
     def on_budget_status_changed(sender, instance, **kwargs):
         """Send notifications on status transitions"""

     # Scheduled task (using Celery or management command)
     @periodic_task(run_every=crontab(hour=0, minute=0))
     def check_entry_period_notifications():
         """Daily check for entry period start/end notifications"""

     1.7 Management Commands (backend/apps/budgeting/management/commands/)

     New Command: send_entry_period_notifications.py
     # Run daily via cron
     # Check for entry periods starting today → notify
     # Check for entry periods ending in 3 days → notify
     # Check for entry periods ended yesterday → notify

     1.8 URL Updates (backend/apps/budgeting/urls.py)

     Add to router:
     # New actions will auto-register via @action decorator
     # Add new view:
     path('approval-queue/', BudgetApprovalQueueView.as_view())

     1.9 Migration

     Create migration:
     python manage.py makemigrations budgeting
     # Will create migration for:
     # - Budget new fields
     # - BudgetApproval model
     # - CostCenter.budget_entry_users
     python manage.py migrate

     ---
     PHASE 2: FRONTEND CHANGES

     2.1 Budget Creation Form (frontend/src/pages/Budgeting/BudgetingWorkspace.jsx)

     Update Budget Modal:
     // Add new form fields:
     - Entry Period Start Date (DatePicker)
     - Entry Period End Date (DatePicker)
     - Budget Active Date (DatePicker)
     - Budget Expire Date (DatePicker)
     - Budget Type selector (CAPEX, OPEX, REVENUE, etc.)

     // Add validation:
     - entry_end_date > entry_start_date
     - budget_expire_date > budget_active_date
     - budget_active_date >= entry_start_date

     // Add help text:
     "This budget will be created for ALL cost centers in your company.
     Cost center owners will be able to enter budget lines during the entry period."

     2.2 Budget Entry Dashboard (frontend/src/pages/Budgeting/BudgetEntry.jsx - NEW COMPONENT)

     Create New Component:
     // Features:
     - Show available budgets with ENTRY_OPEN status
     - Filter by cost centers user has access to
     - Entry period countdown timer
     - Budget line entry form
     - Real-time validation against user's cost center access
     - Disabled state if outside entry period

     2.3 Approval Queue (frontend/src/pages/Budgeting/ApprovalQueue.jsx - NEW COMPONENT)

     Create New Component:
     // Two tabs:
     1. "As Cost Center Owner" - budgets pending user's approval
     2. "As Budget Module Owner" - budgets pending final approval

     // Features:
     - List pending budgets
     - Click to view budget details + lines
     - Approve/Reject/Modify actions
     - Comment field required for reject
     - Modification form for CC owner (edit lines + approve in one step)
     - Send back to CC owner (for module owner)

     2.4 Budget Detail View Enhancement

     Add to BudgetingWorkspace.jsx:
     // Add sections:
     - Entry Period Status badge (Active/Upcoming/Closed)
     - Active Period Status badge
     - Approval Timeline (visual stepper):
       * Created → Entry Period → CC Approvals → Final Approval → Active

     // Add approval history table:
     - Show all approval actions
     - Who approved/rejected
     - Comments
     - Modifications made

     2.5 Notification Integration (frontend/src/components/Notifications/)

     Update Notification Center:
     // Add budget notification types:
     - 'budget.created'
     - 'budget.entry_period_started'
     - 'budget.entry_period_ending'
     - 'budget.entry_period_ended'
     - 'budget.approval_requested'
     - 'budget.approved'
     - 'budget.rejected'
     - 'budget.sent_back'

     // Add action buttons in notifications:
     - "View Budget" → Navigate to budget detail
     - "Approve Now" → Open approval modal

     2.6 API Service Updates (frontend/src/services/budget.js)

     Add New Functions:
     export const submitBudgetForApproval = (budgetId) => { ... }
     export const approveCostCenterBudget = (budgetId, payload) => { ... }
     export const rejectCostCenterBudget = (budgetId, payload) => { ... }
     export const approveFinalBudget = (budgetId, payload) => { ... }
     export const rejectFinalBudget = (budgetId, payload) => { ... }
     export const sendBackForReview = (budgetId, payload) => { ... }
     export const fetchApprovalQueue = () => { ... }
     export const fetchApprovalHistory = (budgetId) => { ... }

     2.7 Navigation Updates (frontend/src/layouts/MainLayout.jsx)

     Add Menu Items:
     // Under Budgeting module:
     - "Budget Entry" (show badge if active entry periods exist)
     - "Approval Queue" (show badge count of pending approvals)

     ---
     PHASE 3: NOTIFICATION IMPLEMENTATION DETAILS

     3.1 Notification Timing

     Budget Created:
     - Trigger: Immediately after budget save (status=DRAFT)
     - Recipients: All cost center owners in company
     - Message: "New {budget_type} budget for {period} has been declared. Entry period: {entry_start} to
     {entry_end}"

     Entry Period Started:
     - Trigger: Daily cron job, check budgets where entry_start_date == today
     - Recipients: All users with budget_entry permission for any cost center
     - Message: "Budget entry period for {budget_name} is now open. You can enter budget lines until
     {entry_end_date}"

     Entry Period Ending Soon:
     - Trigger: Daily cron job, check budgets where entry_end_date - today == 3 days
     - Recipients: Users who haven't submitted budget lines yet
     - Message: "Reminder: Budget entry for {budget_name} ends in 3 days ({entry_end_date})"

     Entry Period Ended:
     - Trigger: Daily cron job, check budgets where entry_end_date == yesterday
     - Recipients: All cost center owners
     - Message: "Budget entry period for {budget_name} has ended. Please review and approve your cost center's
     budget"

     Approval Requested (Cost Center):
     - Trigger: When budget status changes to PENDING_CC_APPROVAL
     - Recipients: Each cost center owner (one notification per CC)
     - Message: "Budget {budget_name} requires your approval for {cost_center_name}. {line_count} budget lines
     submitted"

     Approved by Cost Center Owner:
     - Trigger: When CC owner approves
     - Recipients: Budget creator, Budget module owners
     - Message: "{cost_center_name} budget approved by {approver_name}. {comments}"

     Rejected by Cost Center Owner:
     - Trigger: When CC owner rejects
     - Recipients: Budget creator
     - Message: "{cost_center_name} budget rejected by {approver_name}. Reason: {comments}"

     Final Approval Requested:
     - Trigger: When all CC owners have approved
     - Recipients: Budget module owners
     - Message: "Budget {budget_name} ready for final approval. All cost centers have approved"

     Final Approval:
     - Trigger: When module owner approves
     - Recipients: All cost center owners, budget creator
     - Message: "Budget {budget_name} has been approved and is now active"

     Final Rejection:
     - Trigger: When module owner rejects
     - Recipients: Budget creator, all CC owners
     - Message: "Budget {budget_name} rejected by {approver_name}. Reason: {comments}"

     Sent Back for Review:
     - Trigger: When module owner sends back
     - Recipients: Specific cost center owner
     - Message: "Budget {budget_name} sent back for review of {cost_center_name}. Comments: {comments}"

     ---
     PHASE 4: TESTING CHECKLIST

     Backend Tests:

     - Budget creation with all new fields
     - Entry period validation
     - Cost center permission checking
     - Approval workflow transitions
     - Notification generation
     - Edge cases (expired entry period, unauthorized users)

     Frontend Tests:

     - Budget creation form validation
     - Entry period UI states
     - Approval queue display
     - Notification display and actions
     - Permission-based UI hiding

     Integration Tests:

     - Complete workflow: Create → Entry → CC Approval → Final Approval → Active
     - Rejection flow
     - Modification by CC owner
     - Send back flow

     ---
     IMPLEMENTATION ORDER

     1. Backend Foundation (Days 1-2)
       - Models + Migration
       - Services layer
     2. Backend API (Days 3-4)
       - Serializers
       - ViewSet actions
       - Permissions
     3. Notifications (Day 5)
       - Signal handlers
       - Management command
     4. Frontend Core (Days 6-7)
       - Budget creation form
       - Entry dashboard
     5. Frontend Approval (Days 8-9)
       - Approval queue
       - Approval actions
     6. Notifications UI (Day 10)
       - Notification integration
       - Real-time updates
     7. Testing & Refinement (Days 11-12)
       - End-to-end testing
       - Bug fixes
       - UI polish

     ---
     FILES TO MODIFY/CREATE

     Backend:

     - MODIFY: backend/apps/budgeting/models.py
     - MODIFY: backend/apps/budgeting/serializers.py
     - MODIFY: backend/apps/budgeting/views.py
     - MODIFY: backend/apps/budgeting/permissions.py
     - MODIFY: backend/apps/budgeting/signals.py
     - MODIFY: backend/apps/budgeting/urls.py
     - CREATE: backend/apps/budgeting/services.py
     - CREATE: backend/apps/budgeting/management/commands/send_entry_period_notifications.py
     - CREATE: Migration file (auto-generated)

     Frontend:

     - MODIFY: frontend/src/pages/Budgeting/BudgetingWorkspace.jsx
     - MODIFY: frontend/src/services/budget.js
     - MODIFY: frontend/src/layouts/MainLayout.jsx
     - CREATE: frontend/src/pages/Budgeting/BudgetEntry.jsx
     - CREATE: frontend/src/pages/Budgeting/ApprovalQueue.jsx
     - CREATE: frontend/src/components/Budgeting/ApprovalTimeline.jsx
     - CREATE: frontend/src/components/Budgeting/EntryPeriodStatus.jsx

     ---
     ESTIMATED EFFORT

     - Backend: 5-6 days
     - Frontend: 4-5 days
     - Testing: 2-3 days
     - Total: 12-15 working days

● Perfect! The plan is approved. Let me create a comprehensive todo list to track our progress through this
implementation.

● Excellent! Todo list created with 23 tasks. Now let's start implementing. I'll begin with Phase 1: Backend Models.

● Read(backend\apps\budgeting\models.py)
⎿  Read 100 lines

● Let me continue reading the Budget model to see its complete structure:

● Read(backend\apps\budgeting\models.py)
⎿  Read 100 lines

● Perfect! Now I understand the structure. Let me start implementing the changes. I'll first update the CostCenter
and Budget models, then create the new BudgetApproval model.

● Update(backend\apps\budgeting\models.py)
⎿  Updated backend\apps\budgeting\models.py with 1 addition
28 cost_center_type = models.CharField(max_length=32, choices=CostCenterType.choices,
default=CostCenterType.DEPARTMENT)
29 owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
related_name='primary_cost_centers')
30 deputy_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
related_name='backup_cost_centers')
31 + budget_entry_users = models.ManyToManyField(User, blank=True, + related_name='budget_entry_cost_centers', help_text="Users who can enter budget lines for this cost + center")
32 default_currency = models.CharField(max_length=3, default='USD')
33 description = models.TextField(blank=True)
34 is_active = models.BooleanField(default=True)

> also make sure budget will be based on item code, only revenue budget will be based on product

Todos
☐ PHASE 1: Backend Models - Add new fields to Budget model (entry dates, active dates)
☐ PHASE 1: Backend Models - Create BudgetApproval model for tracking approvals
☐ PHASE 1: Backend Models - Add budget_entry_users field to CostCenter model
☐ PHASE 1: Backend Models - Add helper methods to Budget model
☐ PHASE 1: Create services.py - Implement BudgetNotificationService
☐ PHASE 1: Create services.py - Implement BudgetApprovalService
☐ PHASE 1: Create services.py - Implement BudgetPermissionService
☐ PHASE 1: Update serializers.py - Add new fields to BudgetSerializer
☐ PHASE 1: Update serializers.py - Create BudgetApprovalSerializer
☐ PHASE 1: Update views.py - Add approval action endpoints to BudgetViewSet
☐ PHASE 1: Update views.py - Create BudgetApprovalQueueView
☐ PHASE 1: Update views.py - Add entry period validation to BudgetLineViewSet
☐ PHASE 1: Update permissions.py - Add new budget permissions
☐ PHASE 1: Update signals.py - Add notification signal handlers
☐ PHASE 1: Create management command - send_entry_period_notifications.py
☐ PHASE 1: Create and run database migration
☐ PHASE 2: Frontend - Update budget creation form with new date fields
☐ PHASE 2: Frontend - Create BudgetEntry.jsx component
☐ PHASE 2: Frontend - Create ApprovalQueue.jsx component
☐ PHASE 2: Frontend - Create ApprovalTimeline.jsx component
☐ PHASE 2: Frontend - Update budget.js API service with approval endpoints
☐ PHASE 2: Frontend - Integrate notifications for budget workflow
☐ PHASE 3: Testing - Test complete budget workflow end-to-end

Now lets finalize budget entry page. this is for the user for entering their budgets item wise. add some cards:
Budget items no., Budget value, used value remaining value, the information will show as per user's cost center. if
user have multiple cost-center cards will add the values of those cost centers. there will be a add budget items
button, upon click on it a pop-up window will appear

Now lets finalize budget entry page. this is for the user for entering their budgets item wise. add some cards:
Budget items no., Budget value, used value remaining value, the information will show as per user's cost center. if
user have multiple cost-center cards will add the values of those cost centers. there will be a add budget items
button, upon click on it a pop-up window will appear in which user will select cost-center from dropdown, only the
permitted cost center will show here, select budget from the declared budget, and put item quantity for budget,
system will collect value of items from the last PO of the item, and show value by multiplying with budget quantity.
user can save this budget which will show as draft, after completing all budget items user will submit the budget,
cost center wise budget will be created here. upon submit budget will go to the respective cost center owner and cost center owner can modify submitted budget and approve or reject. after approval of cost center owner budget will go to the budget module owner for final approval. after approval of budget module owner budget will be ready for use. in each case proper notification will be required.
