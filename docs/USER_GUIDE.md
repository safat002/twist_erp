# Twist ERP - Comprehensive User Guide (v3)

This document serves as the official user guide for the Twist ERP platform. It details the purpose, usage, and cross-functional impact of each module.

---

## Backend User Guide

### 1. Introduction & Philosophy

The Twist ERP backend is a modular, multi-tenant, and AI-assisted "business operating system." Its core philosophy is to provide a flexible foundation that can be visually configured to adapt to various industries without developer intervention.

- **Multi-Company Core:** Supports multiple companies within a group, allowing for data isolation, inter-company transactions, and financial consolidation.
- **Metadata-Driven:** All elements (entities, fields, workflows, forms) are defined as metadata, allowing administrators to extend the ERP's data model and processes in real-time.
- **API-First & Event-Driven:** Modules communicate via a shared event bus and expose services through APIs, ensuring loose coupling and scalability.
- **Embedded Intelligence:** An AI layer provides contextual insights, proactive alerts, and operational assistance.
- **Secure & Auditable:** Every action is governed by a granular Role-Based Access Control (RBAC) system and recorded in an immutable audit trail.

### 2. Core Platform Modules

These modules provide common services to all business functions.

#### a. Intelligent Data Migration Engine
- **Purpose:** To enable non-technical users to import legacy data (e.g., from Excel) into the ERP.
- **Key Functions & Usage:**
    1.  **Upload:** A user uploads a file (e.g., customer list) and selects the target company and entity type (e.g., "Customer Master").
    2.  **Map Fields:** The system profiles the file and auto-suggests mappings between the file's columns and the ERP's fields. If a column like "Customer_Loyalty_Tier" doesn't exist in the ERP, the engine suggests creating it as a new custom field.
    3.  **Validate:** The engine validates the data for errors (e.g., missing names, invalid email formats, duplicate entries) and presents a list of valid and invalid rows.
    4.  **Approve & Commit:** A manager reviews the validation summary and potential schema changes, then approves the job. The system then transactionally commits the valid data to the live database.
- **Cross-Module Integration & Business Impact:**
    - **Impact on All Modules:** This engine is the primary tool for populating master data (Customers, Suppliers, Items) and opening balances (Stock, AR, AP) for all other modules, forming the foundation for go-live.
    - **Impact on Metadata:** By allowing the creation of custom fields during import, it directly extends the data model for modules like Sales (new customer fields) or Inventory (new item attributes), which are then immediately available in the Form Builder and Reporting engine.

#### b. Workflow & Automation Engine
- **Purpose:** To automate and enforce business processes.
- **Key Functions & Usage:**
    1.  **Design Workflow:** An admin uses the visual Workflow Studio to draw a process flow, such as for purchase approvals.
    2.  **Define Rules:** They add conditional nodes (e.g., `IF amount > $5,000`) and action nodes (e.g., `ROUTE to CFO for approval`).
    3.  **Execution:** When a user submits a transaction (like a Purchase Requisition), the engine intercepts it, evaluates the rules, and routes it to the correct approver's task list.
- **Cross-Module Integration & Business Impact:**
    - **Impact on All Transactional Modules:** This engine is the gatekeeper for critical processes in Procurement, Sales, Finance, and HR. It ensures that company policies (like spending limits) are enforced automatically, reducing manual oversight and improving compliance.
    - **Impact on Tasks & Notifications:** The engine is the primary source of system-generated tasks. When an approval is required, it creates a `TaskItem` for the approver and sends a notification, directly driving user actions.

### 3. The AI Ecosystem: Your Intelligent Assistant

Think of the AI in Twist ERP not as a simple chatbot, but as a capable, context-aware assistant integrated into your daily workflow. It has a dual personality: it's a knowledgeable assistant that can answer questions and perform tasks, and a behind-the-scenes data analyst that provides insights.

#### What Your AI Can Do For You

- **Answer Complex Questions Across Departments:** You can ask questions that require pulling information from multiple modules. For example: `"Why was our profit margin lower last month?"` The AI can analyze data from Sales (discounts given), Procurement (higher material costs), and Finance (unexpected expenses) to give you a consolidated answer.

- **Perform Actions on Your Behalf:** You can give it direct commands in natural language. For instance: `"Approve the first three purchase orders on my list and notify the procurement team."` The AI will execute these actions, following all the standard approval rules as if you had clicked the buttons yourself.

- **Provide Proactive Nudges and Alerts:** The AI constantly monitors business operations. It can warn you about potential issues before they become critical. You might get a nudge like: `"Heads up, the budget for the marketing department is 85% consumed with two weeks left in the quarter."` or `"This sales order might be delayed; the required items are running low in the warehouse."`

- **Explain What You're Seeing:** If you're on a screen with unfamiliar fields, you can ask the AI, `"What does the 'GRNI Account' field mean?"` The AI can access the system's metadata and policy documents to explain the business purpose of different elements in the ERP.

- **Remember Your Preferences:** You can tell the AI how you like to work. For example: `"From now on, always show my financial reports in USD, not BDT."` The AI will save this as a long-term preference and apply it automatically in the future.

