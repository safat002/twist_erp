"""
Action Execution Skill - Executes ERP operations with confirmation flow
Handles approvals, creating records, posting transactions, etc.
"""

import logging
import json
from typing import Dict, Any, List

import google.generativeai as genai

from apps.ai_companion.models import AIConfiguration
from apps.ai_companion.services.api_key_manager import APIKeyManager
from apps.ai_companion.services.action_executor import ActionExecutor
from .base import BaseSkill, SkillContext, SkillResponse, SkillAction

logger = logging.getLogger(__name__)


class ActionExecutionSkill(BaseSkill):
    """
    Handles ERP action execution with confirmation flow.
    Ensures all actions are safe, audited, and respect RBAC.
    """

    name = "action_execution"
    description = "Executes ERP operations like approving POs, creating SOs, posting transactions"
    priority = 15  # High priority for actions

    def can_handle(self, message: str, context: SkillContext) -> bool:
        """Detect action requests"""
        lowered = message.lower()

        # Don't handle "how to" or "what is" questions - those are for conversation skill
        if any(phrase in lowered for phrase in ["how to", "how do i", "how can i", "what is", "explain", "tell me about", "show me how"]):
            return False

        # Action verbs
        action_verbs = [
            "approve", "reject", "create", "add", "make", "delete", "update", "post", "issue",
            "pay", "send", "cancel", "close", "complete", "submit"
        ]

        # Action targets
        action_targets = [
            "po", "purchase order", "so", "sales order", "invoice", "bill",
            "payment", "voucher", "grn", "stock", "transfer", "customer"
        ]

        has_action_verb = any(verb in lowered for verb in action_verbs)
        has_action_target = any(target in lowered for target in action_targets)

        # Special case: confirmation keywords
        if any(word in lowered for word in ["confirm", "yes", "proceed", "go ahead", "do it"]):
            # Check if there's a pending confirmation in context
            if context.extra.get("pending_confirmation"):
                return True

        return has_action_verb and has_action_target

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        """Handle action execution request"""

        try:
            # Check if this is a confirmation
            if self._is_confirmation(message, context):
                return self._handle_confirmation(message, context)

            # Parse action intent
            action_intent = self._parse_action_intent(message, context)

            # Initialize executor
            executor = ActionExecutor(user=context.user, company=context.company)

            # Prepare action (validation + confirmation request)
            result = executor.prepare_action(
                action_type=action_intent.get("action_type"),
                params=action_intent.get("params", {})
            )

            if not result.success:
                return SkillResponse(
                    message=f"Oops! {result.message}",
                    intent="action_error",
                    confidence=0.9
                )

            if result.requires_confirmation:
                # Return confirmation request
                return SkillResponse(
                    message=f"{result.message}\n\nJust reply with 'confirm' to go ahead, or 'cancel' if you change your mind.",
                    intent="action_confirmation_required",
                    confidence=0.9,
                    actions=[
                        SkillAction(
                            label="Confirm",
                            action="confirm_action",
                            payload={"confirmation_token": result.confirmation_token}
                        ),
                        SkillAction(
                            label="Cancel",
                            action="cancel_action",
                            payload={}
                        )
                    ]
                )
            else:
                # Execute immediately (should not happen for most actions)
                exec_result = executor.execute_confirmed_action(result.confirmation_token)
                return self._format_execution_result(exec_result)

        except Exception as e:
            logger.exception(f"Action execution skill error: {e}")
            return SkillResponse(
                message=f"Uh oh, something went wrong: {str(e)}. Want to try that again?",
                intent="error",
                confidence=0.5
            )

    def _is_confirmation(self, message: str, context: SkillContext) -> bool:
        """Check if this message is confirming a previous action"""
        lowered = message.lower().strip()
        confirmation_words = ["confirm", "yes", "proceed", "go ahead", "do it", "yes do it", "ok", "okay"]

        # Check if user is confirming
        is_confirming = any(word in lowered for word in confirmation_words)

        # Check if there's a pending confirmation in context
        has_pending = "pending_confirmation_token" in context.extra

        return is_confirming and has_pending

    def _handle_confirmation(self, message: str, context: SkillContext) -> SkillResponse:
        """Handle confirmation of a pending action"""
        lowered = message.lower().strip()

        # Check if user is canceling
        if any(word in lowered for word in ["cancel", "no", "abort", "stop", "nevermind"]):
            return SkillResponse(
                message="No problem, I've canceled that action.",
                intent="action_canceled",
                confidence=1.0
            )

        # Get confirmation token from context
        token = context.extra.get("pending_confirmation_token")
        if not token:
            return SkillResponse(
                message="I don't see any pending action to confirm. What would you like me to do?",
                intent="error",
                confidence=0.9
            )

        # Execute the action
        executor = ActionExecutor(user=context.user, company=context.company)
        result = executor.execute_confirmed_action(token)

        return self._format_execution_result(result)

    def _parse_action_intent(self, message: str, context: SkillContext) -> Dict[str, Any]:
        """
        Use Gemini to understand what action user wants to perform.
        """
        prompt = f"""Hey! You're helping me understand what action someone wants to do in an ERP system.

Here's what they can ask me to do:

1. **approve_purchase_order** - Approve a purchase order
   - Needs: po_id (number)
   - Optional: notes (text)

2. **reject_purchase_order** - Reject a purchase order
   - Needs: po_id (number), reason (why they're rejecting it)

3. **create_sales_order** - Create a new sales order
   - Needs: customer_id (number), items (list of stuff)
   - Optional: notes (text)

4. **create_customer** - Create a new customer
   - Optional: name (text), email (text), phone (text)

5. **post_ar_invoice** - Post an invoice to the books
   - Needs: invoice_id (number)

6. **issue_payment** - Pay a supplier
   - Needs: bill_id (number), amount (money), payment_method (how they're paying)

**What they said:**
"{message}"

**Where they are:**
- Page: {context.current_page or 'unknown'}
- Module: {context.module or 'unknown'}

Figure out what they want and give me back JSON like this:
{{
  "action_type": "one_of_the_above",
  "params": {{
    "parameter_name": "extracted_value"
  }},
  "confidence": 0.0-1.0
}}

**Examples:**
- "Approve PO 123" → {{"action_type": "approve_purchase_order", "params": {{"po_id": 123}}, "confidence": 0.95}}
- "Reject purchase order #456 because the price is too high" → {{"action_type": "reject_purchase_order", "params": {{"po_id": 456, "reason": "price is too high"}}, "confidence": 0.9}}
- "Create SO for customer 789" → {{"action_type": "create_sales_order", "params": {{"customer_id": 789}}, "confidence": 0.8}}
- "Make a sales order" → {{"action_type": "create_sales_order", "params": {{}}, "confidence": 0.7}}
- "Create a customer" → {{"action_type": "create_customer", "params": {{}}, "confidence": 0.9}}
- "Add customer named ABC Company" → {{"action_type": "create_customer", "params": {{"name": "ABC Company"}}, "confidence": 0.85}}

**Tips:**
- Pull out ID numbers (they usually come after "PO", "#", "order", etc.)
- If you can't find an ID, that's okay - just set confidence lower
- Grab all the info you can find

Just give me the JSON, nothing else."""

        # Call Gemini
        config = AIConfiguration.get_config()

        def process_with_key(api_key, key_obj):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=config.gemini_model,
                generation_config={
                    "temperature": 0.2,  # Very low temperature for consistent parsing
                    "max_output_tokens": 512,
                }
            )
            response = model.generate_content(prompt)
            return response.text

        result = APIKeyManager.process_with_retry(
            operation_func=process_with_key,
            operation_name="action_parsing",
            max_retries=config.max_retries,
            user=context.user,
            company=context.company
        )

        if not result:
            # Fallback to simple parsing
            return self._simple_action_parse(message)

        # Parse JSON response
        try:
            text = result.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            intent = json.loads(text)
            return intent
        except json.JSONDecodeError:
            logger.error(f"Failed to parse action intent JSON: {result}")
            return self._simple_action_parse(message)

    def _simple_action_parse(self, message: str) -> Dict[str, Any]:
        """Simple fallback action parsing without Gemini"""
        lowered = message.lower()
        import re

        # Try to extract ID numbers
        numbers = re.findall(r'\d+', message)
        first_number = int(numbers[0]) if numbers else None

        if "approve" in lowered and ("po" in lowered or "purchase" in lowered):
            return {
                "action_type": "approve_purchase_order",
                "params": {"po_id": first_number} if first_number else {},
                "confidence": 0.6 if first_number else 0.3
            }
        elif "reject" in lowered and ("po" in lowered or "purchase" in lowered):
            return {
                "action_type": "reject_purchase_order",
                "params": {
                    "po_id": first_number,
                    "reason": "User requested rejection"
                } if first_number else {},
                "confidence": 0.6 if first_number else 0.3
            }
        elif ("create" in lowered or "add" in lowered or "make" in lowered) and ("po" in lowered or "purchase" in lowered):
            return {
                "action_type": "create_purchase_order",
                "params": {"supplier_id": first_number} if first_number else {},
                "confidence": 0.5
            }
        elif ("create" in lowered or "add" in lowered) and ("so" in lowered or "sales" in lowered):
            return {
                "action_type": "create_sales_order",
                "params": {"customer_id": first_number} if first_number else {},
                "confidence": 0.5
            }
        elif ("create" in lowered or "add" in lowered) and ("customer" in lowered):
            return {
                "action_type": "create_customer",
                "params": {},
                "confidence": 0.4
            }
        else:
            return {
                "action_type": "unknown",
                "params": {},
                "confidence": 0.2
            }

    def _format_execution_result(self, result) -> SkillResponse:
        """Format action execution result into response"""
        if result.success:
            return SkillResponse(
                message=f"Done! {result.message}",
                intent="action_success",
                confidence=1.0,
                sources=[{
                    "type": "audit_log",
                    "audit_id": result.audit_id
                }] if result.audit_id else None
            )
        else:
            return SkillResponse(
                message=f"Hmm, that didn't work. {result.message}",
                intent="action_failed",
                confidence=1.0
            )
