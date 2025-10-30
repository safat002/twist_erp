-- ====================================================================
-- Twist ERP Core Schema (Finance, Inventory, Procurement, Sales)
-- This script defines the foundational tables that support
-- the double-entry ledger, stock ledger, procure-to-pay, and
-- order-to-cash workflows.
-- Target database: PostgreSQL 13+
-- ====================================================================

BEGIN;

-- --------------------------------------------------------------------
-- Shared infrastructure tables
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS shared_database_connection (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    engine VARCHAR(100) NOT NULL,
    host VARCHAR(255),
    port INTEGER,
    "user" VARCHAR(100),
    password VARCHAR(100),
    db_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (engine IN (
        'django.db.backends.postgresql',
        'django.db.backends.mysql',
        'django.db.backends.oracle',
        'django.db.backends.sqlite3'
    ))
);

CREATE TABLE IF NOT EXISTS companies_company (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255) NOT NULL,
    parent_company_id BIGINT REFERENCES companies_company(id) ON DELETE RESTRICT,
    currency_code CHAR(3) NOT NULL DEFAULT 'BDT',
    fiscal_year_start DATE NOT NULL,
    tax_id VARCHAR(50) NOT NULL UNIQUE,
    registration_number VARCHAR(100) NOT NULL,
    settings JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    external_db_connection_id BIGINT REFERENCES shared_database_connection(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_companies_company_parent
    ON companies_company(parent_company_id);

CREATE TABLE IF NOT EXISTS permissions (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    module VARCHAR(50) NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS roles (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    company_id BIGINT REFERENCES companies_company(id) ON DELETE CASCADE,
    description TEXT,
    is_system_role BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (name, company_id)
);

CREATE TABLE IF NOT EXISTS roles_permissions (
    id BIGSERIAL PRIMARY KEY,
    role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMPTZ,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL DEFAULT '',
    last_name VARCHAR(150) NOT NULL DEFAULT '',
    email VARCHAR(254) NOT NULL DEFAULT '',
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    phone VARCHAR(20),
    avatar VARCHAR(100),
    is_system_admin BOOLEAN NOT NULL DEFAULT FALSE,
    default_company_id BIGINT REFERENCES companies_company(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_users_default_company
    ON users(default_company_id);

CREATE TABLE IF NOT EXISTS user_company_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, company_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_user_company_roles_company
    ON user_company_roles(company_id);

-- --------------------------------------------------------------------
-- Finance: Chart of Accounts, Ledger, Invoices, Payments
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS finance_account (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    parent_account_id BIGINT REFERENCES finance_account(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_bank_account BOOLEAN NOT NULL DEFAULT FALSE,
    is_control_account BOOLEAN NOT NULL DEFAULT FALSE,
    allow_direct_posting BOOLEAN NOT NULL DEFAULT TRUE,
    is_grni_account BOOLEAN NOT NULL DEFAULT FALSE,
    current_balance NUMERIC(20, 2) NOT NULL DEFAULT 0,
    currency CHAR(3) NOT NULL DEFAULT 'BDT',
    UNIQUE (company_id, code),
    CHECK (account_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'))
);

CREATE INDEX IF NOT EXISTS idx_finance_account_company_type
    ON finance_account(company_id, account_type);

CREATE TABLE IF NOT EXISTS finance_journal (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (company_id, code),
    CHECK (type IN ('GENERAL', 'SALES', 'PURCHASE', 'CASH', 'BANK'))
);

CREATE TABLE IF NOT EXISTS finance_journalvoucher (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    voucher_number VARCHAR(50) NOT NULL,
    journal_id BIGINT NOT NULL REFERENCES finance_journal(id) ON DELETE RESTRICT,
    entry_date DATE NOT NULL,
    period CHAR(7) NOT NULL,
    reference VARCHAR(100),
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    source_document_type VARCHAR(50),
    source_document_id BIGINT,
    posted_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    posted_at TIMESTAMPTZ,
    UNIQUE (company_id, voucher_number),
    CHECK (status IN ('DRAFT', 'POSTED', 'CANCELLED'))
);

CREATE INDEX IF NOT EXISTS idx_finance_journalvoucher_company_date
    ON finance_journalvoucher(company_id, entry_date);

CREATE TABLE IF NOT EXISTS finance_journalentry (
    id BIGSERIAL PRIMARY KEY,
    voucher_id BIGINT NOT NULL REFERENCES finance_journalvoucher(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    account_id BIGINT NOT NULL REFERENCES finance_account(id) ON DELETE RESTRICT,
    debit_amount NUMERIC(20, 2) NOT NULL DEFAULT 0,
    credit_amount NUMERIC(20, 2) NOT NULL DEFAULT 0,
    description VARCHAR(255),
    UNIQUE (voucher_id, line_number)
);

CREATE TABLE IF NOT EXISTS finance_invoice (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    invoice_number VARCHAR(50) NOT NULL,
    invoice_type VARCHAR(10) NOT NULL,
    partner_type VARCHAR(20) NOT NULL,
    partner_id BIGINT NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    subtotal NUMERIC(20, 2) NOT NULL,
    tax_amount NUMERIC(20, 2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(20, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(20, 2) NOT NULL,
    paid_amount NUMERIC(20, 2) NOT NULL DEFAULT 0,
    currency CHAR(3) NOT NULL DEFAULT 'BDT',
    exchange_rate NUMERIC(10, 6) NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    journal_voucher_id BIGINT REFERENCES finance_journalvoucher(id) ON DELETE SET NULL,
    notes TEXT,
    UNIQUE (company_id, invoice_number),
    CHECK (invoice_type IN ('AR', 'AP')),
    CHECK (status IN ('DRAFT', 'POSTED', 'PARTIAL', 'PAID', 'CANCELLED'))
);

CREATE INDEX IF NOT EXISTS idx_finance_invoice_company_status
    ON finance_invoice(company_id, invoice_type, status);

CREATE TABLE IF NOT EXISTS finance_invoiceline (
    id BIGSERIAL PRIMARY KEY,
    invoice_id BIGINT NOT NULL REFERENCES finance_invoice(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    description VARCHAR(255) NOT NULL,
    quantity NUMERIC(15, 3) NOT NULL DEFAULT 1,
    unit_price NUMERIC(20, 2) NOT NULL,
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
    discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    line_total NUMERIC(20, 2) NOT NULL,
    product_id BIGINT,
    account_id BIGINT NOT NULL REFERENCES finance_account(id) ON DELETE RESTRICT,
    UNIQUE (invoice_id, line_number)
);

CREATE TABLE IF NOT EXISTS finance_payment (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    payment_number VARCHAR(50) NOT NULL,
    payment_date DATE NOT NULL,
    payment_type VARCHAR(20) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    bank_account_id BIGINT REFERENCES finance_account(id) ON DELETE SET NULL,
    amount NUMERIC(20, 2) NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'BDT',
    partner_type VARCHAR(20) NOT NULL,
    partner_id BIGINT NOT NULL,
    reference VARCHAR(100),
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    journal_voucher_id BIGINT REFERENCES finance_journalvoucher(id) ON DELETE SET NULL,
    UNIQUE (company_id, payment_number),
    CHECK (payment_type IN ('RECEIPT', 'PAYMENT')),
    CHECK (payment_method IN ('CASH', 'BANK', 'CHEQUE', 'CARD', 'MOBILE')),
    CHECK (status IN ('DRAFT', 'POSTED', 'RECONCILED', 'CANCELLED'))
);

CREATE TABLE IF NOT EXISTS finance_paymentallocation (
    id BIGSERIAL PRIMARY KEY,
    payment_id BIGINT NOT NULL REFERENCES finance_payment(id) ON DELETE CASCADE,
    invoice_id BIGINT NOT NULL REFERENCES finance_invoice(id) ON DELETE RESTRICT,
    allocated_amount NUMERIC(20, 2) NOT NULL,
    UNIQUE (payment_id, invoice_id)
);

-- --------------------------------------------------------------------
-- Inventory: Master data, stock ledger, receipts, deliveries
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS inventory_productcategory (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    parent_category_id BIGINT REFERENCES inventory_productcategory(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (company_id, code)
);

CREATE TABLE IF NOT EXISTS inventory_unitofmeasure (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    code VARCHAR(10) NOT NULL,
    name VARCHAR(50) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (company_id, code)
);

CREATE TABLE IF NOT EXISTS inventory_product (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id BIGINT NOT NULL REFERENCES inventory_productcategory(id) ON DELETE RESTRICT,
    product_type VARCHAR(20) NOT NULL DEFAULT 'GOODS',
    uom_id BIGINT NOT NULL REFERENCES inventory_unitofmeasure(id) ON DELETE RESTRICT,
    track_inventory BOOLEAN NOT NULL DEFAULT TRUE,
    track_serial BOOLEAN NOT NULL DEFAULT FALSE,
    track_batch BOOLEAN NOT NULL DEFAULT FALSE,
    cost_price NUMERIC(20, 2) NOT NULL DEFAULT 0,
    selling_price NUMERIC(20, 2) NOT NULL DEFAULT 0,
    reorder_level NUMERIC(15, 3) NOT NULL DEFAULT 0,
    reorder_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    inventory_account_id BIGINT NOT NULL REFERENCES finance_account(id) ON DELETE RESTRICT,
    income_account_id BIGINT NOT NULL REFERENCES finance_account(id) ON DELETE RESTRICT,
    expense_account_id BIGINT NOT NULL REFERENCES finance_account(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (company_id, code),
    CHECK (product_type IN ('GOODS', 'SERVICE', 'CONSUMABLE'))
);

CREATE INDEX IF NOT EXISTS idx_inventory_product_category
    ON inventory_product(company_id, category_id);

CREATE TABLE IF NOT EXISTS inventory_warehouse (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    warehouse_type VARCHAR(20) NOT NULL DEFAULT 'MAIN',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (company_id, code),
    CHECK (warehouse_type IN ('MAIN', 'TRANSIT', 'RETAIL', 'VIRTUAL'))
);

CREATE TABLE IF NOT EXISTS inventory_stocklevel (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    product_id BIGINT NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    warehouse_id BIGINT NOT NULL REFERENCES inventory_warehouse(id) ON DELETE RESTRICT,
    quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    UNIQUE (company_id, product_id, warehouse_id)
);

CREATE TABLE IF NOT EXISTS inventory_stockmovement (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    movement_number VARCHAR(50) NOT NULL,
    movement_date DATE NOT NULL,
    movement_type VARCHAR(20) NOT NULL,
    from_warehouse_id BIGINT REFERENCES inventory_warehouse(id) ON DELETE RESTRICT,
    to_warehouse_id BIGINT NOT NULL REFERENCES inventory_warehouse(id) ON DELETE RESTRICT,
    reference VARCHAR(100),
    notes TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    posted_at TIMESTAMPTZ,
    UNIQUE (company_id, movement_number),
    CHECK (movement_type IN ('RECEIPT', 'ISSUE', 'TRANSFER', 'ADJUSTMENT')),
    CHECK (status IN ('DRAFT', 'SUBMITTED', 'COMPLETED', 'CANCELLED'))
);

CREATE TABLE IF NOT EXISTS inventory_stockmovementline (
    id BIGSERIAL PRIMARY KEY,
    movement_id BIGINT NOT NULL REFERENCES inventory_stockmovement(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    product_id BIGINT NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    quantity NUMERIC(15, 3) NOT NULL,
    rate NUMERIC(20, 2) NOT NULL,
    batch_no VARCHAR(50),
    serial_no VARCHAR(50),
    UNIQUE (movement_id, line_number)
);

CREATE TABLE IF NOT EXISTS inventory_stockledger (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    transaction_date TIMESTAMPTZ NOT NULL,
    transaction_type VARCHAR(20) NOT NULL,
    product_id BIGINT NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    warehouse_id BIGINT NOT NULL REFERENCES inventory_warehouse(id) ON DELETE RESTRICT,
    quantity NUMERIC(15, 3) NOT NULL,
    rate NUMERIC(20, 2) NOT NULL,
    value NUMERIC(20, 2) NOT NULL,
    balance_qty NUMERIC(15, 3) NOT NULL,
    balance_value NUMERIC(20, 2) NOT NULL,
    source_document_type VARCHAR(50) NOT NULL,
    source_document_id BIGINT NOT NULL,
    batch_no VARCHAR(50),
    serial_no VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (transaction_type IN ('RECEIPT', 'ISSUE', 'TRANSFER', 'ADJUSTMENT'))
);

CREATE INDEX IF NOT EXISTS idx_inventory_stockledger_product
    ON inventory_stockledger(company_id, product_id, warehouse_id);

-- --------------------------------------------------------------------
-- Procurement: Suppliers and Purchase Orders
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS procurement_supplier (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(254),
    phone VARCHAR(20),
    address TEXT,
    payment_terms INTEGER NOT NULL DEFAULT 30,
    payable_account_id BIGINT NOT NULL REFERENCES finance_account(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (company_id, code)
);

CREATE TABLE IF NOT EXISTS procurement_purchaseorder (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    order_number VARCHAR(50) NOT NULL,
    order_date DATE NOT NULL,
    supplier_id BIGINT NOT NULL REFERENCES procurement_supplier(id) ON DELETE RESTRICT,
    expected_delivery_date DATE NOT NULL,
    delivery_address_id BIGINT NOT NULL REFERENCES inventory_warehouse(id) ON DELETE RESTRICT,
    subtotal NUMERIC(20, 2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(20, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(20, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    notes TEXT,
    UNIQUE (company_id, order_number),
    CHECK (status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'PARTIAL', 'RECEIVED', 'CANCELLED'))
);

CREATE TABLE IF NOT EXISTS procurement_purchaseorderline (
    id BIGSERIAL PRIMARY KEY,
    purchase_order_id BIGINT NOT NULL REFERENCES procurement_purchaseorder(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    item_id BIGINT NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    quantity NUMERIC(15, 3) NOT NULL,
    unit_price NUMERIC(20, 2) NOT NULL,
    total_price NUMERIC(20, 2) NOT NULL,
    received_quantity NUMERIC(15, 3) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    UNIQUE (purchase_order_id, line_number),
    CHECK (status IN ('OPEN', 'RECEIVED'))
);

-- --------------------------------------------------------------------
-- Inventory receipts and deliveries (after procurement & sales)
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS inventory_goodsreceipt (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    receipt_number VARCHAR(50) NOT NULL,
    receipt_date DATE NOT NULL,
    purchase_order_id BIGINT NOT NULL REFERENCES procurement_purchaseorder(id) ON DELETE RESTRICT,
    supplier_id BIGINT NOT NULL REFERENCES procurement_supplier(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    notes TEXT,
    UNIQUE (company_id, receipt_number),
    CHECK (status IN ('DRAFT', 'POSTED'))
);

CREATE TABLE IF NOT EXISTS inventory_goodsreceiptline (
    id BIGSERIAL PRIMARY KEY,
    goods_receipt_id BIGINT NOT NULL REFERENCES inventory_goodsreceipt(id) ON DELETE CASCADE,
    purchase_order_line_id BIGINT NOT NULL REFERENCES procurement_purchaseorderline(id) ON DELETE RESTRICT,
    item_id BIGINT NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    quantity_received NUMERIC(15, 3) NOT NULL,
    UNIQUE (goods_receipt_id, purchase_order_line_id)
);

-- --------------------------------------------------------------------
-- Sales: Customers and Sales Orders
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS sales_customer (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    code VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(254),
    phone VARCHAR(20),
    mobile VARCHAR(20),
    billing_address TEXT,
    shipping_address TEXT,
    credit_limit NUMERIC(20, 2) NOT NULL DEFAULT 0,
    payment_terms INTEGER NOT NULL DEFAULT 30,
    receivable_account_id BIGINT NOT NULL REFERENCES finance_account(id) ON DELETE RESTRICT,
    customer_status VARCHAR(20) NOT NULL DEFAULT 'LEAD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (company_id, code),
    CHECK (customer_status IN ('LEAD', 'PROSPECT', 'ACTIVE', 'INACTIVE'))
);

CREATE TABLE IF NOT EXISTS sales_salesorder (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    order_number VARCHAR(50) NOT NULL,
    order_date DATE NOT NULL,
    customer_id BIGINT NOT NULL REFERENCES sales_customer(id) ON DELETE RESTRICT,
    delivery_date DATE NOT NULL,
    shipping_address TEXT NOT NULL,
    subtotal NUMERIC(20, 2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(20, 2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(20, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(20, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    notes TEXT,
    UNIQUE (company_id, order_number),
    CHECK (status IN ('DRAFT', 'CONFIRMED', 'PARTIAL', 'DELIVERED', 'INVOICED', 'CANCELLED'))
);

CREATE TABLE IF NOT EXISTS sales_salesorderline (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES sales_salesorder(id) ON DELETE CASCADE,
    line_number INTEGER NOT NULL,
    product_id BIGINT NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    description VARCHAR(255),
    quantity NUMERIC(15, 3) NOT NULL,
    unit_price NUMERIC(20, 2) NOT NULL,
    discount_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
    line_total NUMERIC(20, 2) NOT NULL,
    delivered_qty NUMERIC(15, 3) NOT NULL DEFAULT 0,
    warehouse_id BIGINT NOT NULL REFERENCES inventory_warehouse(id) ON DELETE RESTRICT,
    UNIQUE (order_id, line_number)
);

-- --------------------------------------------------------------------
-- Inventory deliveries (dependent on sales)
-- --------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS inventory_deliveryorder (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies_company(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    delivery_number VARCHAR(50) NOT NULL,
    delivery_date DATE NOT NULL,
    sales_order_id BIGINT NOT NULL REFERENCES sales_salesorder(id) ON DELETE RESTRICT,
    customer_id BIGINT NOT NULL REFERENCES sales_customer(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    notes TEXT,
    UNIQUE (company_id, delivery_number),
    CHECK (status IN ('DRAFT', 'POSTED'))
);

CREATE TABLE IF NOT EXISTS inventory_deliveryorderline (
    id BIGSERIAL PRIMARY KEY,
    delivery_order_id BIGINT NOT NULL REFERENCES inventory_deliveryorder(id) ON DELETE CASCADE,
    sales_order_line_id BIGINT NOT NULL REFERENCES sales_salesorderline(id) ON DELETE RESTRICT,
    item_id BIGINT NOT NULL REFERENCES inventory_product(id) ON DELETE RESTRICT,
    quantity_shipped NUMERIC(15, 3) NOT NULL,
    UNIQUE (delivery_order_id, sales_order_line_id)
);

COMMIT;