- **Guide You Through Complex Tasks:** The AI can act as a guide for multi-step processes. You can say, `"Help me migrate our supplier list from this Excel file."` The AI will then initiate the Data Migration Engine and walk you through the steps of mapping, validating, and importing the data.

#### How Your AI Works (In Simple Terms)

- **It Acts As You (And Only You):** This is the most important concept. The AI is not a global, all-seeing entity. When you interact with it, it inherits **your exact permissions**. It cannot see a report, approve a payment, or access a record unless you already have the permission to do so. Think of it as a perfectly trustworthy human assistant who uses your login to operate the system on your behalf.

- **It Has a Team of "Skills":** The AI has a modular design, with different "skills" for different business domains. It has a `FinanceSkill`, an `InventorySkill`, and a `PolicySkill`. When you ask a question, the AI Orchestrator routes it to the right expert skill (or combination of skills) to formulate the best possible answer.

- **It Has Both Short-Term and Long-Term Memory:** The AI can remember the immediate context of your conversation (e.g., the list of invoices it just showed you). It also has a long-term memory to store your explicit preferences, ensuring it becomes more personalized to your working style over time.

- **Everything is Audited:** For your protection and for compliance, every significant action the AI takes on your behalf is recorded in the main system audit trail. If the AI approves a PO for you, the log will clearly state that the action was performed by the AI based on your request.

### 4. Business Process Modules

#### a. Financial Management
- **Purpose:** To be the system of record for all financial transactions and ensure compliance.
- **Key Functions & Usage:**
    1.  **Automated Journal Posting:** Users do not create manual debit/credit entries. Instead, when an operational event occurs (e.g., a sales invoice is approved), the system automatically generates the corresponding balanced journal entries based on pre-configured posting rules.
    2.  **Manage Payables (AP):** The finance team reviews supplier bills that are automatically created from procurement, schedules them for payment, and records the payment transaction.
    3.  **Manage Receivables (AR):** The team tracks customer invoices, sends reminders for overdue payments, and records collections.
    4.  **Bank Reconciliation:** The system provides an interface to match bank statement lines with ERP transactions.
- **Cross-Module Integration & Business Impact:**
    - **Procurement → Finance:** When a supplier invoice is posted in Procurement, it creates a bill in AP, increasing the company's liabilities. When the payment is made, it reduces cash and clears the liability.
    - **Sales → Finance:** An approved customer invoice from the Sales module creates an invoice in AR, increasing revenue and accounts receivable. A customer receipt increases cash and clears the receivable.
    - **Inventory → Finance:** Every stock movement that has a cost implication (like a sale or a write-off) triggers a journal entry to update the inventory asset value and Cost of Goods Sold (COGS) on the Profit & Loss statement.
    - **Business Impact:** This module provides the ultimate view of the company's health. By consolidating data from all other modules, it produces the P&L, Balance Sheet, and Cash Flow statements that are critical for strategic decision-making.

#### b. Procurement & Supplier Management
- **Purpose:** To control company spending and manage supplier relationships.
- **Key Functions & Usage:**
    1.  **Create Purchase Requisition (PR):** A user requests to buy goods/services. This is a non-binding internal request.
    2.  **Approve PR & Create Purchase Order (PO):** The PR is routed for approval via the Workflow Engine. Once approved, it is converted into a legally binding PO sent to a supplier.
    3.  **Record Goods Receipt (GRN):** When goods arrive, the warehouse team creates a Goods Receipt Note, confirming what was received.
    4.  **Match & Post Invoice:** The finance team matches the supplier's bill to the PO and GRN (3-way match) before posting it for payment.
- **Cross-Module Integration & Business Impact:**
    - **Impact on Budgeting:** An approved PO places a **commitment** on a cost center's budget, reducing the available funds. This prevents budget overruns before they happen.
    - **Impact on Inventory:** A posted GRN immediately increases the stock quantity in the **Inventory module**, making those items available for use.
    - **Impact on Finance:** The 3-way matched supplier bill creates a liability in **Accounts Payable**, ensuring suppliers are paid on time and accurately.

#### c. Sales & Customer Relationship Management (CRM)
- **Purpose:** To manage the entire customer lifecycle from lead to cash collection.
- **Key Functions & Usage:**
    1.  **Manage Leads & Opportunities:** Salespeople track potential deals in a visual pipeline (Kanban board).
    2.  **Create Quotation & Sales Order (SO):** A quotation is sent to a customer. If accepted, it's converted into a Sales Order.
    3.  **Fulfill Order (Delivery):** The warehouse team is notified to pick, pack, and ship the items, creating a Delivery Note.
    4.  **Invoice Customer:** Based on the delivery, a customer invoice is generated and sent.
- **Cross-Module Integration & Business Impact:**
    - **Impact on Inventory:** A confirmed Sales Order can **reserve** stock. A posted Delivery Note **decreases** the stock quantity, preventing the sale of unavailable items.
    - **Impact on Finance:** A customer invoice increases **Accounts Receivable** and **Revenue**. This directly impacts the company's top-line performance and cash flow projections.
    - **Impact on Manufacturing:** If an item is not in stock, a confirmed SO can trigger a demand signal to the **Manufacturing module** to produce it.

