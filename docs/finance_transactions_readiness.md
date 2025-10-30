## Finance Transaction Entry Readiness

The finance posting pipeline has been hardened for production use.

### Voucher Numbering & Sequencing

- New table `finance_journalsequence` issues per-company, per-journal running numbers.
- Journal vouchers now store `sequence_number` alongside the human-friendly `voucher_number`.

### Journal Service Rules

- `JournalService.create_journal_voucher` validates that:
  - All accounts belong to the same company and allow direct posting.
  - Debit and credit values are positive, exclusive, and balanced.
  - Voucher numbers are automatically generated in the format `{JOURNAL_CODE}-{FISCAL_YEAR}-{####}`.
- Entries are created in bulk to preserve ordering and atomicity.

- `JournalService.post_journal_voucher` now locks the voucher, entries, and accounts before updating balances and re-validates the double-entry totals prior to posting.

### Invoice Posting

- Supplier and sales invoices pass the posting user as the journal creator, ensuring audit trails remain intact.

### Outstanding Tasks

- Configure purchase (`PURCHASE`), sales (`SALES`), and general (`GENERAL`) journals per company.
- Flag any master data (suppliers, customers, accounts) missing required ledger mappings before go-live.
