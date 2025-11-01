"""
Conversation Skill - Intelligent natural language conversation using Gemini
Handles greetings, help requests, explanations, and general ERP questions
"""

import logging
from typing import List

import google.generativeai as genai

from apps.ai_companion.models import AIConfiguration, AIMessage
from apps.ai_companion.services.api_key_manager import APIKeyManager
from .base import BaseSkill, SkillContext, SkillResponse, MemoryRecord

logger = logging.getLogger(__name__)


class ConversationSkill(BaseSkill):
    """
    Handles general conversation, help, and explanations.
    Uses Gemini AI for intelligent, context-aware responses.
    """

    name = "conversation"
    description = "Handles general conversation, greetings, help requests, and ERP explanations"
    priority = 50  # Lower priority than specific skills

    def can_handle(self, message: str, context: SkillContext) -> bool:
        """
        Handles general conversation, greetings, and help requests.
        Falls back to this if no other skill matches.
        """
        lowered = message.lower().strip()

        # Greetings
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        if any(lowered.startswith(greet) for greet in greetings):
            return True

        # Help requests
        if any(word in lowered for word in ["help", "how to", "how do i", "what is", "explain"]):
            return True

        # Questions
        if lowered.endswith("?"):
            return True

        # Default fallback
        return False

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        """Handle conversation using Gemini AI"""

        try:
            # Check if AI is enabled
            config = AIConfiguration.get_config()
            if not config.ai_assistant_enabled:
                return SkillResponse(
                    message="AI assistant is currently disabled. Please contact your administrator.",
                    intent="error",
                    confidence=1.0
                )

            # Build context-aware prompt
            prompt = self._build_conversation_prompt(message, context)

            # Call Gemini
            response_text = self._call_gemini(prompt, context)

            # Extract memory if any
            memory_updates = self._extract_memory_from_response(response_text, context)

            return SkillResponse(
                message=response_text,
                intent="conversation",
                confidence=0.85,
                memory_updates=memory_updates
            )

        except Exception as e:
            logger.exception(f"Conversation skill error: {e}")
            return self._fallback_response(message)

    def _build_conversation_prompt(self, message: str, context: SkillContext) -> str:
        """Build comprehensive prompt for Gemini"""

        user_name = context.user.get_full_name() if context.user else "User"
        company_name = context.company.name if context.company else "your company"

        # Format conversation history
        history_text = self._format_history(context.history)

        # Get user preferences
        preferences = context.long_term
        pref_text = self._format_preferences(preferences)

        # Current context
        current_page = context.current_page or "unknown"
        current_module = context.module or "unknown"

        prompt = f"""You are a helpful AI assistant for Twist ERP, an enterprise resource planning system.

**Your Role:**
- Help users navigate and understand the ERP system
- Answer questions about business processes (procurement, finance, inventory, sales, HR, etc.)
- Explain ERP concepts in simple terms
- Guide users on how to perform tasks
- Be friendly, concise, and professional

**Current Context:**
- User: {user_name}
- Company: {company_name}
- Current Page: {current_page}
- Current Module: {current_module}

**Conversation History:**
{history_text}

**User Preferences:**
{pref_text}

**ERP Modules Available:**
1. **Procurement** - Purchase orders, suppliers, GRN (Goods Receipt Note)
2. **Finance** - Accounts, journal entries, AR (Accounts Receivable), AP (Accounts Payable), banking
3. **Inventory** - Stock management, warehouses, stock movements
4. **Sales** - Sales orders, customers, invoicing
5. **Production** - Work orders, BOM (Bill of Materials), manufacturing
6. **HR** - Employees, payroll, attendance, leave management
7. **Assets** - Asset management, depreciation, maintenance
8. **Projects** - Project tracking, tasks, budgets

**Important Guidelines:**
- Keep responses concise (2-4 sentences for simple queries, more for complex explanations)
- If asked about specific data ("show me POs", "what's my cash balance"), tell them you can help with that and suggest they use the data query feature
- If asked to perform actions ("approve PO 123"), explain you can help prepare that action but they need to confirm it
- Use business-friendly language, avoid technical jargon unless necessary
- If you're not sure, be honest and suggest alternatives

**User Message:**
"{message}"

**Your Response:**
Respond naturally and helpfully. Do not include any preamble like "As an AI assistant" - just answer directly."""

        return prompt

    def _format_history(self, history: List[AIMessage]) -> str:
        """Format conversation history"""
        if not history:
            return "(No recent conversation)"

        lines = []
        for msg in history[-10:]:  # Last 10 messages
            role = msg.role.capitalize()
            content = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def _format_preferences(self, preferences: dict) -> str:
        """Format user preferences"""
        if not preferences:
            return "(No preferences set)"

        lines = []
        for key, value in preferences.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "(No preferences set)"

    def _call_gemini(self, prompt: str, context: SkillContext) -> str:
        """Call Gemini API with automatic key rotation"""

        config = AIConfiguration.get_config()

        def process_with_key(api_key, key_obj):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=config.gemini_model,
                generation_config={
                    "temperature": config.temperature,
                    "max_output_tokens": min(config.max_tokens, 1024),  # Limit for conversation
                }
            )
            response = model.generate_content(prompt)
            return response.text

        result = APIKeyManager.process_with_retry(
            operation_func=process_with_key,
            operation_name="conversation",
            max_retries=config.max_retries,
            user=context.user,
            company=context.company
        )

        if not result:
            raise Exception("No API key available for conversation")

        return result

    def _extract_memory_from_response(self, response: str, context: SkillContext) -> List[MemoryRecord]:
        """
        Extract any preferences or facts that should be remembered.
        For now, this is a placeholder. In the future, we could parse the conversation
        for statements like "remember that I prefer..." or "my default warehouse is..."
        """
        # TODO: Implement intelligent memory extraction
        return []

    def _fallback_response(self, message: str) -> SkillResponse:
        """Fallback response when Gemini fails"""
        lowered = message.lower().strip()

        # Handle greetings
        if any(lowered.startswith(greet) for greet in ["hi", "hello", "hey"]):
            return SkillResponse(
                message=f"Hello! I'm your Twist ERP assistant. How can I help you today?",
                intent="greeting",
                confidence=0.9
            )

        # Handle help
        if "help" in lowered:
            return SkillResponse(
                message=(
                    "I can help you with:\n"
                    "- Answering questions about ERP processes\n"
                    "- Querying data (purchase orders, invoices, stock levels, etc.)\n"
                    "- Guiding you through workflows\n"
                    "- Explaining business concepts\n\n"
                    "What would you like to know?"
                ),
                intent="help",
                confidence=0.9
            )

        # Default
        return SkillResponse(
            message="I'm here to help! Could you please rephrase your question or tell me what you'd like to do?",
            intent="fallback",
            confidence=0.5
        )
