"""
Document processing service for extracting journal entry data from PDF/images using AI.
Uses Google Gemini (free tier) for document analysis with automatic API key rotation.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process PDF/image documents to extract journal entry data using AI with automatic key rotation."""

    def __init__(self, user=None, company=None):
        """Initialize with optional user and company for logging."""
        self.user = user
        self.company = company

    def process_journal_voucher_document(
        self,
        file_content: bytes,
        file_name: str,
        company,
        accounts_list: List[Dict],
        journals_list: List[Dict],
    ) -> Dict:
        """
        Extract journal voucher data from a PDF or image document.

        Args:
            file_content: The binary content of the uploaded file
            file_name: Name of the uploaded file
            company: Company instance for context
            accounts_list: List of available accounts for matching
            journals_list: List of available journals for matching

        Returns:
            Dictionary containing extracted journal voucher data
        """
        # Determine file type
        file_ext = file_name.lower().split('.')[-1] if '.' in file_name else ''

        if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            return self._process_image(file_content, file_ext, company, accounts_list, journals_list)
        elif file_ext == 'pdf':
            return self._process_pdf(file_content, company, accounts_list, journals_list)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

    def _process_image(
        self,
        image_content: bytes,
        file_ext: str,
        company,
        accounts_list: List[Dict],
        journals_list: List[Dict],
    ) -> Dict:
        """Process image using Google Gemini vision API with automatic key rotation."""
        from apps.ai_companion.services.api_key_manager import APIKeyManager
        from apps.ai_companion.models import AIConfiguration

        # Get AI configuration
        try:
            config = AIConfiguration.get_config()
            if not config.document_processing_enabled:
                logger.warning("Document processing is disabled in AI configuration")
                return self._fallback_extraction()
        except Exception as e:
            logger.error(f"Could not load AI configuration: {e}")
            return self._fallback_extraction()

        try:
            import google.generativeai as genai
            from PIL import Image
            import io
        except ImportError:
            logger.error("google-generativeai or Pillow not installed. Run: pip install google-generativeai Pillow")
            return self._fallback_extraction()

        def process_with_key(api_key, key_obj):
            """Process image with given API key."""
            # Configure Gemini
            genai.configure(api_key=api_key)

            # Use configured model or default
            model_name = config.gemini_model if hasattr(config, 'gemini_model') else 'gemini-2.0-flash-exp'
            model = genai.GenerativeModel(model_name)

            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_content))

            # Create prompt for Gemini
            prompt = self._build_extraction_prompt(company, accounts_list, journals_list)

            # Generate content with vision
            response = model.generate_content([prompt, image])

            # Extract JSON from response
            response_text = response.text
            return self._parse_ai_response(response_text, accounts_list, journals_list)

        # Use API key manager with automatic rotation
        try:
            result = APIKeyManager.process_with_retry(
                operation_func=process_with_key,
                operation_name="document_processing_image",
                max_retries=config.max_retries if hasattr(config, 'max_retries') else 3,
                user=self.user,
                company=self.company
            )

            if result:
                return result
            else:
                logger.error("All API key attempts failed")
                return self._fallback_extraction()

        except Exception as e:
            logger.exception(f"Error processing image with Gemini: {e}")
            return self._fallback_extraction()

    def _process_pdf(
        self,
        pdf_content: bytes,
        company,
        accounts_list: List[Dict],
        journals_list: List[Dict],
    ) -> Dict:
        """Process PDF by converting to images and using Gemini vision API."""
        if not self.api_key:
            logger.warning("Google Gemini API key not configured. Using fallback extraction.")
            return self._fallback_extraction()

        try:
            from pdf2image import convert_from_bytes
        except ImportError:
            logger.error("pdf2image not installed. Run: pip install pdf2image")
            return self._fallback_extraction()

        try:
            # Convert PDF to images (first page only for now)
            images = convert_from_bytes(pdf_content, first_page=1, last_page=1)

            if not images:
                raise ValueError("Could not extract images from PDF")

            # Process first page as image
            import io
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()

            # Process as image
            return self._process_image(img_byte_arr, 'png', company, accounts_list, journals_list)

        except Exception as e:
            logger.exception(f"Error processing PDF: {e}")
            return self._fallback_extraction()

    def _build_extraction_prompt(
        self,
        company,
        accounts_list: List[Dict],
        journals_list: List[Dict],
    ) -> str:
        """Build the prompt for Gemini to extract journal entry data."""

        # Format accounts for the prompt (limit to avoid token overflow)
        accounts_info = "\n".join([
            f"- ID: {acc['id']}, Code: {acc['code']}, Name: {acc['name']}"
            for acc in accounts_list[:50]
        ])

        # Format journals for the prompt
        journals_info = "\n".join([
            f"- ID: {j['id']}, Code: {j.get('code', 'N/A')}, Name: {j['name']}"
            for j in journals_list
        ])

        prompt = f"""You are an AI assistant helping to extract journal entry data from financial documents.

Please analyze the image and extract the following information for a journal voucher:

1. Entry Date (date in YYYY-MM-DD format)
2. Reference number or document reference
3. Description/Narration
4. Journal type (if mentioned)
5. All journal entries with:
   - Account name or code
   - Debit amount (if any)
   - Credit amount (if any)
   - Line description

Available Accounts (for matching):
{accounts_info}

Available Journals (for matching):
{journals_info}

IMPORTANT:
- Try to match account names/codes from the document to the account IDs in the list above
- Try to match journal type to the journal IDs in the list above
- If you cannot find an exact match, leave the ID fields as null
- Return the data in JSON format as shown below
- Ensure debits and credits are balanced
- Use decimal numbers for amounts (e.g., 1500.00, not 1,500)

Return ONLY a valid JSON object with this structure (no additional text, no markdown code blocks):
{{
  "entry_date": "YYYY-MM-DD",
  "reference": "reference number or text",
  "description": "overall description",
  "journal_id": null or matching journal ID,
  "entries": [
    {{
      "account_id": null or matching account ID,
      "account_name": "account name from document",
      "debit_amount": 0.00,
      "credit_amount": 0.00,
      "description": "line description"
    }}
  ]
}}"""
        return prompt

    def _parse_ai_response(
        self,
        response_text: str,
        accounts_list: List[Dict],
        journals_list: List[Dict],
    ) -> Dict:
        """Parse the AI response and validate the data."""
        try:
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Try to find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")

            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)

            # Validate and clean the data
            result = {
                'entry_date': data.get('entry_date'),
                'reference': data.get('reference', ''),
                'description': data.get('description', ''),
                'journal_id': data.get('journal_id'),
                'entries': []
            }

            for entry in data.get('entries', []):
                cleaned_entry = {
                    'account_id': entry.get('account_id'),
                    'account_name': entry.get('account_name', ''),
                    'debit_amount': float(entry.get('debit_amount', 0)),
                    'credit_amount': float(entry.get('credit_amount', 0)),
                    'description': entry.get('description', ''),
                }
                result['entries'].append(cleaned_entry)

            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.debug(f"Response text: {response_text}")
            return self._fallback_extraction()

    def _fallback_extraction(self) -> Dict:
        """Return a minimal structure when AI processing fails."""
        from datetime import date

        return {
            'entry_date': date.today().isoformat(),
            'reference': '',
            'description': 'AI processing unavailable. Please manually enter the journal entry details.',
            'journal_id': None,
            'entries': [
                {
                    'account_id': None,
                    'account_name': '',
                    'debit_amount': 0,
                    'credit_amount': 0,
                    'description': '',
                },
                {
                    'account_id': None,
                    'account_name': '',
                    'debit_amount': 0,
                    'credit_amount': 0,
                    'description': '',
                },
            ]
        }
