"""Pricing agent implementation for handling financial queries"""

import re
from typing import Dict, Any
from agents.base_agent import SimplifiedAgent
from context.conversation_context import ConversationContext
from tools.calculateincentivetool import CalculateIncentiveTool


class PricingAgent(SimplifiedAgent):
    """Handles pricing related queries"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext, incentive_tool: CalculateIncentiveTool):
        super().__init__(
            name="PricingAgent",
            system_message="""
You are the PricingAgent. You assist users in calculating dealer compensation, GAP refund, or funding packet address.

🚨 CRITICAL INSTRUCTION:
You MUST end EVERY response with [final_answer]. This is required for proper conversation termination.

Behavior Instructions:
1. Always start by asking the user for the dealer name (for GAP/compensation) or RBC number (for funding) if not already provided.
2. Once required info is present, call the appropriate tool method:
    - get_gap_refund(dealer_name)
    - get_funding_address(rbc_number)
    - run(dealer_name) for compensation
3. After receiving the result, share it with the user.
4. ALWAYS end EVERY message with [final_answer].
5. Remember values from earlier in the conversation unless updated.
""",
            llm_config=llm_config,
            context=context
        )

        self.incentive_tool = incentive_tool
        if not hasattr(self.context, "intent"):
            self.context.intent = None

    def generate_response(self, message: str) -> str:
        self._extract_info_from_message(message)
        self._infer_intent(message)
        message_lower = message.lower()
        print(message_lower)

        try:
            intent = getattr(self.context, "intent", None)

            # GAP refund flow
            if intent == "gap_refund":
                if self.context.dealer_name is None:
                    return "To get the GAP refund, please provide the Dealer Name. [user_input_needed]"
                dealer_name = self.context.dealer_name
                refund = self.incentive_tool.get_gap_refund(dealer_name)
                response = f"The GAP refund amount for {dealer_name} is ${refund}.[final_answer]"
                self._clear_context_after_completion()
                return response

            # Funding address flow
            if intent == "funding_address":
                if self.context.rbc_number is None:
                    return "To get the funding address, please provide the RBC number. [user_input_needed]"
                rbc_number = self.context.rbc_number
                address = self.incentive_tool.get_funding_address(rbc_number)
                response = f"The mailing address for RBC number {rbc_number} is: {address}.[final_answer]"
                self._clear_context_after_completion()
                return response

            # Dealer incentive flow
            if intent == "dealer_incentive":
                if self.context.dealer_name is None:
                    return "Could you please provide the Dealer Name? [user_input_needed]"
                dealer_name = self.context.dealer_name
                incentive = self.incentive_tool.run(dealer_name)
                response = f"The dealer incentive for the sale is ${incentive}.[final_answer]"
                self._clear_context_after_completion()
                return response

            # Handle partial context inputs: try to re-trigger previous intent if data is now available
            if self.context.intent is None:
                if self.context.rbc_number is not None:
                    self.context.intent = "funding_address"
                    return self.generate_response("funding follow-up")
                elif self.context.dealer_name is not None:
                    last_msgs = self.context.get_recent_messages(2)
                    if any("gap" in msg["message"].lower() for msg in last_msgs if msg["sender"] == "user"):
                        self.context.intent = "gap_refund"
                    else:
                        self.context.intent = "dealer_incentive"
                    return self.generate_response("dealer follow-up")

            # No valid intent available
            return "Can you please clarify your request (e.g., GAP refund, funding address, or dealer incentive)? [user_input_needed]"

        except Exception as e:
            return f"Sorry, I encountered an error while processing the request: {str(e)}"

    def _clear_context_after_completion(self):
        self.context.intent = None
        self.context.rbc_number = None
        self.context.dealer_name = None

    def _extract_info_from_message(self, message: str) -> None:
        super()._extract_info_from_message(message)
        message_lower = message.lower()
        print(f"Pricing Agent: _extract_info_from_message : Message is {message}")

        # Dealer name patterns
        dealer_patterns = [
            r"dealer(?:\s+name)?\s+(?:is|=|:)\s+([A-Za-z0-9\s]+)",
            r"the dealer(?:\s+name)?\s+(?:is|=|:)\s+([A-Za-z0-9\s]+)",
            r"^(prestige motors|groupon automotive|sonic automotive|lithium motors|bmw|mercedes|chevrolet)$",
            r"(?:i\s+(?:choose|select|want|pick)\s+)(prestige motors|groupon automotive|sonic automotive|lithium motors)",
            r"(tesla|ford|toyota|honda|bmw|mercedes|chevrolet)(?:\s+please)",
            r"(?:it's|its|is)\s+(prestige motors|groupon automotive|sonic automotive|lithium motors)"
        ]

        for pattern in dealer_patterns:
            dealer_match = re.search(pattern, message_lower)
            if dealer_match:
                dealer_name = dealer_match.group(1).strip()
                dealer_name = ' '.join(word.capitalize() for word in dealer_name.split())
                self.context.dealer_name = dealer_name
                print(f"Dealer name extracted: {dealer_name} using pattern: {pattern}")
                break

        # RBC number extraction (e.g., RBC123 or rbc 123)
        rbc_match = re.search(r"\brbc[\s:.-]?(\d{3,6})\b", message_lower)
        if rbc_match:
            self.context.rbc_number = f"RBC{rbc_match.group(1)}"
            print(f"Extracted RBC number: {self.context.rbc_number}")
        else:
            # If funding intent, treat any 3-6 digit number as RBC
            numeric_match = re.search(r"\b(\d{3,6})\b", message_lower)
            if numeric_match and getattr(self.context, "intent", None) == "funding_address":
                self.context.rbc_number = f"RBC{numeric_match.group(1)}"
                print(f"Inferred RBC number from plain digits: {self.context.rbc_number}")

        # APR extraction
        apr_match = re.search(r"(?:contract apr|apr|interest)(?:\s+is|\s*[:=])?\s*(\d+\.?\d*)", message_lower)
        if apr_match:
            self.context.contract_apr = float(apr_match.group(1))

        # Buy rate extraction
        buy_rate_match = re.search(r"(?:buy rate|buy|rate)(?:\s+is|\s*[:=])?\s*(\d+\.?\d*)", message_lower)
        if buy_rate_match and "apr" not in message_lower[buy_rate_match.start() - 5:buy_rate_match.start()]:
            self.context.buy_rate = float(buy_rate_match.group(1))

    def _infer_intent(self, message: str) -> None:
        message_lower = message.lower()
        inferred = None
        if "gap refund" in message_lower or ("gap" in message_lower and "refund" in message_lower):
            inferred = "gap_refund"
        elif any(kw in message_lower for kw in [
            "funding", 
            "rbc", 
            "send paper contract", 
            "mailing address", 
            "funding packet", 
            "packet", 
            "send contract",
            "where should i send",
            "address to send",
            "where do i send",
            "funding address"
        ]):
            inferred = "funding_address"
        elif "compensation" in message_lower or "dealer incentive" in message_lower or "incentive" in message_lower:
            inferred = "dealer_incentive"

        if inferred:
            self.context.intent = inferred
        print(f"Inferred intent: {self.context.intent}")