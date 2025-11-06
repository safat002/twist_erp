# Django Admin - Business Type Template Loading Guide

## Visual Guide to Using Business Type Dropdown

### Step 1: Access Company Creation
```
Django Admin → Companies → Companies → Add Company
```

### Step 2: Form Sections

#### Basic Information Section
```
┌─────────────────────────────────────────────┐
│ Basic Information                           │
├─────────────────────────────────────────────┤
│ Code:           [__________]                │
│ Name:           [____________________]      │
│ Legal name:     [____________________]      │
│ Company type:   [Independent ▼]             │
└─────────────────────────────────────────────┘
```

#### Configuration Section (Important!)
```
┌─────────────────────────────────────────────────────────────────┐
│ Configuration                                                   │
│ Select a Business Type to automatically load industry-specific │
│ templates (Chart of Accounts, Categories, etc.)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Business type: ┌─────────────────────────────┐                 │
│                │ ---------                   │ ◄─── SELECT ONE │
│                │ Manufacturing               │                 │
│                │ Service Provider            │                 │
│                │ Trading/Wholesale           │                 │
│                └─────────────────────────────┘                 │
│                                                                 │
│  ℹ️ Select an industry type to automatically load pre-         │
│     configured templates (Chart of Accounts, Item Categories,  │
│     Product Categories, etc.)                                  │
│                                                                 │
│ Industry category:         MANUFACTURING (Auto-filled) 🔒       │
│ Industry sub category:     [____________________]               │
│ Default data loaded:       ❌ (Will be ✅ after save)          │
│ Default data loaded at:    (Not yet)                           │
│                                                                 │
│ Requires branch structure: ☐                                   │
│ Enable inter company...    ☐                                   │
│ Is active:                 ☑                                   │
│ Is consolidation enabled:  ☐                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Step 3: After Saving

#### Company List View
```
Companies

 + Add Company   🔍 Search

Filters:
▶ By company group
▶ By company type
▶ By industry category  ◄─── NEW FILTER
▶ By base currency
▶ By is active
▶ By default data loaded  ◄─── NEW FILTER

┌────────┬──────────────┬────────┬─────────────┬──────────┬────────┬────────────────┬──────────────┐
│ CODE   │ NAME         │ GROUP  │ TYPE        │ INDUSTRY │ ACTIVE │ DATA LOADED    │ CREATED      │
├────────┼──────────────┼────────┼─────────────┼──────────┼────────┼────────────────┼──────────────┤
│ TAL    │ TAL          │ BG1    │ Independent │ SERVICE  │ ✅     │ ✅             │ Nov 5, 2025  │
│ MFG001 │ ABC Mfg Ltd  │ BG1    │ Subsidiary  │ MANUFACT │ ✅     │ ✅             │ Nov 6, 2025  │
│ TR001  │ XYZ Trading  │ BG2    │ Independent │ TRADING  │ ✅     │ ✅             │ Nov 6, 2025  │
└────────┴──────────────┴────────┴─────────────┴──────────┴────────┴────────────────┴──────────────┘
```

#### Company Detail View (After Template Loading)
```
┌─────────────────────────────────────────────────────────────────┐
│ Configuration                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Business type:             Manufacturing                        │
│                                                                 │
│ Industry category:         MANUFACTURING 🔒                     │
│ Industry sub category:     Textile Manufacturing                │
│ Default data loaded:       ✅ Yes                              │
│ Default data loaded at:    Nov 6, 2025, 11:30 AM               │
│                                                                 │
│ ℹ️ Templates successfully loaded!                              │
│    - 150 Chart of Accounts                                     │
│    - 9 Item Categories                                         │
│    - 4 Product Categories                                      │
│    - 4 Tax Categories                                          │
│    - 3 Currencies                                              │
│    - 12 Units of Measure                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## What Happens Behind the Scenes

### Automatic Process Flow
```
┌──────────────────────────────────────────────────────────┐
│ User Action: Select "Manufacturing" & Click Save        │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Form Validation: Set industry_category = "MANUFACTURING" │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Save Company Record to Database                         │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Signal Triggered: post_save                             │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ DefaultDataService.load_all_defaults()                  │
│  ├─ Load Currencies (3 records)                         │
│  ├─ Load Units of Measure (12 records)                  │
│  ├─ Load Chart of Accounts (150 records)                │
│  ├─ Load Item Categories (9 records)                    │
│  ├─ Load Product Categories (4 records)                 │
│  └─ Load Tax Categories (4 records)                     │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Update Company:                                          │
│  - default_data_loaded = True                           │
│  - default_data_loaded_at = Now                         │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│ Success! ✅ Templates Loaded                            │
└──────────────────────────────────────────────────────────┘
```

## Dropdown Options Explained

### Option 1: Manufacturing
**Use For:**
- Manufacturing companies
- Production facilities
- Assembly operations
- Industrial manufacturing