#### d. Inventory & Warehouse Management
- **Purpose:** To maintain an accurate, real-time view of all stock.
- **Key Functions & Usage:**
    1.  **Track Stock Movements:** Every physical movement is recorded via a GRN (in), Delivery Note (out), or Stock Transfer (internal).
    2.  **Manage Stock Levels:** The system tracks on-hand quantity, reserved quantity, and available quantity per item in each warehouse.
    3.  **Perform Cycle Counts:** Users can perform periodic stock takes to ensure physical stock matches system records.
    4.  **Valuation:** The system automatically calculates the financial value of the inventory using methods like FIFO or Weighted Average.
- **Cross-Module Integration & Business Impact:**
    - **Business Impact:** Accurate inventory management is critical for business operations. It prevents stock-outs that halt sales/production and avoids over-stocking that ties up cash. The valuation directly impacts the company's balance sheet.
    - **Linkages:** This module is the physical heart of the operation, connecting the purchasing of goods (**Procurement**) with the selling (**Sales**) and production (**Manufacturing**) of goods.

#### e. Manufacturing / Production
- **Purpose:** To manage the conversion of raw materials into finished goods.
- **Key Functions & Usage:**
    1.  **Define Bill of Materials (BOM):** Users define the "recipe" for a finished product, listing all raw materials and quantities required.
    2.  **Create Work Order:** A production run is initiated via a Work Order, which consumes the BOM.
    3.  **Issue Materials:** The system generates a pick list for the warehouse to issue the required raw materials to the production floor.
    4.  **Record Production:** As finished goods are produced, they are recorded and received back into inventory.
- **Cross-Module Integration & Business Impact:**
    - **Impact on Inventory:** Work Orders **consume** raw materials (decreasing their stock) and **produce** finished goods (increasing their stock).
    - **Impact on Finance:** The cost of raw materials and labor is moved from individual expense/asset accounts into a **Work-in-Progress (WIP)** account. When production is finished, the value is moved from WIP to the **Finished Goods Inventory** asset account. This provides an accurate cost for each unit produced.

### 5. To-Be-Implemented Backend Features

The following features are on the implementation roadmap to enhance user productivity and system intelligence.

- **Unified Task & To-Do System:** A central `TaskItem` object to manage both system-assigned tasks (e.g., "Approve PO-123") and personal to-dos. These tasks can be linked to any ERP entity and will have due dates, priorities, and statuses.
- **Calendar Integration:** The system will automatically push tasks and deadlines with due dates to the user's Outlook calendar, ensuring they never miss a critical action item.
- **Email Awareness:** The ERP will monitor the user's inbox for relevant, unread emails (e.g., workflow notifications) and surface alerts within the ERP, linking directly to Outlook.
- **Enhanced Notification System:** A comprehensive notification center will provide an auditable "inbox" for all ERP events, including approvals, escalations, and AI-driven nudges, with snooze and "assign follow-up task" capabilities.

---

## Frontend User Guide

### 1. Introduction & Philosophy

The Twist ERP frontend is a visual, configurable, and context-aware interface designed to make the powerful backend accessible to non-technical users. It prioritizes clarity and ease of use through a drag-and-drop interaction model.

### 2. Key UI Concepts

#### a. Visual Builders
- **Purpose:** To allow administrators to customize the ERP without writing code.
- **Key Functions & Usage:**
    - **Form Builder:** An admin wants to add a "Region" field to the Customer screen. They open the Form Builder, drag a "Dropdown" field onto the form canvas, label it "Region," and enter the possible values (e.g., "North," "South"). After saving, the "Region" field immediately appears on the Customer form for all users.
    - **Workflow Builder:** A manager wants all POs over $10,000 to be approved by the CEO. They open the Workflow Studio, add a condition node (`IF PO.total > 10000`), and drag a line from it to an approval node assigned to the "CEO" role. The rule is now live.

#### b. AI Assistant Panel
- **Purpose:** To provide contextual help and perform actions via natural language.
- **Key Functions & Usage:**
    - A sales manager is viewing a Sales Order and asks the AI, **"Is this customer reliable?"** The AI accesses the customer's record, sees several overdue invoices in the **Finance module**, and replies, "This customer has 3 overdue invoices totaling $5,200. Proceed with caution."
    - A user types, **"Create a PO for 100 units of Item X from Supplier Y."** The AI drafts the Purchase Order by calling the **Procurement** service and presents it to the user for confirmation before submitting.

#### c. Notification Center & Taskboard
- **Purpose:** To be the user's central hub for all required actions.
- **Key Functions & Usage:**
    - A manager approves a Purchase Requisition. The **Workflow Engine** sends a notification and creates a `TaskItem` for the procurement officer.
    - The officer sees "New Task: Convert PR-056 to Purchase Order" on their Taskboard. Clicking it takes them directly to the PO creation screen with all the information from the PR pre-filled.
    - This creates a seamless, auditable chain of action, ensuring no requests are dropped and accountability is clear.
