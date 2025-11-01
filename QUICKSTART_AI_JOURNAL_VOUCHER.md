# Quick Start: AI-Powered Journal Voucher Upload

## What's New?

✨ **Upload PDF or images of journal vouchers and let AI fill in the form automatically!**

Your Journal Voucher form now has:
- 📤 **File Upload Button**: Upload PDF/images to auto-fill the form
- 🤖 **AI Processing**: Uses FREE Google Gemini to extract data
- 📏 **Bigger Modal**: 1400px wide (was 720px)
- 📊 **Better Layout**: Each entry fits on a single line

## 3-Step Setup

### 1. Get FREE API Key (2 minutes)
1. Go to: https://makersuite.google.com/app/apikey
2. Sign in with Google
3. Click "Create API Key"
4. Copy the key

### 2. Add to Environment (1 minute)
Create/edit `backend/.env` file:
```env
GOOGLE_GEMINI_API_KEY=paste_your_key_here
```

### 3. Install Packages (2 minutes)

**Option A - Simple (if no errors):**
```bash
cd backend
pip install -r requirements.txt
```

**Option B - If permission error on Windows:**
```bash
# Close all Python processes first
# Then run as Administrator:
cd backend
pip install google-generativeai pdf2image Pillow
```

**For PDF support, also install Poppler:**
- **Windows**: Download from https://github.com/oschwartz10612/poppler-windows/releases/
  Extract to `C:\Program Files\poppler` and add `C:\Program Files\poppler\Library\bin` to PATH
- **Linux**: `sudo apt-get install poppler-utils`
- **Mac**: `brew install poppler`

## How to Use

1. **Open** Finance → Journal Vouchers
2. **Click** "New Voucher"
3. **Upload** PDF/image using the upload button
4. **Wait** 2-5 seconds for AI to process
5. **Verify** extracted data
6. **Click** OK to save

## File Types Supported
- ✅ PDF files
- ✅ JPG/JPEG images
- ✅ PNG images
- ✅ GIF images
- ✅ WebP images
- 📦 Max size: 10MB

## What AI Extracts

The AI will automatically fill in:
- ✅ Entry date
- ✅ Reference number
- ✅ Description/narration
- ✅ Journal type (if mentioned)
- ✅ All entry lines with:
  - Account names/codes (matched to your chart of accounts)
  - Debit amounts
  - Credit amounts
  - Line descriptions

## Cost

**100% FREE** with Google Gemini free tier:
- 15 requests per minute
- 1,500 requests per day
- No credit card required
- More than enough for most businesses

## Troubleshooting

**Problem**: "API key not configured"
**Solution**: Add `GOOGLE_GEMINI_API_KEY` to `backend/.env` and restart server

**Problem**: Can't install packages
**Solution**: Run terminal as Administrator (Windows) or use `sudo` (Linux/Mac)

**Problem**: PDF not working
**Solution**: Install Poppler (see step 3 above)

## More Info

Full documentation: `docs/journal_voucher_ai_setup.md`

## Questions?

Ask your AI assistant:
- "How do I upload documents?"
- "Help with document processing"

---

**Enjoy your new AI-powered workflow!** 🚀
