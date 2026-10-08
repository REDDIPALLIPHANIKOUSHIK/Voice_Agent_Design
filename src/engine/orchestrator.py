"""
Conversation Orchestrator for Home Credit LAP AI Voice Agent.
Implements the core state-machine algorithm:
Extract First -> Validate Second -> Update State Third -> Ask First Missing Question Fourth.
"""

from typing import Tuple, Optional, Dict, Any
from src.engine.models import (
    QualificationState,
    CallStage,
    ChecklistItem,
    ExtractedFacts,
)
from src.engine.rules import (
    evaluate_property_type,
    evaluate_ownership,
    evaluate_documents,
    evaluate_loan_amount,
    evaluate_occupation,
    evaluate_income_mode,
    evaluate_tenure,
    evaluate_transfer_condition,
    evaluate_overall_eligibility,
    MAX_LOAN_AMOUNT,
)
from src.engine.extractor import extract_facts

CHECKLIST_SEQUENCE = [
    ChecklistItem.PROPERTY_TYPE,
    ChecklistItem.OWNERSHIP_STATUS,
    ChecklistItem.DOCUMENTS_AVAILABLE,
    ChecklistItem.LOAN_AMOUNT,
    ChecklistItem.OCCUPATION_INCOME_MODE,
    ChecklistItem.MARKET_VALUE,
    ChecklistItem.TENURE_YEARS,
]

QUESTIONS_EN = {
    ChecklistItem.PROPERTY_TYPE: "Could you please confirm if your property is Residential (such as a house or flat), Commercial (a shop or office), or Industrial (a factory)?",
    ChecklistItem.OWNERSHIP_STATUS: "Are you the sole owner of this property, or is it jointly owned with family members or partners?",
    ChecklistItem.DOCUMENTS_AVAILABLE: "Do you have the original property documents available for verification?",
    ChecklistItem.LOAN_AMOUNT: "How much loan amount are you looking to borrow against your property?",
    ChecklistItem.OCCUPATION_INCOME_MODE: "Could you share your occupation—whether you are Salaried or Self-employed—and whether your monthly income is received in a bank account or in cash?",
    ChecklistItem.MARKET_VALUE: "What is your approximate estimate of the current market value of your property?",
    ChecklistItem.TENURE_YEARS: "Over how many years would you like to repay the loan? We offer flexible repayment tenures between 3 and 15 years.",
}

QUESTIONS_HI = {
    ChecklistItem.PROPERTY_TYPE: "क्या आप बता सकते हैं कि आपकी संपत्ति आवासीय (घर या फ्लैट), व्यावसायिक (दुकान या कार्यालय), या औद्योगिक (फैक्ट्री) है?",
    ChecklistItem.OWNERSHIP_STATUS: "क्या आप इस संपत्ति के एकमात्र मालिक हैं, या यह परिवार या साझेदारों के साथ संयुक्त स्वामित्व में है?",
    ChecklistItem.DOCUMENTS_AVAILABLE: "क्या आपके पास सत्यापन के लिए संपत्ति के मूल (ओरिजिनल) दस्तावेज उपलब्ध हैं?",
    ChecklistItem.LOAN_AMOUNT: "आप अपनी संपत्ति के बदले कितनी ऋण (लोन) राशि लेना चाहते हैं?",
    ChecklistItem.OCCUPATION_INCOME_MODE: "कृपया बताएं कि आप वेतनभोगी (नौकरीपेशा) हैं या स्व-नियोजित (व्यापार), और आपकी आय बैंक खाते में आती है या नकद में?",
    ChecklistItem.MARKET_VALUE: "आपकी संपत्ति का अनुमानित वर्तमान बाजार मूल्य (मार्केट वैल्यू) कितना होगा?",
    ChecklistItem.TENURE_YEARS: "आप कितने वर्षों में यह लोन चुकाना चाहेंगे? हमारे पास 3 से 15 वर्ष तक की अवधि उपलब्ध है।",
}


