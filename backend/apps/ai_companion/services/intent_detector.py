"""
Intelligent Intent Detection using Gemini AI
Understands user intent and extracts structured parameters for action execution
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from django.conf import settings

from apps.ai_companion.models import AIConfiguration
from apps.ai_companion.services.api_key_manager import APIKeyManager

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    """Structured intent extracted from user message"""
    category: str  # query, action, conversation, analysis
    subcategory: str  # e.g., "purchase_order_approval", "cash_analysis"
    confidence: float
    entities: Dict[str, Any]  # extracted parameters
    requires_confirmation: bool
    suggested_skill: str
    natural_response: str  # Human-friendly interpretation


class IntentDetector:
    """
    Uses Gemini AI to understand user intent and extract structured parameters.
    This is the "brain" that routes requests to the right skills.
    """

    def __init__(self, user=None, company=None):
        self.user = user
        self.company = company
        self.config = AIConfiguration.get_config()

    def detect(self, message: str, context: Dict[str, Any] = None) -> Intent:
        """
        Analyze user message and return structured intent.

        Args:
            message: User's natural language input
            context: Additional context (current page, module, history, etc.)

        Returns:
            Intent object with category, entities, and routing information
        """
        context = context or {}

        # Build context-aware prompt
        prompt = self._build_intent_prompt(message, context)

        # Call Gemini to analyze intent
        try:
            result = self._call_gemini(prompt)
            intent_data = self._parse_gemini_response(result)

            return Intent(
                category=intent_data.get("category", "conversation"),
                subcategory=intent_data.get("subcategory", "general"),
                confidence=intent_data.get("confidence", 0.5),
                entities=intent_data.get("entities", {}),
                requires_confirmation=intent_data.get("requires_confirmation", False),
                suggested_skill=intent_data.get("suggested_skill", "conversation"),
                natural_response=intent_data.get("natural_response", ""),
            )
        except Exception as e:
            logger.exception(f"Intent detection failed: {e}")
            # Fallback to basic intent
            return self._fallback_intent(message)

    def _build_intent_prompt(self, message: str, context: Dict[str, Any]) -> str:
        """Build comprehensive prompt for Gemini to understand intent"""

        # Get user and company context
        user_name = self.user.get_full_name() if self.user else "User"
        company_name = self.company.name if self.company else "Unknown Company"
        current_page = context.get("current_page", "unknown")
        current_module = context.get("module", "unknown")

        # Get conversation history
        history = context.get("history", [])
        history_text = self._format_history(history[-5:] if len(history) > 5 else history)

        # Get user preferences
        preferences = context.get("long_term", {})
        pref_text = self._format_preferences(preferences)

        prompt = f"""You are an intelligent ERP assistant for Twist ERP analyzing user intent.

**Current Context:**
- User: {user_name}
- Company: {company_name}
- Current Page: {current_page}
- Current Module: {current_module}

**Recent Conversation:**
{history_text}

**User Preferences:**
{pref_text}

**ERP Capabilities:**
1. **QUERY** - Answer questions about data
   - Subcategories: purchase_orders, sales_orders, inventory, finance, cash_flow, ar_aging, ap_aging, expenses
   - Examples: "Show me pending POs", "What's our cash balance?", "Who owes us money?"

2. **ACTION** - Perform operations
   - Subcategories: approve_purchase_order, create_sales_order, post_invoice, issue_payment, adjust_inventory
   - Examples: "Approve PO #123", "Create SO for Customer ABC", "Pay supplier invoice"
   - IMPORTANT: Actions require confirmation = true

3. **ANALYSIS** - Cross-module analysis and insights
   - Subcategories: cash_analysis, profitability, efficiency, risk_assessment
   - Examples: "Why is cash low?", "Which products are profitable?", "What's blocking approvals?"

4. **CONVERSATION** - General chat and help
   - Subcategories: greeting, help, explanation, clarification
   - Examples: "Hi", "How do I create a PO?", "What does GRN mean?"

**User Message:**
"{message}"

Analyze this message and return a JSON object with:
{{
  "category": "query|action|analysis|conversation",
  "subcategory": "specific_subcategory",
  "confidence": 0.0-1.0,
  "entities": {{
    "extracted_parameters": "values"
  }},
  "requires_confirmation": true/false,
  "suggested_skill": "conversation|data_query|action_executor|analysis",
  "natural_response": "human-friendly interpretation of what user wants"
}}

**Entity Extraction Examples:**
- "Approve PO 123" → {{"po_id": "123", "action": "approve"}}
- "Show pending POs above 10k" → {{"status": "pending", "amount_min": 10000}}
- "Create SO for ABC Corp for 500 units of Item-123" → {{"customer": "ABC Corp", "quantity": 500, "item": "Item-123"}}

**Confirmation Rules:**
- Any financial transaction = requires_confirmation: true
- Any approval/posting = requires_confirmation: true
- Queries/analysis = requires_confirmation: false

Return ONLY valid JSON, no markdown formatting."""

        return prompt

    def _format_history(self, history: List) -> str:
        """Format conversation history for context"""
        if not history:
            return "(No recent conversation)"

        lines = []
        for msg in history:
            role = msg.role.capitalize()
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _format_preferences(self, preferences: Dict[str, Any]) -> str:
        """Format user preferences for context"""
        if not preferences:
            return "(No preferences set)"

        lines = []
        for key, value in preferences.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "(No preferences set)"

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API with automatic key rotation"""

        def process_with_key(api_key, key_obj):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=self.config.gemini_model,
                generation_config={
                    "temperature": 0.3,  # Lower temperature for more consistent JSON
                    "max_output_tokens": 1024,
                }
            )
            response = model.generate_content(prompt)
            return response.text

        result = APIKeyManager.process_with_retry(
            operation_func=process_with_key,
            operation_name="intent_detection",
            max_retries=self.config.max_retries,
            user=self.user,
            company=self.company
        )

        if not result:
            raise Exception("No API key available for intent detection")

        return result

    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini's JSON response"""
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            # Parse JSON
            data = json.loads(text)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}\nResponse: {response_text}")
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            raise

    def _fallback_intent(self, message: str) -> Intent:
        """Simple fallback when Gemini is unavailable"""
        lowered = message.lower()

        # Detect greetings
        if any(word in lowered for word in ["hi", "hello", "hey", "good morning", "good afternoon"]):
            return Intent(
                category="conversation",
                subcategory="greeting",
                confidence=0.9,
                entities={},
                requires_confirmation=False,
                suggested_skill="conversation",
                natural_response="User wants to start a conversation"
            )

        # Detect questions
        if any(word in lowered for word in ["what", "where", "when", "who", "how", "why", "show", "list"]):
            return Intent(
                category="query",
                subcategory="general",
                confidence=0.6,
                entities={},
                requires_confirmation=False,
                suggested_skill="data_query",
                natural_response="User is asking a question"
            )

        # Detect actions
        if any(word in lowered for word in ["approve", "create", "post", "delete", "update", "pay", "issue"]):
            return Intent(
                category="action",
                subcategory="general",
                confidence=0.6,
                entities={},
                requires_confirmation=True,
                suggested_skill="action_executor",
                natural_response="User wants to perform an action"
            )

        # Default to conversation
        return Intent(
            category="conversation",
            subcategory="general",
            confidence=0.5,
            entities={},
            requires_confirmation=False,
            suggested_skill="conversation",
            natural_response="General conversation"
        )
