Perfect. Here’s the improved, final, production-grade **Backup, Restore & Update Implementation Plan** for your ERP — including local + cloud/NAS targets, verification, PITR, version lock, and admin configuration.

You can drop this straight into your system design doc.

---

# Twist ERP – Backup, Restore & Update (Final Plan)

## 1. Objectives

1. **Never lose data** – full DB + media + config.
2. **Recover fast** – restore without CLI, from UI.
3. **Store off the server** – Google Drive, OneDrive, NAS, S3/MinIO.
4. **Safe upgrades** – every update auto-backs up and can roll back.
5. **Auditable** – every backup/restore logged, with per-target status.
6. **Multi-tenant ready** – per-company export in future.

---

## 2. What We Back Up

Every backup job creates **one logical backup** containing:

1. **Database (PostgreSQL)** – full dump (`pg_dump -Fc`), all ERP data, metadata, permissions, visual data model tables, auto-added columns.
2. **Media/attachments** – zipped/tarred `/media` (invoices, supplier docs, GRNs, KYC).
3. **Config** – current `.env` or settings snapshot (DB host, email, storage configs).
4. **Manifest** – `manifest.json`:

   - app name
   - ERP version (e.g. `twist_erp 1.4.2`)
   - DB engine/version
   - tenant mode (cluster/single)
   - timestamp
   - Django migration head
   - list of storage targets used
   - checksum(s)

This gives us everything needed to restore **and** to validate the backup.

---

## 3. Core Components

### 3.1 Backup Engine (Django command)

- `python manage.py backup_full`
- Steps:

  1. create temp dir
  2. run `pg_dump` → `db.dump`
  3. archive media → `media.tar.gz`
  4. write `manifest.json`
  5. (optional) pack all into `twist-backup-<date>.tar.gz`
  6. create DB record in `sys_backup_job` (status=running)
  7. call **Backup Dispatcher** (see 3.2)
  8. mark job as success/partial/failed

### 3.2 Backup Dispatcher

- Looks up all enabled storage targets from DB:

  - local folder
  - Google Drive
  - OneDrive
  - S3/MinIO
  - NAS/share

- For each, uses driver to upload
- Writes per-target status in `sys_backup_job_target`
- If any fails → job = `partial`
- If all fail → job = `failed`
- If any fail → send ERP notification

### 3.3 Storage Drivers

- `LocalStorageDriver(base_path)`
- `GoogleDriveStorageDriver(folder_id, token)`
- `OneDriveStorageDriver(folder_id, token)`
- `S3StorageDriver(endpoint, bucket, key, secret)`
- `NASStorageDriver(path)` (really just copy to mounted path)

All storage-specific logic isolated here.

---

## 4. Storage Configuration (Admin Panel)

**Model:** `sys_backup_storage`
Fields:

- `name`
- `storage_type`: local / gdrive / onedrive / s3 / nas
- `is_enabled`
- type-specific fields (folder_id, bucket_name, base_path, token JSON)
- `encrypt_before_upload` (bool)

**Admin screens:**

1. **Backup Destinations** – add/edit/test, enable/disable
2. **Backup Policy** – schedule time, retention, encryption on/off
3. **Backup Jobs** – history, per-target status, download (for local)

**Test connection** button will try upload of a small temp file and update status.

---

## 5. Scheduling

- **Primary**: Celery beat (recommended)

  - task: `system.backup.full`
  - cron: daily at `02:00`

- **Fallback**: OS cron calling the Django command
- Backup job uses the **same** logic in both paths.

---

## 6. Retention & Cleanup

Management command / scheduled task:

- `cleanup_backups`

  - keep last **7** daily
  - keep last **4** weekly
  - keep last **3** monthly
  - keep last **3** “pre-update” backups
  - delete older local files
  - optionally delete remote ones if policy says so

Retention is configurable in admin.

---

## 7. Verification (Very Important)

After each backup:

1. **Checksum**: generate SHA-256 for the backup package → store in `sys_backup_job.checksum`
2. **Optional auto-verify** (recommended for nightly):

   - create **temporary DB** (e.g. `twist_restore_verify_<timestamp>`)
   - run `pg_restore` into it
   - run healthcheck:

     - can select from `auth_user`?
     - `django_migrations` present?
     - your key tables (finance, company, users) present?

   - if OK → mark backup as **Verified**
   - else → mark as **Unverified** and notify admin