def get_first_missing_checklist_item(state: QualificationState) -> Optional[ChecklistItem]:
    """
    Identifies the very first unanswered checklist item in the strict sequential order.
    """
    if state.property_type is None:
        return ChecklistItem.PROPERTY_TYPE
    if state.ownership_status is None:
        return ChecklistItem.OWNERSHIP_STATUS
    if state.documents_available is None:
        return ChecklistItem.DOCUMENTS_AVAILABLE
    if state.loan_amount is None:
        return ChecklistItem.LOAN_AMOUNT
    if state.occupation is None or state.income_mode is None:
        return ChecklistItem.OCCUPATION_INCOME_MODE
    if state.market_value is None:
        return ChecklistItem.MARKET_VALUE
    if state.tenure_years is None:
        return ChecklistItem.TENURE_YEARS
    return None


class ConversationOrchestrator:
    def __init__(self, state: Optional[QualificationState] = None, rag_context: Optional[str] = None):
        self.state = state or QualificationState()
        self.rag_context = rag_context

    def generate_initial_greeting(self) -> str:
        """
        Stage A: Greeting and customer identification.
        """
        self.state.call_stage = CallStage.VERIFICATION
        if self.state.language_to_speak.lower() == "hindi":
            return f"नमस्ते, क्या मैं {self.state.customer_name} जी से बात कर रही हूँ? मैं {self.state.agent_name}, {self.state.company_name} से बोल रही हूँ।"
        return f"Hello, may I speak with {self.state.customer_name}? This is {self.state.agent_name} calling from {self.state.company_name}."

    def process_utterance(self, utterance: str) -> Tuple[str, QualificationState]:
        """
        Main decision loop on customer response:
        1. Extract all facts from utterance
        2. Detect corrections & normalize values
        3. Check busy customer flow
        4. Detect transfer intent (existing loan / EMI reduction)
        5. Check confirmation if awaiting capping approval
        6. Apply deterministic business rules & check disqualification
        7. Handle diversions / interruptions (without fabricating data)
        8. Find FIRST unanswered checklist item
        9. Trigger final handoff gate if all 7 questions answered
        """
        if self.state.call_ended:
            msg = "The call has concluded. Thank you for your time."
            return msg, self.state

        current_item = (
            self.state.current_checklist_item.value
            if isinstance(self.state.current_checklist_item, ChecklistItem)
            else self.state.current_checklist_item
        )
        facts: ExtractedFacts = extract_facts(utterance, current_expected_item=current_item)

        is_hindi = self.state.language_to_speak.lower() == "hindi"

        # --- STEP 1: Handle Customer Verification & Busy Check ---
        if self.state.call_stage in [CallStage.GREETING, CallStage.VERIFICATION]:
            # Check busy first
            if facts.customer_busy:
                self.state.customer_busy = True
                self.state.call_stage = CallStage.BUSY_CHECK
                self.state.call_ended = True
                cb_time = facts.callback_time or "a convenient time"
                self.state.callback_time = cb_time
                if is_hindi:
                    return f"बिल्कुल, मैं समझती हूँ। हम आपको {cb_time} पर दोबारा कॉल करेंगे। आपका दिन शुभ हो!", self.state
                return f"Certainly, I understand you are busy right now. We will call you back at {cb_time}. Thank you for your time, and have a good day!", self.state

            # Customer confirms identity
            self.state.customer_verified = True
            self.state.call_stage = CallStage.OFFER_PRESENTATION

            # Offer presentation + first missing question
            offer_text_en = (
                f"Thank you, {self.state.customer_name}. We're reaching out because, as one of our valued customers, "
                f"you may be eligible for a special Loan Against Property offer of up to ₹75 lakh. "
                f"I'd just like to ask a few quick questions to check whether the offer is suitable for you."
            )
            offer_text_hi = (
                f"धन्यवाद {self.state.customer_name} जी। हम आपसे इसलिए संपर्क कर रहे हैं क्योंकि हमारे एक मूल्यवान ग्राहक के रूप में, "
                f"आप ₹75 लाख तक के विशेष लोन अगेंस्ट प्रॉपर्टी (LAP) ऑफर के पात्र हो सकते हैं। "
                f"इसकी पात्रता जांचने के लिए मैं आपसे कुछ बुनियादी प्रश्न पूछना चाहूंगी।"
            )

            # Check if customer already supplied any details in greeting utterance
            self._update_state_with_facts(facts)

            # Check transfer or disqualification if customer immediately blurted facts
            trans_resp = self._check_transfer_condition(facts, is_hindi)
            if trans_resp:
                return trans_resp, self.state

            disq_resp = self._check_immediate_disqualification(is_hindi)
            if disq_resp:
                return disq_resp, self.state

            first_missing = get_first_missing_checklist_item(self.state)
            self.state.current_checklist_item = first_missing
            self.state.call_stage = CallStage.QUALIFICATION

            q_text = QUESTIONS_HI[first_missing] if is_hindi else QUESTIONS_EN[first_missing]
            greeting = offer_text_hi if is_hindi else offer_text_en
            return f"{greeting} {q_text}", self.state

        # --- STEP 2: Handle Busy Customer during qualification ---
        if facts.customer_busy:
            self.state.customer_busy = True
            self.state.call_ended = True
            cb_time = facts.callback_time or "a convenient time"
            self.state.callback_time = cb_time
            if is_hindi:
                return f"बिल्कुल, मैं समझती हूँ। हम आपको {cb_time} पर दोबारा कॉल करेंगे। धन्यवाद!", self.state
            return f"Certainly, I understand. We will schedule a callback for {cb_time}. Thank you for your time!", self.state

        # --- STEP 3: Handle Transfer Intent (Existing Loan / EMI Reduction) ---
        trans_resp = self._check_transfer_condition(facts, is_hindi)
        if trans_resp:
            return trans_resp, self.state

        # --- STEP 4: Handle Awaiting 75L Capping Confirmation ---
        if self.state.awaiting_75l_confirmation:
            if facts.confirmation_answer is True:
                self.state.loan_amount = MAX_LOAN_AMOUNT
                self.state.awaiting_75l_confirmation = False
                # Continue qualification
                first_missing = get_first_missing_checklist_item(self.state)
                self.state.current_checklist_item = first_missing
                if first_missing is None:
                    return self._generate_final_handoff(is_hindi)
                q_text = QUESTIONS_HI[first_missing] if is_hindi else QUESTIONS_EN[first_missing]
                ack = "बहुत बढ़िया, हमने ₹75 लाख की अधिकतम राशि दर्ज कर ली है।" if is_hindi else "Great, we have noted ₹75 lakh as the loan amount."
                return f"{ack} {q_text}", self.state
            elif facts.confirmation_answer is False:
                self.state.call_ended = True
                self.state.awaiting_75l_confirmation = False
                if is_hindi:
                    return "मैं समझती हूँ। चूंकि यह ऑफर केवल ₹75 लाख तक के लिए उपलब्ध है, हम फिलहाल इस आवेदन को आगे नहीं बढ़ा पाएंगे। संपर्क करने के लिए धन्यवाद!", self.state
                return "I completely understand. Since this promotional offer is capped at ₹75 lakh, we will not be able to proceed with a higher amount at this time. Thank you for speaking with us today.", self.state
            else:
                # Clarify capping question
                if is_hindi:
                    return "यह विशेष ऑफर अधिकतम ₹75 लाख तक के लिए है। क्या आप ₹75 लाख के साथ आगे बढ़ना चाहेंगे? कृपया हाँ या ना में बताएं।", self.state
                return "Our current offer is available for up to ₹75 lakh. Would you like to proceed with the maximum eligible amount of ₹75 lakh?", self.state

        # --- STEP 5: Update Internal State with Extracted Facts ---
        self._update_state_with_facts(facts)

        # Check Loan Amount > 75L special rule
        if facts.loan_amount and facts.loan_amount > MAX_LOAN_AMOUNT:
            self.state.original_requested_loan_amount = facts.loan_amount
            self.state.awaiting_75l_confirmation = True
            self.state.call_stage = CallStage.CONFIRM_75L
            if is_hindi:
                return "यह विशेष ऑफर अधिकतम ₹75 लाख तक के लिए उपलब्ध है। क्या आप ₹75 लाख की अधिकतम पात्र राशि के साथ आगे बढ़ना चाहेंगे?", self.state
            return "The current offer is available for up to ₹75 lakh. Would you like to proceed with the maximum eligible amount of ₹75 lakh?", self.state

        # --- STEP 6: Immediate Disqualification Gate ---
        disq_resp = self._check_immediate_disqualification(is_hindi)
        if disq_resp:
            return disq_resp, self.state

        # --- STEP 7: Handle Diversions & Interruptions ---
        prefix_response = ""
        if facts.is_diversion:
            if facts.diversion_topic == "interest_rate":
                prefix_response = (
                    "ब्याज दर के बारे में हमारी वरिष्ठ ऋण विशेषज्ञ योग्यता जांच के बाद आपको सटीक जानकारी देंगे। "
                    if is_hindi
                    else "The exact interest rate will be provided by our senior loan expert after this preliminary qualification. "
                )
            elif facts.diversion_topic == "charges":
                prefix_response = (
                    "प्रोसेसिंग फीस और अन्य शुल्कों की विस्तृत जानकारी हमारे ऋण विशेषज्ञ साझा करेंगे। "
                    if is_hindi
                    else "All processing fees and fee structures will be detailed by our senior loan specialist. "
                )
            # Check RAG context if applicable
            if self.rag_context and not prefix_response:
                prefix_response = f"Regarding your query: {self.rag_context}. "
        elif facts.is_interruption:
            if "what documents" in utterance.lower():
                prefix_response = (
                    "सत्यापन के लिए आपके नाम पर संपत्ति के मूल दस्तावेज (जैसे सेल डीड या रजिस्ट्री) की आवश्यकता होती है। "
                    if is_hindi
                    else "We require original title deeds and registered property documents in your name for verification. "
                )

        # --- STEP 8: Find First Missing Question or Final Handoff ---
        first_missing = get_first_missing_checklist_item(self.state)
        self.state.current_checklist_item = first_missing

        if first_missing is None:
            # All 7 questions answered! Validate overall eligibility
            return self._generate_final_handoff(is_hindi, prefix_response)

        # Ask only the first missing question
        self.state.call_stage = CallStage.QUALIFICATION
        q_text = QUESTIONS_HI[first_missing] if is_hindi else QUESTIONS_EN[first_missing]
        if prefix_response:
            return f"{prefix_response}Now, {q_text}" if not is_hindi else f"{prefix_response}अब, {q_text}", self.state
        return q_text, self.state

    def _update_state_with_facts(self, facts: ExtractedFacts) -> None:
        """
        Stores newly extracted facts into internal state. Never overrides with None.
        """
        if facts.property_type is not None:
            self.state.property_type = facts.property_type
        if facts.ownership_status is not None:
            self.state.ownership_status = facts.ownership_status
        if facts.documents_available is not None:
            self.state.documents_available = facts.documents_available
        if facts.loan_amount is not None:
            self.state.loan_amount = facts.loan_amount
            if self.state.original_requested_loan_amount is None:
                self.state.original_requested_loan_amount = facts.loan_amount
        if facts.occupation is not None:
            self.state.occupation = facts.occupation
        if facts.income_mode is not None:
            self.state.income_mode = facts.income_mode
        if facts.market_value is not None:
            self.state.market_value = facts.market_value
        if facts.tenure_years is not None:
            self.state.tenure_years = facts.tenure_years
        if facts.existing_property_loan is not None:
            self.state.existing_property_loan = facts.existing_property_loan
        if facts.emi_reduction_request is not None:
            self.state.emi_reduction_request = facts.emi_reduction_request

    def _check_transfer_condition(self, facts: ExtractedFacts, is_hindi: bool) -> Optional[str]:
        """
        Evaluates existing loan / EMI reduction transfer logic.
        """
        existing_loan = facts.existing_property_loan or self.state.existing_property_loan
        emi_red = facts.emi_reduction_request or self.state.emi_reduction_request

        transfer_res = evaluate_transfer_condition(existing_loan, emi_red)
        if transfer_res.is_transfer_required:
            self.state.transfer_required = True
            self.state.transfer_reason = transfer_res.transfer_reason
            self.state.call_stage = CallStage.SPECIALIST_TRANSFER
            self.state.call_ended = True
            if is_hindi:
                return (
                    "स्पष्ट करने के लिए धन्यवाद। चूंकि संपत्ति पर पहले से ही एक ऋण चल रहा है, इसलिए इसे हमारे ऋण-स्थानांतरण (लोन ट्रांसफर) "
                    "विशेषज्ञ द्वारा संभाला जाएगा। हमारे विशेषज्ञ जल्द ही आपसे संपर्क करेंगे। अपना समय देने के लिए धन्यवाद।"
                )
            return (
                "Thank you for clarifying. Since you already have an existing loan on the property, "
                "this would need to be handled by our loan-transfer specialist. A specialist will contact you "
                "shortly regarding this. Thank you for your time."
            )
        return None

    def _check_immediate_disqualification(self, is_hindi: bool) -> Optional[str]:
        """
        Evaluates deterministic disqualifications (agricultural, cash income, missing docs, invalid tenure).
        """
        # Property type
        prop_res = evaluate_property_type(self.state.property_type)
        if prop_res.is_disqualified:
            return self._disqualify(prop_res.disqualification_reason, is_hindi)

        # Documents
        doc_res = evaluate_documents(self.state.documents_available)
        if doc_res.is_disqualified:
            return self._disqualify(doc_res.disqualification_reason, is_hindi)

        # Income mode
        inc_res = evaluate_income_mode(self.state.income_mode)
        if inc_res.is_disqualified:
            return self._disqualify(inc_res.disqualification_reason, is_hindi)

        # Tenure
        ten_res = evaluate_tenure(self.state.tenure_years)
        if ten_res.is_disqualified:
            return self._disqualify(ten_res.disqualification_reason, is_hindi)

        return None

    def _disqualify(self, reason: Optional[str], is_hindi: bool) -> str:
        self.state.disqualified = True
        self.state.disqualification_reason = reason
        self.state.call_stage = CallStage.DISQUALIFIED
        self.state.call_ended = True

        if is_hindi:
            return (
                f"जानकारी साझा करने के लिए धन्यवाद। दुर्भाग्य से, आप इस समय इस विशिष्ट ऑफर के मानदंडों को पूरा नहीं करते हैं "
                f"क्योंकि {reason or 'आवश्यक शर्तें पूरी नहीं होती हैं'}। भविष्य में अन्य अवसरों के लिए हम आपसे संपर्क करेंगे। आपका दिन शुभ हो।"
            )
        return (
            f"Thank you for sharing that information. Unfortunately, based on our lending criteria, "
            f"you do not meet the eligibility requirements for this specific offer at this time ({reason or 'criteria not met'}). "
            f"We truly appreciate your time speaking with us today. Have a wonderful day."
        )

    def _generate_final_handoff(self, is_hindi: bool, prefix: str = "") -> Tuple[str, QualificationState]:
        """
        Gate 22: Final handoff triggered ONLY after ALL 7 items are answered and criteria are met.
        """
        self.state.handoff_required = True
        self.state.call_stage = CallStage.HANDOFF
        self.state.call_ended = True

        if is_hindi:
            text = (
                f"{prefix}सभी विवरण साझा करने के लिए धन्यवाद। प्रारंभिक मूल्यांकन के आधार पर, आप हमारी पात्रता शर्तों को पूरा करते हैं। "
                f"हमारे एक वरिष्ठ ऋण विशेषज्ञ (Senior Loan Expert) जल्द ही आपको कॉल करेंगे ताकि आगे की प्रक्रिया और सटीक ब्याज दरों पर चर्चा की जा सके। "
                f"होम क्रेडिट के साथ जुड़ने के लिए धन्यवाद!"
            )
        else:
            text = (
                f"{prefix}Thank you for providing all the details. Based on our preliminary check, you successfully meet our eligibility criteria! "
                f"A senior loan expert will contact you shortly to discuss the next steps and provide the exact interest rate. "
                f"Thank you for your time, and have a great day!"
            )
        return text.strip(), self.state
