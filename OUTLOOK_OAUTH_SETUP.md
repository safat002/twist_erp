# Outlook Calendar OAuth Setup Guide

## Overview
This guide will help you configure Microsoft Outlook Calendar integration for your Twist ERP system. This allows users to sync their Outlook calendars with tasks in the system.

## Prerequisites
- Microsoft Azure account (free tier is sufficient)
- Admin access to Azure AD
- Your application running locally or deployed

## Step 1: Register Application in Azure AD

### 1.1 Access Azure Portal
1. Go to [Azure Portal](https://portal.azure.com)
2. Sign in with your Microsoft account
3. Navigate to **Azure Active Directory** (or search for "Azure AD")

### 1.2 Register New Application
1. In Azure AD, click **App registrations** in the left sidebar
2. Click **+ New registration**
3. Fill in the registration form:

```
Name: Twist ERP Calendar Sync
Supported account types: Accounts in any organizational directory (Any Azure AD - Multitenant) and personal Microsoft accounts
Redirect URI:
  - Platform: Web
  - URI: http://localhost:8788/api/v1/tasks/calendar/outlook/callback
```

> **Note:** If deploying to production, add production URL too:
> `https://yourdomain.com/api/v1/tasks/calendar/outlook/callback`

4. Click **Register**

### 1.3 Note Your Application (Client) ID
After registration, you'll see the **Overview** page showing:
- **Application (client) ID**: Copy this - you'll need it for `OUTLOOK_CLIENT_ID`
- **Directory (tenant) ID**: This is optional, defaults to "common"

Example:
```
Application (client) ID: 12345678-1234-1234-1234-123456789abc
```

## Step 2: Create Client Secret

### 2.1 Generate Secret
1. In your app registration, click **Certificates & secrets** in left sidebar
2. Click **+ New client secret**
3. Enter description: `Twist ERP Calendar Access`
4. Select expiration:
   - **6 months** (for testing)
   - **12 months** or **24 months** (for production)
5. Click **Add**

### 2.2 Copy Secret Value
⚠️ **IMPORTANT:** Copy the **Value** immediately - it won't be shown again!

```
Secret Value: abc123xyz456def789ghi012jkl345mno678
```

Store this securely - you'll need it for `OUTLOOK_CLIENT_SECRET`

## Step 3: Configure API Permissions

### 3.1 Add Microsoft Graph Permissions
1. Click **API permissions** in left sidebar
2. Click **+ Add a permission**
3. Select **Microsoft Graph**
4. Select **Delegated permissions**
5. Search and add these permissions:
   - `Calendars.Read` - Read user calendars
   - `offline_access` - Maintain access to data
6. Click **Add permissions**

### 3.2 (Optional) Grant Admin Consent
If you're an admin and want to allow all users:
1. Click **Grant admin consent for [Your Organization]**
2. Click **Yes** to confirm

## Step 4: Configure Environment Variables

### 4.1 Update .env File
Open `backend/.env` and uncomment/add these lines:

```bash
# Outlook Calendar OAuth Configuration
OUTLOOK_CLIENT_ID=12345678-1234-1234-1234-123456789abc
OUTLOOK_CLIENT_SECRET=abc123xyz456def789ghi012jkl345mno678
OUTLOOK_REDIRECT_URI=http://localhost:8788/api/v1/tasks/calendar/outlook/callback
OUTLOOK_TENANT=common
```

Replace with your actual values:
- `OUTLOOK_CLIENT_ID`: Application (client) ID from Step 1.3
- `OUTLOOK_CLIENT_SECRET`: Secret value from Step 2.2
- `OUTLOOK_REDIRECT_URI`: Your callback URL (must match Azure registration)
- `OUTLOOK_TENANT`:
  - Use `common` for personal + work accounts (recommended)
  - Use specific tenant ID for organization-only accounts

### 4.2 Restart Django Server
```bash
# Stop the server (Ctrl+C)
# Restart
cd backend
python manage.py runserver
```

## Step 5: Test the Integration

### 5.1 Access Calendar Sync
1. Log in to Twist ERP
2. Navigate to **Tasks** or **Calendar** section
3. Click **Connect Outlook Calendar** button

### 5.2 Authorization Flow
1. You'll be redirected to Microsoft login
2. Sign in with your Microsoft account
3. Consent to the requested permissions:
   - Read your calendars
   - Maintain access to data you've given it access to
4. Click **Accept**
5. You'll be redirected back to Twist ERP

### 5.3 Verify Connection
After successful authorization:
- Status should show: ✅ **Outlook Connected**
- Your upcoming Outlook events should appear in the app
- Calendar sync indicator should be active

## Troubleshooting

### Error: 400 Bad Request - "Outlook OAuth is not configured"

**Cause:** Environment variables not set or server not restarted

**Solution:**
1. Verify `.env` file has all 3 required variables uncommented:
   ```bash
   OUTLOOK_CLIENT_ID=...
   OUTLOOK_CLIENT_SECRET=...
   OUTLOOK_REDIRECT_URI=...
   ```
2. Restart Django server
3. Clear browser cache and try again

### Error: Redirect URI Mismatch

**Cause:** The redirect URI in your request doesn't match Azure registration

**Solution:**
1. Go to Azure Portal → Your App → Authentication
2. Ensure redirect URI exactly matches:
   ```
   http://localhost:8788/api/v1/tasks/calendar/outlook/callback
   ```
3. Check for:
   - `http` vs `https`
   - Port number (8788)
   - Trailing slashes
   - Exact path

### Error: Invalid Client Secret

**Cause:** Secret has expired or is incorrect

**Solution:**
1. Go to Azure Portal → Your App → Certificates & secrets
2. Check if secret is expired
3. If expired, create a new secret
4. Update `OUTLOOK_CLIENT_SECRET` in `.env`
5. Restart server

### Error: Insufficient Privileges

**Cause:** App doesn't have required permissions

**Solution:**
1. Go to Azure Portal → Your App → API permissions
2. Verify these permissions are present:
   - `Calendars.Read`
   - `offline_access`
3. If missing, add them (Step 3.1)
4. User may need to re-authorize

### Error: AADSTS50011 - Reply URL mismatch

**Cause:** Redirect URI not configured in Azure

**Solution:**
1. Go to Azure Portal → Your App → Authentication
2. Under **Web** platform, ensure redirect URI is added
3. Add if missing: `http://localhost:8788/api/v1/tasks/calendar/outlook/callback`
4. Click **Save**

## Production Deployment

### Additional Configuration for Production

1. **Add Production Redirect URI:**
   ```
   Azure Portal → Your App → Authentication
   Add: https://yourdomain.com/api/v1/tasks/calendar/outlook/callback
   ```

2. **Update .env:**
   ```bash
   OUTLOOK_REDIRECT_URI=https://yourdomain.com/api/v1/tasks/calendar/outlook/callback
   ```

3. **Use Organization Tenant (Optional):**
   If you only want to allow users from your organization:
   ```bash
   OUTLOOK_TENANT=your-tenant-id-here
   ```
   Get tenant ID from Azure Portal → Azure AD → Overview

4. **Enable HTTPS:**
   - Ensure your production server uses HTTPS
   - Update redirect URI to use `https://`

## Security Best Practices

### 1. Secret Management
- ✅ Store secrets in environment variables (not in code)
- ✅ Use different secrets for development and production
- ✅ Rotate secrets regularly (every 6-12 months)
- ✅ Never commit `.env` file to version control

### 2. Redirect URI
- ✅ Use exact match (no wildcards)
- ✅ Use HTTPS in production
- ✅ Whitelist only necessary URIs

### 3. Permissions
- ✅ Request minimum required permissions
- ✅ Use delegated permissions (not application permissions)
- ✅ Review permissions regularly

### 4. Token Storage
- ✅ Tokens are stored encrypted in database
- ✅ Refresh tokens are used for long-term access
- ✅ Tokens expire and are automatically refreshed

## API Endpoints

Once configured, these endpoints become available:

### Get Auth URL
```
GET /api/v1/tasks/calendar/outlook/auth-url
```
Returns the Microsoft OAuth authorization URL

### OAuth Callback
```
GET /api/v1/tasks/calendar/outlook/callback?code=...&state=...
```
Handles the OAuth callback from Microsoft

### Check Status
```
GET /api/v1/tasks/calendar/status
```
Returns calendar sync status for current user

### Disconnect
```
POST /api/v1/tasks/calendar/disconnect
```
Revokes calendar access and removes credentials

## Frequently Asked Questions

### Q: Do I need a paid Microsoft account?
**A:** No, a free Microsoft account works fine for testing. Azure free tier is sufficient.

### Q: Can users connect their personal Outlook accounts?
**A:** Yes, if you use `OUTLOOK_TENANT=common`. Users can connect personal (@outlook.com, @hotmail.com) and work accounts.

### Q: How often does the calendar sync?
**A:** Events are fetched when the user views their calendar or task list. Automatic background sync can be configured separately.

### Q: Is the calendar two-way sync?
**A:** Currently read-only (Outlook → Twist ERP). Future versions may support two-way sync.

### Q: What happens if the secret expires?
**A:** Users will see authentication errors. Create a new secret in Azure Portal and update `.env`.

### Q: Can I use the same app registration for multiple environments?
**A:** Yes, but add separate redirect URIs for each environment (localhost, staging, production).

## Related Documentation

- [Microsoft Graph API - Calendar](https://learn.microsoft.com/en-us/graph/api/resources/calendar)
- [Azure AD App Registration](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app)
- [OAuth 2.0 Authorization Code Flow](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)

## Support

If you continue to experience issues:
1. Check Django logs for detailed error messages
2. Verify all environment variables are set correctly
3. Ensure redirect URIs match exactly
4. Try creating a new app registration from scratch

## Summary Checklist

Before testing, ensure:
- ✅ App registered in Azure AD
- ✅ Client ID copied
- ✅ Client Secret generated and copied
- ✅ API permissions added (Calendars.Read, offline_access)
- ✅ Redirect URI configured in Azure
- ✅ Environment variables set in `.env`
- ✅ Django server restarted
- ✅ Browser cache cleared

Once configured, the error message will disappear and users can connect their Outlook calendars! 🎉