**Admin UI** shows:

- ✅ verified
- ⚠️ unverified (use with care)

Only **verified** backups should show “One-click restore” button.

---

## 8. Restore (Safe, 2-Phase)

**We never restore straight into live DB.**
Flow:

1. User → Admin → “Restore” → pick backup (local/cloud)
2. App downloads if remote → stores in temp
3. App creates **temp DB**: `twist_restore_tmp_<timestamp>`
4. App `pg_restore` into temp DB
5. If success:

   - put app into **maintenance** (flag in DB / file)
   - swap DB (change connection / rename DBs, or update .env and reload)
   - restore media (rsync/copy)
   - exit maintenance
   - log restore

6. If failure: show error, keep running on old DB

**Extra feature (recommended):**

- “Restore as Sandbox” → same as above but don’t swap → just tell admin: DB ready at `twist_restore_tmp_...` → good for investigation.

---

## 9. PITR (Point-in-Time Recovery) – Improvement

To protect from “I imported wrong file 1 hour ago”:

1. Enable **WAL archiving** in PostgreSQL:

   - `archive_mode = on`
   - `archive_command = 'cp %p /var/backups/wal/%f'` (or to NAS/S3)

2. Keep WALs for 24–48 hours.
3. Add UI option: “Restore to Time”:

   - pick base backup
   - pick time
   - backend: restore base → replay WAL → stop at time

4. Mark PITR backups differently in history.

This gives you short-interval recovery in addition to daily full backups.

---

## 10. Update / Upgrade Flow

To make updates “hassle free,” every ERP update must follow this pipeline:

1. **Pre-check**

   - DB reachable
   - enough disk for backup
   - all enabled backup targets reachable
   - current ERP version is supported for upgrade

2. **Auto “pre-update” backup**

   - `backup_full` (flagged as `pre-update`)
   - if backup fails → block update

3. **Apply update**

   - pull new code / deploy new container
   - `python manage.py migrate`
   - run your **metadata upgrade** (register new models in DM, new permissions)
   - rebuild assets if needed

4. **Post-check**

   - run healthcheck endpoint
   - check DB schema version
   - check ERP version

5. **Mark success**

   - write to `sys_update_log`

6. **If anything fails** → **auto-restore** from the “pre-update” backup.

**Version Lock:**
In `manifest.json` and in DB, store:

```json
"app_version": "1.4.2",
"db_schema_version": "2025.11.01"
```

On restore: if backup version > current app version → block and tell admin: “Upgrade app to 1.4.2+ then restore.”

---

## 11. Security & Permissions

Define 4 permissions:

1. `system_run_backup` – can start on-demand backup
2. `system_download_backup` – can download local backups
3. `system_restore_backup` – can restore (super-sensitive)
4. `system_configure_backup` – can add/edit storage targets and policies

**Default:** only superadmin gets 3 and 4.

Store cloud tokens encrypted (field-level encryption / key in env).

---

## 12. Notifications & Monitoring

- If 2 scheduled backups in a row fail → raise **high-priority notification** in ERP + email to admin
- If cloud token expired → show banner “Google Drive backup failed — reauthorize”
- If backup filesize drops unusually (e.g. 900 MB → 50 MB) → warn (possible partial export)
- Show **System Status** widget on homepage for admins: last backup, last restore, last update.

---

## 13. Future / Optional

1. **Per-company export** – dump only data for a given company_id → good for multi-tenant moves.
2. **Partial restore** – restore only media / only DB.
3. **Encrypt-at-rest** – GPG before upload.
4. **Compression level** – configurable per target.

---

## 14. Implementation Order (practical)

1. ✅ `backup_full` command (local only)
2. ✅ DB models: `BackupStorage`, `BackupJob`, `BackupJobTarget`
3. ✅ Dispatcher + local driver
4. ✅ Admin UI: list backups, run backup
5. ✅ Restore (safe, 2-phase)
6. ✅ Add cloud/NAS drivers
7. ✅ Add scheduling (Celery/cron)
8. ✅ Add verification (restore-to-temp + healthcheck)
9. ✅ Add pre-update backup + version lock
10. ✅ Add WAL/PITR support

After step 5, you already have working backup/restore. Steps 6–10 make it “strong.”

---

That’s the improved, final version — supports local, cloud, NAS, safe restore, versioned updates, and real-world failure handling.