**Templates Include:**
- Raw Materials Inventory (1131)
- Work in Progress Inventory (1132)
- Finished Goods Inventory (1133)
- Direct Material Costs (5100)
- Direct Labor Costs (5200)
- Manufacturing Overhead (5300)
- Factory Supplies
- Production Equipment
- And 144 more accounts...

**Example Companies:**
- Textile Mills
- Electronics Assembly
- Food Processing
- Automobile Parts
- Furniture Manufacturing

---

### Option 2: Service Provider
**Use For:**
- Consulting firms
- Professional services
- IT services
- Agency businesses

**Templates Include:**
- Service Revenue (4100)
- Professional Fees Income (4200)
- Consulting Revenue (4210)
- Direct Labor Costs (5100)
- Employee Costs (6100)
- Office Expenses (6200)
- Software & Subscriptions
- Professional Services
- And 124 more accounts...

**Example Companies:**
- IT Consulting
- Marketing Agencies
- Legal Firms
- Accounting Firms
- Management Consulting

---

### Option 3: Trading/Wholesale
**Use For:**
- Trading companies
- Wholesale distributors
- Import/export businesses
- Retail distributors

**Templates Include:**
- Trading Stock Inventory (1130)
- Sales Revenue - Trading (4100)
- Cost of Goods Sold - Trading (5100)
- Freight Inward (5200)
- Freight Outward (6300)
- Trading Commissions
- Import Duties
- Distribution Costs
- And 132 more accounts...

**Example Companies:**
- Wholesale Distributors
- Import/Export Companies
- Trading Houses
- Distribution Companies
- Supply Chain Businesses

## Common Scenarios

### Scenario 1: New Manufacturing Company
```
1. Select Business Type: Manufacturing
2. Save Company
3. ✅ Automatically get:
   - Manufacturing Chart of Accounts
   - Inventory accounts for raw materials, WIP, finished goods
   - Manufacturing cost accounts
   - Production-related categories
```

### Scenario 2: Service Company
```
1. Select Business Type: Service Provider
2. Save Company
3. ✅ Automatically get:
   - Service-focused Chart of Accounts
   - Professional fees accounts
   - Service delivery cost accounts
   - Service-related categories
```

### Scenario 3: Trading Company
```
1. Select Business Type: Trading/Wholesale
2. Save Company
3. ✅ Automatically get:
   - Trading-specific Chart of Accounts
   - Merchandise inventory accounts
   - Trading commission accounts
   - Import/export related accounts
```

### Scenario 4: Company Without Template
```
If you need a company type not in the list:
1. Leave Business Type empty (select "---------")
2. Save Company
3. Manually create accounts later
   OR
4. Contact admin to add new template
```

## Verification Steps

After creating a company, verify templates loaded correctly:

### Check 1: Accounts
```
Django Admin → Finance → Accounts
Filter by: Your Company

Expected Results:
- Manufacturing: ~150 accounts
- Service: ~130 accounts
- Trading: ~140 accounts
```

### Check 2: Item Categories
```
Django Admin → Inventory → Item Categories
Filter by: Your Company

Expected Results:
- Manufacturing: 9 categories
- Service: 9 categories
- Trading: 6 categories
```

### Check 3: Logs
```
Check backend logs for:
✅ INFO Loading default data for new company: [Name] (MANUFACTURING)
✅ INFO Default data loaded: {'currencies': 3, 'accounts': 150, ...}

❌ ERROR Failed to load default data: [error message]
```

## Troubleshooting

### Issue: Dropdown Shows No Options
**Solution:**
- Ensure you're on the latest code
- Check that INDUSTRIES_WITH_TEMPLATES is defined in admin.py

### Issue: Templates Not Loading
**Solution:**
1. Check company detail page
2. Look for "Default data loaded: ❌"
3. Check logs for errors
4. Manually load using management command:
   ```bash
   python manage.py load_company_defaults --company [ID]
   ```

### Issue: Wrong Templates Loaded
**Solution:**
1. Check "Industry category" field value
2. If wrong, use management command with --force:
   ```bash
   python manage.py load_company_defaults --company [ID] --force
   ```

## Tips & Best Practices

### ✅ Do This
- Select the correct business type before saving
- Review the loaded accounts after creation
- Add industry sub-category for better classification
- Keep default data loaded = True (don't manually change)

### ❌ Don't Do This
- Don't change industry_category manually after templates loaded
- Don't delete the auto-loaded accounts (modify if needed)
- Don't set default_data_loaded = False unless resetting
- Don't skip business type selection (unless intentional)

## Summary

The Business Type dropdown provides:
1. **One-Click Setup**: Select type, save, done!
2. **Industry-Specific**: Templates match your business
3. **Complete Configuration**: Everything you need pre-loaded
4. **Time Savings**: Hours of setup reduced to seconds
5. **Consistency**: All companies get proper structure

Happy company creation! 🎉
