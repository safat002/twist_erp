# AI Management System - Quick Start Guide

## ✅ Implementation Complete!

Your ERP now has a comprehensive AI management system with automatic API key rotation.

---

## 🎯 What's New

### Backend Features

✅ **AI Configuration Dashboard**
- Turn AI features ON/OFF globally
- Configure 15+ settings
- Real-time status monitoring

✅ **Multi-Key Management**
- Add unlimited Gemini API keys
- Automatic rotation on rate limits
- Priority-based failover

✅ **Usage Tracking**
- Monitor all API requests
- Track successes/failures
- View response times
- Full audit trail

✅ **Scheduled Maintenance**
- Auto-reset daily counters
- Auto-reset minute counters
- Auto-cleanup old logs

---

## 🚀 Getting Started (3 Steps)

### Step 1: Access Django Admin (30 seconds)

```
1. Go to: http://localhost:8000/admin/
2. Login with your admin credentials
3. Look for "AI COMPANION" section
```

### Step 2: Add Your First API Key (2 minutes)

```
1. Click "Gemini API Keys"
2. Click "Add Gemini API Key"
3. Fill in:
   - Name: "Production Key 1"
   - API Key: [Your Google Gemini key]
   - Priority: 0
   - Daily Limit: 1500
   - Minute Limit: 15
4. Click "Save"
```

**Get FREE API Key:**
https://makersuite.google.com/app/apikey

### Step 3: Test It! (1 minute)

```
1. Go to Finance > Journal Vouchers
2. Click "New Voucher"
3. Upload a PDF/image
4. Watch AI auto-fill the form!
```

---

## 📊 Django Admin Sections

### AI Configuration
**Path:** AI COMPANION > AI Configuration

**What You Can Do:**
- ✓ Enable/disable AI assistant
- ✓ Enable/disable document processing
- ✓ Configure model settings (temperature, tokens, etc.)
- ✓ Set up caching and performance
- ✓ Configure email notifications

### Gemini API Keys
**Path:** AI COMPANION > Gemini API Keys

**What You Can Do:**
- ✓ Add new API keys
- ✓ Set priority (0 = highest)
- ✓ View usage statistics
- ✓ Reset rate limits
- ✓ Enable/disable keys

**List View Shows:**
- Name & masked key
- Status badge (Active/Rate Limited/etc.)
- Usage today with percentage
- Last used timestamp
- Availability status

### API Key Usage Logs
**Path:** AI COMPANION > API Key Usage Logs

**What You Can See:**
- All API requests
- Success/failure status
- Response times
- Error messages
- User and company context

---

## 🔄 Automatic Key Rotation

### How It Works

```
User uploads document
    ↓
System picks highest priority ACTIVE key
    ↓
Checks rate limits
    ↓
Within limits? → Use key ✓
Hit limit? → Try next key
    ↓
All keys limited? → Wait for cooldown
    ↓
After cooldown → Auto-reactivate
```

### What Happens When Rate Limited

1. Key automatically marked as "Rate Limited"
2. Cooldown timer starts (default: 60 min)
3. System switches to next available key
4. Email notification sent (if configured)
5. Usage logged for monitoring

### Example Multi-Key Setup

```
┌─────────────────────────────────────┐
│ Production Key 1 (Priority 0)       │
│ Status: Active ✓                    │
│ Usage: 450/1500 (30%)              │
└─────────────────────────────────────┘
          │
          │ If rate limited ↓
          ↓
┌─────────────────────────────────────┐
│ Production Key 2 (Priority 1)       │
│ Status: Active ✓                    │
│ Usage: 120/1500 (8%)               │
└─────────────────────────────────────┘
          │
          │ If rate limited ↓
          ↓
┌─────────────────────────────────────┐
│ Backup Key (Priority 2)             │
│ Status: Active ✓                    │
│ Usage: 0/1500 (0%)                 │
└─────────────────────────────────────┘
```

---

## 📈 Monitoring Dashboard

### Key Status Indicators

**🟢 Active**
- Ready to use
- Within rate limits
- Will be used for next request

**🟠 Rate Limited**
- Temporarily disabled
- Shows countdown: "Limited (45m left)"
- Auto-reactivates when timer expires

**⚫ Disabled**
- Manually disabled
- Won't be used until enabled

**🔴 Invalid**
- Bad credentials
- Needs to be fixed/deleted

### Usage Statistics

**Per Key:**
```
Usage Today: 450 / 1500 (30%) 🟢
Requests This Minute: 2 / 15
Last Used: 2m ago
```

**Color Coding:**
- 🟢 Green: < 50% usage
- 🟠 Orange: 50-80% usage
- 🔴 Red: > 80% usage

---

## ⚙️ Configuration Options

### Feature Toggles

```
☑ AI Assistant Enabled
☑ Document Processing Enabled
☑ Proactive Suggestions Enabled
```

