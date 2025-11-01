"""
Document extraction skill for AI companion.
Handles extraction of structured data from PDF/image documents.
"""
from __future__ import annotations

import logging
from typing import List

from .base import BaseSkill, SkillContext, SkillResponse

logger = logging.getLogger(__name__)


class DocumentExtractionSkill(BaseSkill):
    """
    Skill for extracting structured data from documents like journal vouchers,
    invoices, receipts, etc.
    """

    name = "document_extraction"
    priority = 5
    description = "Extract structured data from PDF/image documents"

    def can_handle(self, message: str, context: SkillContext) -> bool:
        """Check if this skill can handle the message."""
        # This skill is typically invoked via API, not chat
        # But we can detect if user asks about document upload
        keywords = [
            "upload document",
            "process pdf",
            "scan receipt",
            "extract from image",
            "read document",
            "ocr",
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in keywords)

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        """Handle document extraction requests."""
        # Provide guidance to user on how to use document upload
        response_message = """I can help you extract data from documents!

**Supported Features:**
- 📄 Extract journal entries from scanned vouchers
- 🧾 Read invoice data from PDF/images
- 💰 Process receipt information

**How to use:**
1. Go to the Journal Vouchers page in Finance module
2. Click "New Voucher" button
3. Click the "Upload PDF/Image to Auto-Fill" button
4. Select your document (PDF, PNG, JPG)
5. I'll analyze it and fill in the form automatically
6. Review and verify the extracted data
7. Click OK to save

**Supported formats:** PDF, JPG, PNG, GIF, WebP (max 10MB)

**Tips for best results:**
- Use clear, high-resolution images
- Ensure text is readable
- Avoid skewed or rotated images
- Make sure the document is well-lit if photographing

Would you like me to help with anything else?"""

        return SkillResponse(
            message=response_message,
            intent="document_extraction.guide",
            confidence=0.95,
        )

    def is_authorised(self, context: SkillContext) -> bool:
        """Check if user is authorized to use this skill."""
        # All authenticated users can use document extraction
        return context.user is not None
