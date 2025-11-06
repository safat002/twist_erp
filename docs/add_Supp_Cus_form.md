When you add **“Add Customer”** and **“Add Supplier”** forms in this ERP, you’re actually creating two of the most important master-data screens in the whole system — because **everything else (sales, procurement, AR, AP, BI)** depends on how clean these two are.

Here’s what you should consider, grouped so you can implement step by step.

---

## 1. Core Master Data Structure (both)

- **Unique code** (auto-generated):

  - `CUST-000123` for customers
  - `SUP-000123` for suppliers
  - Generated per company/tenant using your doc/sequence service.

- **Legal / display name** (required)
- **Short name** (for dropdowns)
- **Status**: active / inactive / blacklisted
- **Type / group**:

  - Customer type: local / export / intercompany
  - Supplier type: local / import / service / sub-contractor
  - This helps pricing, tax, LC, withholding.

---

## 2. Company / Tenant Awareness

- Every customer/supplier must be linked to **company/tenant** (your `CompanyAwareModel`).
- Decide: **shared master across group** vs **company-specific**:

  - If shared → one customer usable by multiple companies
  - If company-specific → same customer can exist multiple times with different credit/tax rules

- Form should show **“Available for companies:”** if you support cross-company customers/suppliers.

---

## 3. Identity & Compliance Fields

- VAT/TIN/Tax ID/Business ID (country dependent)
- Trade license / registration no.
- For suppliers: BIN, IRC (if import), bank details
- For customers: eTIN for invoicing (if required)
- **Validation**: if tax number duplicate → warn or block (to avoid duplicate masters).

---

## 4. Addresses & Contacts (must be structured)

Don’t just put one big text box.

- **Bill-to address**
- **Ship-to / Delivery address** (multiple)
- **Contact persons** (name, designation, email, mobile)
- **Preferred contact mode** (email / phone / ERP notification)

This is important for:

- invoices
- DO/Challan
- LC/shipment
- PO delivery

So make it a **sub-grid** in the form.

---

## 5. Finance / AR / AP Settings

**For Customer:**

- Currency (default)
- Payment term (e.g. 30 days, 45 days)
- Credit limit
- Credit hold flag (if exceeded)
- AR control account (if you allow customer-specific GL)
- Tax/VAT profile

**For Supplier:**

- Currency (default)
- Payment term
- Advance allowed? (Y/N)
- Withholding settings
- AP control account / supplier group
- Standard payment method (bank/cash/LC)

Your form should **not** make these mandatory for basic creation if you want “quick add,” but the **full form** should have them.

---

## 6. Procurement / Sales Integration

- Supplier form must support **item/category/vendor-class linkage**:

  - “This supplier supplies: Yarn, Trims, Fabric”
  - So PR/PO can suggest vendors.

- Customer form must support **sales area / price list / delivery terms**:

  - So future sales order can pick defaults.

- Add “is_internal” / “is_intercompany” for group transactions.

---

## 7. Approval & Permissions

Use your permission policy:

- `crm_create_customer`
- `crm_update_customer`
- `purchase_create_supplier`
- `purchase_update_supplier`
- (optionally) `master_approve_supplier`

**Why?** In many companies, anyone can _propose_ a supplier, but only Accounts/Procurement can **approve/activate** it.

So:

- Form saves as **Draft**
- Approval changes status to **Active**
- Transactions (PO, invoice) only allowed for **Active**

---

## 8. Duplicate Check / Data Quality

Before saving:

- Check by name (case-insensitive)
- Check by tax ID
- Check by phone/email
- If possible: show “Similar records found” and let user pick existing → avoids master-data explosion.

---

## 9. Attachments / KYC (esp. for supplier)

- Trade license
- VAT registration
- Bank info/cheque leaf
- Contracts / NDA
- Supplier evaluation form

Add an attachments area to the form (your file manager).

---

## 10. Notification / Workflow Hooks

- On “new supplier created” → notify Procurement + Finance
- On “customer put on credit hold” → notify Sales
- AI can later say: “This supplier has no tax info” / “This customer has exceeded credit limit.”

So leave **event hooks** in the create/update view.

---

## 11. Visual Data Model / BI Registration

When customer/supplier is added as a model:

- register `crm_customer` (or `ar_customer`) in DM
- register `ap_supplier`
- define relationship:

  - `ap_supplier` → `procurement_po_header` (1–N)
  - `crm_customer` → `sales_order_header` (1–N)
    So dashboards can show:

- top suppliers
- top customers
- vendor performance

This fits your “if relation not found → ask manual join” rule.

---

## 12. UI/UX Considerations

- **Two modes**:

  1. **Quick Add** (name + type + mobile/email + company) → for users in transactions
  2. **Full Form** (all finance/compliance/address) → for master-data/admin

- **Tabs**:

  - General
  - Finance
  - Addresses & Contacts
  - Attachments
  - History

- **Status badge**: Draft / Active / Blocked / Blacklisted
- **Disable inactivation** if customer/supplier has open invoices/POs.

---

## 13. Blocking / Blacklisting

Add these fields:

- `is_blocked` (can’t be used in new transactions)
- `block_reason`
- `blocked_by`, `blocked_at`

Procurement & Sales must check this before creating a PO/SO.

---

## 14. Auto-Code / Auto-ID (to match our policy)

- Customer code: `CUST-{company}-{sequence}` → e.g. `CUST-A-00045`
- Supplier code: `SUP-{company}-{sequence}`
- Permission codes (auto):

  - `crm_create_customer`, `crm_update_customer`, `crm_view_customer`
  - `procurement_create_supplier`, `procurement_update_supplier`, `procurement_view_supplier`

- API:

  - `/api/crm/customers/`
  - `/api/procurement/suppliers/`

- Menu:

  - `crm-customers`
  - `procurement-suppliers`

All auto, no manual naming.

---

## 15. Security / Scope

- If your ERP is multi-company → show only customers/suppliers of that company
- Allow “shared master” flag: if ON → visible to other companies in same tenant
- Enforce in viewset with your `filter_queryset_by_user_scopes(...)`

---

### In short

For **Add Customer** and **Add Supplier** you should care about:

- master-data cleanliness (duplicates)
- finance readiness (payment terms, currency, credit)
- procurement/sales readiness (what they buy/sell)
- approval/status
- multi-company
- auto-code
- BI registration
- blacklisting

If you tell me whether you want **one combined “Party” screen** (customer/supplier same model) or **two separate models**, I can give you the exact model fields too.
