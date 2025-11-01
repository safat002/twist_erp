# AI Management System - Complete Guide

## Overview

The AI Management System provides comprehensive control over AI features in your ERP system, including:

- ✅ Enable/Disable AI features globally
- ✅ Manage multiple Gemini API keys
- ✅ Automatic API key rotation on rate limits
- ✅ Usage tracking and monitoring
- ✅ Detailed configuration options
- ✅ Scheduled tasks for maintenance

## Table of Contents

1. [Features](#features)
2. [Getting Started](#getting-started)
3. [AI Configuration](#ai-configuration)
4. [API Key Management](#api-key-management)
5. [Automatic Key Rotation](#automatic-key-rotation)
6. [Usage Monitoring](#usage-monitoring)
7. [Scheduled Tasks](#scheduled-tasks)
8. [Django Admin Guide](#django-admin-guide)
9. [Troubleshooting](#troubleshooting)

---

## Features

### AI Configuration

Global settings for the AI system:

**Feature Toggles:**
- AI Assistant ON/OFF
- Document Processing ON/OFF
- Proactive Suggestions ON/OFF

**API Key Management:**
- Auto key rotation
- Max retries
- Rate limit cooldown duration

**Model Settings:**
- Gemini model selection
- Max tokens
- Temperature (creativity)

**Performance:**
- Request timeout
- Response caching
- Cache TTL

**Safety:**
- Content filtering
- Request logging

**Notifications:**
- Alert on key exhaustion
- Email notifications

### API Key Management

**Multiple Keys:**
- Add unlimited API keys
- Priority-based selection
- Status tracking (Active/Rate Limited/Disabled/Invalid)

**Rate Limiting:**
- Daily limits (default: 1500 requests)
- Per-minute limits (default: 15 requests)
- Automatic cooldown
- Usage counters

**Monitoring:**
- Requests today
- Requests this minute
- Last used timestamp
- Error tracking

---

## Getting Started

### Step 1: Access Django Admin

1. Navigate to: `http://your-domain/admin/`
2. Login with your admin credentials
3. Look for **AI COMPANION** section in the sidebar

### Step 2: Configure AI Settings

1. Click on **AI Configuration**
2. You'll see the default configuration or create one
3. Adjust settings as needed:
   - Enable/disable features
   - Set model preferences
   - Configure performance options

### Step 3: Add API Keys

1. Click on **Gemini API Keys**
2. Click **Add Gemini API Key**
3. Fill in the form:
   - **Name**: e.g., "Production Key 1"
   - **API Key**: Your Google Gemini API key
   - **Priority**: 0 (highest), 1, 2, etc.
   - **Daily Limit**: 1500 (free tier default)
   - **Minute Limit**: 15 (free tier default)
4. Click **Save**

### Step 4: Test the System

1. Go to Finance > Journal Vouchers
2. Create New Voucher
3. Upload a PDF/image
4. System will automatically use the first available key

---

## AI Configuration

### Accessing Configuration

**Django Admin Path:** AI COMPANION > AI Configuration

**Single Instance:** Only one configuration exists (automatically created)

### Feature Toggles

#### AI Assistant Enabled
- **Default:** True
- **Description:** Master switch for all AI features
- **Effect:** When disabled, all AI features stop working

#### Document Processing Enabled
- **Default:** True
- **Description:** Enable PDF/image document extraction
- **Effect:** Controls journal voucher auto-fill feature

#### Proactive Suggestions Enabled
- **Default:** True
- **Description:** Enable AI-generated suggestions
- **Effect:** Controls proactive insights and recommendations

### API Key Management Settings

#### Auto Key Rotation
- **Default:** True
- **Description:** Automatically switch to next key when one is rate limited
- **Recommended:** Keep enabled for uninterrupted service

#### Max Retries
- **Default:** 3
- **Range:** 1-10
- **Description:** How many times to retry with different keys before giving up

#### Rate Limit Cooldown Minutes
- **Default:** 60
- **Range:** 1-1440 (24 hours)
- **Description:** How long to wait before retrying a rate-limited key

### Model Settings

#### Gemini Model
- **Default:** `gemini-2.0-flash-exp`
- **Options:**
  - `gemini-2.0-flash-exp` - Fast, vision-enabled (recommended)
  - `gemini-pro-vision` - High quality vision
  - `gemini-pro` - Text only
- **Description:** Which Gemini model to use for document processing

#### Max Tokens
- **Default:** 2048
- **Range:** 256-8192
- **Description:** Maximum length of AI response
- **Note:** Higher = more detailed but slower

#### Temperature
- **Default:** 0.7
- **Range:** 0.0-1.0
- **Description:** AI creativity level
  - 0.0 = Very focused and deterministic
  - 0.7 = Balanced (recommended for data extraction)
  - 1.0 = Very creative

### Performance Settings

#### Request Timeout Seconds
- **Default:** 30
- **Range:** 5-300
- **Description:** How long to wait for AI response

#### Enable Caching
- **Default:** True
- **Description:** Cache identical requests
- **Benefit:** Faster responses, reduced API usage

#### Cache TTL Minutes
- **Default:** 60
- **Range:** 1-1440
- **Description:** How long to keep cached responses

### Safety Settings

#### Enable Content Filtering
- **Default:** True
- **Description:** Filter inappropriate AI responses
- **Recommended:** Keep enabled

#### Log All Requests
- **Default:** True
- **Description:** Log every AI API request
- **Benefit:** Full audit trail, debugging

### Notifications

#### Notify on Key Exhaustion
- **Default:** True
- **Description:** Send email when all keys are rate limited

#### Notification Email
- **Default:** (empty)
- **Format:** admin@yourcompany.com
- **Description:** Where to send alerts

---

## API Key Management

### Adding a New Key

1. **Get API Key from Google:**
   - Visit: https://makersuite.google.com/app/apikey
   - Sign in with Google
   - Click "Create API Key"
   - Copy the key

2. **Add to System:**
   ```
   Name: Production Key 1
   API Key: AIzaSyD... (paste your key)
   Status: Active
   Priority: 0 (or higher number for lower priority)
   Daily Limit: 1500
   Minute Limit: 15
   ```

3. **Click Save**

### Priority System

Keys are used in order of priority:
- **Priority 0** - Highest priority (used first)
- **Priority 1** - Second choice
- **Priority 2** - Third choice
- etc.

**Example Setup:**
```
Key 1: Priority 0 (Main production key)
Key 2: Priority 1 (Backup key 1)
Key 3: Priority 2 (Backup key 2)
```

### Key Status

#### Active (Green)
- Ready to use
- Within rate limits
- Will be used for next request

#### Rate Limited (Orange)
- Temporarily disabled
- Hit daily or per-minute limit
- Shows cooldown time remaining
- Automatically reactivates when cooldown expires

#### Disabled (Gray)
- Manually disabled by admin
- Won't be used until manually re-enabled

#### Invalid (Red)
- Authentication failed
- Key is incorrect or revoked
- Needs to be updated or deleted

### Manual Actions

**In Django Admin, select key(s) and choose action:**

1. **Reset Rate Limit:**
   - Immediately reactivate rate-limited keys
   - Use if limits were hit incorrectly

2. **Mark as Active:**
   - Manually enable disabled keys

3. **Mark as Disabled:**
   - Temporarily disable keys without deleting

---

## Automatic Key Rotation

### How It Works

```
Request comes in
    ↓
Get highest priority ACTIVE key
    ↓
Check if within rate limits
    ↓
YES → Use this key
NO → Try next priority key
    ↓
All keys exhausted?
    ↓
YES → Fail with error
NO → Continue rotation
```

### Rate Limit Detection

The system automatically detects:
- **Daily limits:** Tracks requests_today vs daily_limit
- **Per-minute limits:** Tracks requests_this_minute vs minute_limit
- **API errors:** "429 Too Many Requests", "quota exceeded", etc.

### What Happens When Rate Limited

1. **Mark key as rate_limited**
2. **Set cooldown timer** (default: 60 minutes)
3. **Try next available key**
4. **Log the event**
5. **Send notification** (if enabled)

### Cooldown Behavior

- Rate-limited keys automatically reactivate after cooldown
- Cooldown timer is configurable (1-1440 minutes)
- Manual reset available in Django admin

---

## Usage Monitoring

### API Key Usage Logs

**Location:** Django Admin > AI COMPANION > API Key Usage Logs

**Information Tracked:**
- Timestamp
- API Key used
- Operation (e.g., "document_processing_image")
- Success/Failure
- Error message (if failed)
- Response time (milliseconds)
- User who made request
- Company context
- Additional metadata

###Usage Dashboard

**In API Key list:**
- **Usage Today:** 45 / 1500 (3.0%)
- **Last Used:** 5m ago
- **Status Badge:** Active / Rate Limited / etc.
- **Availability:** Ready / Limited (30m left) / Unavailable

### Monitoring Best Practices

1. **Check daily** - Review usage in Django admin
2. **Watch for patterns** - High usage times
3. **Plan for growth** - Add keys before hitting limits
4. **Review logs** - Identify issues early

---

## Scheduled Tasks

### Automatic Maintenance

**Three tasks run automatically:**

#### 1. Reset Daily Counters
- **Schedule:** Daily at midnight (00:00)
- **Task:** `reset_api_key_daily_counters`
- **Action:** Resets `requests_today` to 0 for all keys
- **Why:** Free tier limits reset daily

#### 2. Reset Minute Counters
- **Schedule:** Every minute
- **Task:** `reset_api_key_minute_counters`
- **Action:** Resets `requests_this_minute` to 0
- **Why:** Prevents false rate limiting

#### 3. Cleanup Old Logs
- **Schedule:** Daily at 3 AM
- **Task:** `cleanup_old_api_logs`
- **Action:** Deletes logs older than 30 days
- **Why:** Prevents database bloat

### Monitoring Tasks

Check Celery logs:
```bash
# View logs
tail -f logs/celery.log | grep "AI Companion"

# You should see:
# AI Companion: Reset daily counters for 3 API key(s)
# AI Companion: Reset minute counters for 3 API key(s)
# AI Companion: Deleted 150 old API usage log(s)
```

---

## Django Admin Guide

### Navigation

```
Django Admin
└── AI COMPANION
    ├── AI Configuration (1 object)
    ├── Gemini API Keys (manage multiple)
    ├── API Key Usage Logs (view only)
    ├── AI Conversations
    ├── AI Messages
    ├── AI Feedback
    ├── AI Proactive Suggestions
    └── ... (other AI features)
```

### AI Configuration Screen

**Sections:**
1. Feature Toggles - ON/OFF switches
2. API Key Management - Rotation settings
3. Model Settings - Gemini configuration
4. Performance Settings - Speed optimizations
5. Safety Settings - Security options
6. Notifications - Alert configuration

**Tips:**
- Only one configuration exists
- Cannot delete (only edit)
- Changes apply immediately

### Gemini API Keys Screen

**List View Shows:**
- Name
- Masked Key (AIza****1234)
- Status Badge (colored)
- Priority
- Usage Today (with percentage)
- Last Used
- Availability

**Actions Available:**
- Add new key
- Edit existing key
- Reset rate limit (bulk action)
- Mark as active (bulk action)
- Mark as disabled (bulk action)
- Delete key

**Filters:**
- By status
- By priority

**Search:**
- By name
- By API key

### API Key Usage Logs Screen

**List View Shows:**
- Timestamp
- API Key name
- Operation
- Success/Failed status
- Response time
- User
- Company

**Filters:**
- By success/failure
- By operation type
- By date

**Features:**
- Read-only (no add/edit/delete)
- Full audit trail
- Sortable columns
- Date hierarchy

---

## Troubleshooting

### Issue 1: "No API keys available"

**Symptoms:**
- Document upload returns fallback data
- Error in logs: "No API keys available"

**Solutions:**
1. Check if any keys exist in Django admin
2. Verify at least one key has status "Active"
3. Check if Document Processing is enabled in AI Configuration
4. Ensure keys aren't all rate limited
5. Try manual "Reset Rate Limit" action

### Issue 2: All keys showing "Rate Limited"

**Symptoms:**
- All keys orange/rate limited
- Features not working

**Solutions:**
1. **Wait for cooldown** - Keys auto-reactivate
2. **Add more keys** - Get additional free API keys
3. **Manual reset** - Use "Reset rate limit" action
4. **Upgrade to paid tier** - Higher limits
5. **Check rate limits** - Maybe set too low

### Issue 3: Key marked as "Invalid"

**Symptoms:**
- Red status badge
- "Unauthorized" or "Invalid API key" errors

**Solutions:**
1. **Verify API key** - Check it's correct
2. **Check Google Console** - Key might be revoked
3. **Regenerate key** - Get new one from Google
4. **Update or delete** - Fix the key or remove it

### Issue 4: Document processing not working

**Symptoms:**
- Upload doesn't auto-fill
- Fallback message appears

**Checklist:**
1. ✅ AI Configuration > Document Processing Enabled?
2. ✅ At least one Active API key?
3. ✅ Packages installed? (google-generativeai, pdf2image, Pillow)
4. ✅ Check usage logs for errors
5. ✅ Try manual upload with different file

### Issue 5: High API usage

**Symptoms:**
- Keys hitting limits quickly
- Usage dashboard shows high numbers

**Solutions:**
1. **Enable caching** - Reduce duplicate requests
2. **Add more keys** - Distribute load
3. **Review logs** - Find heavy users
4. **Set quotas** - Limit per-user requests
5. **Optimize prompts** - Reduce token usage

### Issue 6: Notifications not sending

**Symptoms:**
- No emails when keys exhausted

**Checklist:**
1. ✅ Notify on Key Exhaustion enabled?
2. ✅ Notification Email configured?
3. ✅ Email settings correct in Django?
4. ✅ Check spam folder
5. ✅ Test email functionality

---

## Best Practices

### 1. Multiple Keys Strategy

**Recommended Setup:**
```
Production Key 1 (Priority 0)
Production Key 2 (Priority 1)
Backup Key 1 (Priority 2)
Emergency Key (Priority 99)
```

**Why:**
- Automatic failover
- No downtime
- Better load distribution

### 2. Monitoring Routine

**Daily:**
- Check usage dashboard
- Review any failed requests
- Monitor key status

**Weekly:**
- Review usage logs
- Check for patterns
- Plan capacity

**Monthly:**
- Clean up old logs (automatic)
- Review configuration
- Update keys if needed

### 3. Configuration Tips

**For Production:**
```
Auto Key Rotation: ✓ Enabled
Max Retries: 3
Log All Requests: ✓ Enabled
Enable Caching: ✓ Enabled
Notify on Exhaustion: ✓ Enabled
```

**For Development:**
```
Auto Key Rotation: ✓ Enabled
Max Retries: 1 (fail fast)
Log All Requests: ✓ Enabled (debugging)
Enable Caching: ✗ Disabled (testing)
```

### 4. Security

✅ **DO:**
- Rotate API keys periodically
- Use descriptive key names
- Enable request logging
- Monitor for unusual patterns
- Set up email alerts

❌ **DON'T:**
- Share API keys
- Commit keys to version control
- Disable content filtering
- Ignore rate limit warnings
- Use same key everywhere

---

## API Reference

### Programmatic Access

```python
from apps.ai_companion.models import AIConfiguration, GeminiAPIKey
from apps.ai_companion.services.api_key_manager import APIKeyManager

# Get configuration
config = AIConfiguration.get_config()

# Check if document processing is enabled
if config.document_processing_enabled:
    # Get available key
    api_key, key_obj = APIKeyManager.get_available_key()

    # Use with retry logic
    result = APIKeyManager.process_with_retry(
        operation_func=my_function,
        operation_name="my_operation",
        max_retries=3,
        user=request.user,
        company=company
    )
```

---

## Support

### Getting Help

1. **Check logs** - `backend/logs/`
2. **Django admin** - Review usage logs
3. **Documentation** - This guide
4. **Ask AI assistant** - Built-in help

### Common Log Locations

```bash
# Application logs
backend/logs/django.log

# Celery logs
backend/logs/celery.log

# AI-specific
grep "AI Companion" backend/logs/*.log
```

---

## Appendix

### Free Tier Limits (Google Gemini)

- **Requests per minute:** 15
- **Requests per day:** 1,500
- **No credit card required**
- **Limits reset daily**

### Upgrading to Paid

**Benefits:**
- Higher rate limits
- Priority support
- No daily reset needed

**Cost:** ~$0.075 per 1,000 requests (very affordable)

**When to upgrade:**
- > 1,500 requests/day consistently
- Need guaranteed uptime
- High-volume production use

---

**Last Updated:** January 2025
**Version:** 1.0
**Status:** Production Ready
