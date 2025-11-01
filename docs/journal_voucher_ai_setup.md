# AI-Powered Journal Voucher Document Processing

## Overview

This feature allows you to upload PDF or image files (scanned documents, photos) of journal vouchers, and the AI will automatically extract and fill in the form fields for you. You just need to verify the data and click OK to save.

## Features

- 📄 **PDF Support**: Upload PDF files containing journal voucher information
- 🖼️ **Image Support**: Upload images (JPG, PNG, GIF, WebP) of vouchers
- 🤖 **AI Extraction**: Automatic data extraction using Google Gemini (FREE)
- ✅ **Smart Matching**: Automatically matches account names/codes to your chart of accounts
- 💾 **Easy Review**: Extracted data is pre-filled; you just verify and save

## Setup Instructions

### Step 1: Get a Free Google Gemini API Key

1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key

**Note**: Google Gemini offers a generous free tier:
- **Free quota**: 15 requests per minute
- **No credit card required**
- Sufficient for most business use cases

### Step 2: Configure Environment Variables

1. Create a `.env` file in the `backend` directory (if it doesn't exist)
2. Add your API key:

```env
GOOGLE_GEMINI_API_KEY=your_api_key_here
```

3. Save the file

### Step 3: Install Required Python Packages

**Option A: Install all at once (recommended)**

```bash
cd backend
pip install -r requirements.txt
```

**Option B: If you encounter permission errors on Windows**

1. Close any running Python processes
2. Restart your terminal as Administrator
3. Run:
```bash
cd backend
pip install google-generativeai==0.8.3 pdf2image==1.17.0 Pillow==10.2.0
```

**Option C: If you still have issues**

1. Deactivate your virtual environment
2. Delete the `venv` folder
3. Create a new virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```
4. Install all requirements:
```bash
cd backend
pip install -r requirements.txt
```

### Step 4: Install Poppler (Required for PDF Processing)

**Windows:**
1. Download Poppler for Windows: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract to `C:\Program Files\poppler`
3. Add `C:\Program Files\poppler\Library\bin` to your PATH environment variable

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install poppler-utils
```

**Mac:**
```bash
brew install poppler
```

### Step 5: Restart Your Backend Server

```bash
cd backend
python manage.py runserver
```

## How to Use

### Creating a Journal Voucher from Document

1. **Navigate** to Finance > Journals > Journal Vouchers
2. **Click** "New Voucher" button
3. **Upload Document**:
   - Click the "📄 📷 Upload PDF/Image to Auto-Fill" button
   - Select your document (PDF, PNG, JPG - max 10MB)
   - Wait for AI processing (usually 2-5 seconds)
4. **Review Extracted Data**:
   - Entry date
   - Reference number
   - Description
   - Journal entries (accounts, debits, credits)
5. **Verify and Adjust**: Make any necessary corrections
6. **Save**: Click "OK" to create the voucher

### Tips for Best Results

✅ **DO:**
- Use clear, high-resolution images (minimum 1000x1000 pixels)
- Ensure text is readable and not blurry
- Use well-lit photos if capturing with phone
- Keep documents straight (not skewed)
- Use PDFs when possible for best accuracy

❌ **DON'T:**
- Upload blurry or low-resolution images
- Use rotated or upside-down documents
- Submit heavily watermarked or obscured documents
- Exceed the 10MB file size limit

## Improved UI Layout

The modal window has been redesigned:
- **Larger Modal**: 1400px wide (was 720px)
- **Single-Line Entries**: Each journal entry now fits on a single line
- **Fixed Width Fields**:
  - Account dropdown: 450px
  - Debit/Credit: 140px each
  - Description: Flexible width
  - Remove button: Auto width

This ensures better visibility and easier data entry.

## Asking Your AI Assistant

You can also ask your AI assistant about document processing:

- "How do I upload a document?"
- "Can you process a PDF invoice?"
- "Help me extract data from an image"

The AI will guide you through the process.

## Troubleshooting

### "API key not configured" error

**Solution**: Make sure you've added `GOOGLE_GEMINI_API_KEY` to your `.env` file and restarted the server.

### "google-generativeai not installed" error

**Solution**:
```bash
pip install google-generativeai==0.8.3
```

### "Could not extract images from PDF" error

**Solution**: Install Poppler (see Step 4 above)

### AI returns generic fallback data

**Possible causes**:
1. API key not configured
2. Network connectivity issues
3. Poor quality document
4. Unsupported document format

**Solution**: Check logs in `backend/logs/` for detailed error messages.

### Permission errors during installation

**Solution**:
1. Run terminal as Administrator (Windows)
2. Or use `sudo pip install` (Linux/Mac)
3. Or create a new virtual environment

## API Rate Limits

Google Gemini free tier limits:
- **15 requests per minute**
- **1500 requests per day**

For most businesses, this is more than sufficient. If you need more:
- Upgrade to paid tier (very affordable)
- Or implement request queuing/batching

## Cost Analysis

**Free Tier (Gemini 2.0 Flash)**:
- ✅ 15 RPM (requests per minute)
- ✅ 1500 RPD (requests per day)
- ✅ No credit card required
- ✅ Vision capabilities included

**Paid Tier** (if needed):
- $0.075 per 1000 requests (very affordable)
- Higher rate limits
- Priority support

For most small to medium businesses, the free tier is sufficient.

## Security Notes

- API keys are stored in `.env` file (not in version control)
- Uploaded files are processed in memory and not permanently stored
- Audit logs record all document processing activities
- Only authenticated users can upload documents

## Future Enhancements

Planned features:
- [ ] Multi-page PDF support
- [ ] Batch document processing
- [ ] Invoice and receipt extraction
- [ ] OCR for handwritten documents
- [ ] Learning from user corrections
- [ ] Export training data for fine-tuning

## Support

For issues or questions:
1. Check backend logs: `backend/logs/`
2. Review Django admin audit logs
3. Ask your AI assistant
4. Contact system administrator

---

**Last Updated**: January 2025
**Version**: 1.0