### API Key Settings

```
☑ Auto Key Rotation
Max Retries: 3
Rate Limit Cooldown: 60 minutes
```

### Model Settings

```
Gemini Model: gemini-2.0-flash-exp
Max Tokens: 2048
Temperature: 0.7 (balanced)
```

### Performance

```
☑ Enable Caching
Cache TTL: 60 minutes
Request Timeout: 30 seconds
```

### Safety

```
☑ Enable Content Filtering
☑ Log All Requests
```

### Notifications

```
☑ Notify on Key Exhaustion
Email: admin@yourcompany.com
```

---

## 🛠️ Admin Actions

### Bulk Actions (Select keys and choose)

**Reset Rate Limit**
- Immediately reactivate rate-limited keys
- Use if limits were incorrectly hit

**Mark as Active**
- Enable disabled keys
- Keys will be used again

**Mark as Disabled**
- Temporarily disable keys
- Useful for testing or maintenance

---

## 📅 Scheduled Tasks

**Running Automatically:**

### Every Minute
```
Task: reset_api_key_minute_counters
Action: Resets per-minute request counters
Why: Prevents false rate limiting
```

### Daily at Midnight
```
Task: reset_api_key_daily_counters
Action: Resets daily request counters
Why: Free tier limits reset daily
```

### Daily at 3 AM
```
Task: cleanup_old_api_logs
Action: Deletes logs older than 30 days
Why: Prevents database bloat
```

---

## 🔧 Troubleshooting

### Problem: No keys available

**Solution:**
1. Go to Django Admin > Gemini API Keys
2. Check if any keys exist
3. Verify at least one is "Active" status
4. If all "Rate Limited", wait for cooldown or reset

### Problem: Keys keep getting rate limited

**Solutions:**
1. Add more keys (get multiple free API keys)
2. Increase cooldown time
3. Enable caching to reduce requests
4. Review usage logs for heavy usage

### Problem: Can't find admin section

**Solution:**
1. Ensure you're logged in as admin/superuser
2. Look for "AI COMPANION" in left sidebar
3. If missing, run: `python manage.py migrate ai_companion`

---

## 💡 Best Practices

### 1. Use Multiple Keys

**Recommended:** 3+ keys for production

```
Key 1: Main production key (Priority 0)
Key 2: Backup key (Priority 1)
Key 3: Emergency key (Priority 2)
```

### 2. Monitor Regularly

**Daily:**
- Check usage dashboard
- Review any failed requests

**Weekly:**
- Check usage patterns
- Plan for additional keys

### 3. Configure Notifications

```
1. Enable "Notify on Key Exhaustion"
2. Add your email
3. Test by hitting rate limit
```

### 4. Enable Caching

```
☑ Enable Caching
Cache TTL: 60 minutes
```

**Benefits:**
- Faster responses
- Reduced API usage
- Lower costs

---

## 📚 Documentation

**Full Guide:** `docs/ai_management_system.md`

**Topics Covered:**
- Complete feature reference
- Detailed configuration guide
- API reference
- Advanced troubleshooting
- Security best practices

---

## 🎓 Getting More API Keys

**Free Tier:**
1. Visit: https://makersuite.google.com/app/apikey
2. Create multiple Google accounts if needed
3. Generate one key per account
4. Add all keys to your system

**Free Tier Limits Per Key:**
- 15 requests/minute
- 1,500 requests/day
- No credit card required

**With 3 Keys:**
- 45 requests/minute (3 × 15)
- 4,500 requests/day (3 × 1,500)
- More than enough for most businesses!

---

## ✅ Checklist

Before going live:

- [ ] Add at least 2 API keys
- [ ] Set priorities correctly (0, 1, 2...)
- [ ] Configure email notifications
- [ ] Enable caching
- [ ] Enable auto key rotation
- [ ] Test document upload
- [ ] Review usage logs
- [ ] Set up monitoring routine

---

## 🆘 Quick Help

**Issue:** Features not working
**Fix:** Check AI Configuration > AI Assistant Enabled

**Issue:** All keys rate limited
**Fix:** Django Admin > Select keys > "Reset rate limit"

**Issue:** Want to add key
**Fix:** Django Admin > Gemini API Keys > Add

**Issue:** Need usage stats
**Fix:** Django Admin > API Key Usage Logs

---

## 🎉 You're All Set!

Your AI system is now:
- ✅ Fully functional
- ✅ Auto-rotating keys
- ✅ Monitoring usage
- ✅ Logging everything
- ✅ Maintenance-free

**Test it now:**
Go upload a journal voucher document and watch the magic happen!

---

**Questions?**
- Check full docs: `docs/ai_management_system.md`
- Review logs: `backend/logs/`
- Ask AI assistant: Built-in help available

**Enjoy your enterprise-grade AI management system!** 🚀
