"""
Data Query Skill - RBAC-aware cross-module data querying
Handles user requests for data across Finance, Procurement, Inventory, etc.
"""

import logging
import json
from typing import Dict, Any

import google.generativeai as genai

from apps.ai_companion.models import AIConfiguration
from apps.ai_companion.services.api_key_manager import APIKeyManager
from apps.ai_companion.services.data_query_layer import DataQueryLayer
from .base import BaseSkill, SkillContext, SkillResponse

logger = logging.getLogger(__name__)


class DataQuerySkill(BaseSkill):
    """
    Handles data queries across all ERP modules.
    Uses DataQueryLayer for RBAC-aware access.
    """

    name = "data_query"
    description = "Handles data queries - purchase orders, invoices, cash balance, stock levels, etc."
    priority = 20  # High priority for data queries

    def can_handle(self, message: str, context: SkillContext) -> bool:
        """Detect data query requests"""
        lowered = message.lower()

        # Query keywords
        query_keywords = [
            "show", "list", "get", "find", "what's", "whats", "how much", "how many",
            "pending", "overdue", "balance", "total", "summary", "status of"
        ]

        # Data entities
        data_entities = [
            "po", "purchase order", "so", "sales order", "invoice", "bill",
            "cash", "balance", "ar", "ap", "receivable", "payable",
            "stock", "inventory", "item", "warehouse", "approval"
        ]

        has_query_keyword = any(keyword in lowered for keyword in query_keywords)
        has_data_entity = any(entity in lowered for entity in data_entities)

        return has_query_keyword and has_data_entity

    def handle(self, message: str, context: SkillContext) -> SkillResponse:
        """Handle data query request"""

        try:
            # Initialize query layer
            query_layer = DataQueryLayer(user=context.user, company=context.company)

            # Use Gemini to understand what data is needed
            query_intent = self._parse_query_intent(message, context)

            # Execute query
            result = self._execute_query(query_layer, query_intent)

            # Format response
            response_message = self._format_response(result, query_intent)

            return SkillResponse(
                message=response_message,
                intent="data_query",
                confidence=0.85,
                sources=[{
                    "type": "data_query",
                    "query_type": query_intent.get("query_type"),
                    "filters": query_intent.get("filters", {}),
                }]
            )

        except Exception as e:
            logger.exception(f"Data query skill error: {e}")
            return SkillResponse(
                message=f"Sorry, I encountered an error while querying data: {str(e)}",
                intent="error",
                confidence=0.5
            )

    def _parse_query_intent(self, message: str, context: SkillContext) -> Dict[str, Any]:
        """
        Use Gemini to understand what data the user wants and extract filters.
        """
        prompt = f"""You are analyzing a data query request for an ERP system.

**Available Queries:**
1. **purchase_orders** - Get purchase orders
   - Filters: status (DRAFT/PENDING_APPROVAL/APPROVED), amount_min, amount_max, supplier_id, overdue (bool), limit

2. **pending_approvals** - Get pending workflow approvals for user
   - No filters needed

3. **cash_balance** - Get cash balance across all bank accounts
   - No filters needed

4. **ar_aging** - Get accounts receivable aging
   - Filters: buckets (list of days, e.g., [30, 60, 90])

5. **ap_aging** - Get accounts payable aging
   - Filters: buckets (list of days)

6. **stock_levels** - Get inventory stock levels
   - Filters: below_reorder (bool), item_id, warehouse_id, limit

7. **cash_flow_analysis** - Analyze cash flow
   - Filters: days (number of days to analyze, default 30)

8. **dashboard_summary** - Get high-level summary across modules
   - No filters needed

**User Request:**
"{message}"

Analyze this request and return a JSON object:
{{
  "query_type": "one_of_the_above",
  "filters": {{"filter_name": "filter_value"}},
  "confidence": 0.0-1.0
}}

Examples:
- "Show me pending POs above 10000" -> {{"query_type": "purchase_orders", "filters": {{"status": "PENDING_APPROVAL", "amount_min": 10000}}, "confidence": 0.9}}
- "What's my cash balance?" -> {{"query_type": "cash_balance", "filters": {{}}, "confidence": 0.95}}
- "Show AR aging" -> {{"query_type": "ar_aging", "filters": {{}}, "confidence": 0.9}}
- "Items below reorder level" -> {{"query_type": "stock_levels", "filters": {{"below_reorder": true}}, "confidence": 0.85}}

Return ONLY valid JSON, no markdown."""

        # Call Gemini
        config = AIConfiguration.get_config()

        def process_with_key(api_key, key_obj):
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=config.gemini_model,
                generation_config={
                    "temperature": 0.3,  # Low temperature for consistent parsing
                    "max_output_tokens": 512,
                }
            )
            response = model.generate_content(prompt)
            return response.text

        result = APIKeyManager.process_with_retry(
            operation_func=process_with_key,
            operation_name="data_query_parsing",
            max_retries=config.max_retries,
            user=context.user,
            company=context.company
        )

        if not result:
            # Fallback to simple parsing
            return self._simple_query_parse(message)

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
            logger.error(f"Failed to parse query intent JSON: {result}")
            return self._simple_query_parse(message)

    def _simple_query_parse(self, message: str) -> Dict[str, Any]:
        """Simple fallback query parsing without Gemini"""
        lowered = message.lower()

        if "cash" in lowered or "balance" in lowered:
            return {"query_type": "cash_balance", "filters": {}, "confidence": 0.7}
        elif "pending" in lowered and ("po" in lowered or "purchase" in lowered):
            return {"query_type": "purchase_orders", "filters": {"status": "PENDING_APPROVAL"}, "confidence": 0.7}
        elif "approval" in lowered:
            return {"query_type": "pending_approvals", "filters": {}, "confidence": 0.7}
        elif "ar" in lowered or "receivable" in lowered:
            return {"query_type": "ar_aging", "filters": {}, "confidence": 0.7}
        elif "ap" in lowered or "payable" in lowered:
            return {"query_type": "ap_aging", "filters": {}, "confidence": 0.7}
        elif "stock" in lowered or "inventory" in lowered:
            return {"query_type": "stock_levels", "filters": {}, "confidence": 0.7}
        else:
            return {"query_type": "dashboard_summary", "filters": {}, "confidence": 0.5}

    def _execute_query(self, query_layer: DataQueryLayer, query_intent: Dict[str, Any]):
        """Execute the appropriate query"""
        query_type = query_intent.get("query_type")
        filters = query_intent.get("filters", {})

        query_methods = {
            "purchase_orders": query_layer.get_purchase_orders,
            "pending_approvals": query_layer.get_pending_approvals,
            "cash_balance": query_layer.get_cash_balance,
            "ar_aging": query_layer.get_ar_aging,
            "ap_aging": query_layer.get_ap_aging,
            "stock_levels": query_layer.get_stock_levels,
            "cash_flow_analysis": query_layer.analyze_cash_flow,
            "dashboard_summary": query_layer.get_dashboard_summary,
        }

        method = query_methods.get(query_type)
        if not method:
            raise ValueError(f"Unknown query type: {query_type}")

        return method(**filters)

    def _format_response(self, result, query_intent: Dict[str, Any]) -> str:
        """Format query result into human-readable response"""

        if not result.success:
            return f"Oops! {result.message}"

        query_type = query_intent.get("query_type")

        # Format based on query type
        if query_type == "purchase_orders":
            return self._format_po_response(result)
        elif query_type == "pending_approvals":
            return self._format_approvals_response(result)
        elif query_type == "cash_balance":
            return self._format_cash_response(result)
        elif query_type == "ar_aging":
            return self._format_ar_aging_response(result)
        elif query_type == "ap_aging":
            return self._format_ap_aging_response(result)
        elif query_type == "stock_levels":
            return self._format_stock_response(result)
        elif query_type == "cash_flow_analysis":
            return self._format_cash_analysis_response(result)
        elif query_type == "dashboard_summary":
            return self._format_dashboard_response(result)
        else:
            return f"{result.message}"

    def _format_po_response(self, result) -> str:
        """Format purchase orders response"""
        if not result.data:
            return "No purchase orders found matching your criteria."

        lines = [f"**Found {len(result.data)} Purchase Order(s):**\n"]
        for po in result.data[:10]:  # Show max 10
            lines.append(
                f"- **#{po.get('po_number')}** - {po.get('supplier__name', 'N/A')} "
                f"- {po.get('status')} - {po.get('total_amount', 0):,.2f}"
            )

        if len(result.data) > 10:
            lines.append(f"\n_...and {len(result.data) - 10} more_")

        return "\n".join(lines)

    def _format_approvals_response(self, result) -> str:
        """Format pending approvals response"""
        if not result.data:
            return "You have no pending approvals."

        lines = [f"**You have {len(result.data)} pending approval(s):**\n"]
        for approval in result.data[:10]:
            lines.append(
                f"- **{approval.get('workflow')}** - {approval.get('task_name')} "
                f"- {approval.get('entity_type')}"
            )

        return "\n".join(lines)

    def _format_cash_response(self, result) -> str:
        """Format cash balance response"""
        data = result.data
        total = data.get("total_balance", 0)
        accounts = data.get("accounts", [])

        lines = [f"**Total Cash Balance: {total:,.2f}**\n"]
        if accounts:
            lines.append("**By Account:**")
            for acc in accounts:
                lines.append(
                    f"- {acc.get('account_name')} ({acc.get('bank_name')}): "
                    f"{acc.get('current_balance', 0):,.2f}"
                )

        return "\n".join(lines)

    def _format_ar_aging_response(self, result) -> str:
        """Format AR aging response"""
        data = result.data
        summary = data.get("summary", {})
        total = data.get("total", 0)

        lines = [f"**Total Accounts Receivable: {total:,.2f}**\n"]
        lines.append("**Aging Breakdown:**")
        for bucket, amount in summary.items():
            lines.append(f"- {bucket} days: {amount:,.2f}")

        return "\n".join(lines)

    def _format_ap_aging_response(self, result) -> str:
        """Format AP aging response"""
        data = result.data
        summary = data.get("summary", {})
        total = data.get("total", 0)

        lines = [f"**Total Accounts Payable: {total:,.2f}**\n"]
        lines.append("**Aging Breakdown:**")
        for bucket, amount in summary.items():
            lines.append(f"- {bucket} days: {amount:,.2f}")

        return "\n".join(lines)

    def _format_stock_response(self, result) -> str:
        """Format stock levels response"""
        if not result.data:
            return "No stock records found."

        lines = [f"**Found {len(result.data)} stock record(s):**\n"]
        for stock in result.data[:15]:
            lines.append(
                f"- **{stock.get('item__name')}** ({stock.get('item__code')}) "
                f"- Warehouse: {stock.get('warehouse__name')} "
                f"- Qty: {stock.get('quantity', 0)} "
                f"(Reorder: {stock.get('reorder_level', 0)})"
            )

        return "\n".join(lines)

    def _format_cash_analysis_response(self, result) -> str:
        """Format cash flow analysis response"""
        data = result.data

        lines = [
            f"**Cash Flow Analysis:**\n",
            f"- Current Cash: {data.get('current_cash', 0):,.2f}",
            f"- Expected Inflow: {data.get('expected_inflow', 0):,.2f}",
            f"- Expected Outflow: {data.get('expected_outflow', 0):,.2f}",
            f"- Projected Cash: {data.get('projected_cash', 0):,.2f}",
            f"- Overdue Receivables: {data.get('overdue_receivables', 0):,.2f}",
            f"\n**Insights:**"
        ]

        for insight in data.get('insights', []):
            lines.append(f"- {insight}")

        return "\n".join(lines)

    def _format_dashboard_response(self, result) -> str:
        """Format dashboard summary response"""
        data = result.data

        return f"""**Dashboard Summary:**

- Cash Balance: {data.get('cash_balance', 0):,.2f}
- Accounts Receivable: {data.get('accounts_receivable', 0):,.2f}
- Accounts Payable: {data.get('accounts_payable', 0):,.2f}
- Pending Approvals: {data.get('pending_approvals', 0)}
"""

