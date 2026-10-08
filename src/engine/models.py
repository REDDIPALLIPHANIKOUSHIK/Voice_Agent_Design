"""
Data models and state representations for the Home Credit LAP AI Voice Agent.
Strongly typed using Pydantic v2.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"


class OwnershipStatus(str, Enum):
    SOLE = "sole"
    JOINT = "joint"


class DocumentStatus(str, Enum):
    ORIGINAL = "original"
    PHOTOCOPY = "photocopy"
    MISSING = "missing"


class Occupation(str, Enum):
    SALARIED = "salaried"
    SELF_EMPLOYED = "self-employed"


class IncomeMode(str, Enum):
    BANK = "bank"
    CASH = "cash"


class ChecklistItem(str, Enum):
    PROPERTY_TYPE = "property_type"
    OWNERSHIP_STATUS = "ownership_status"
    DOCUMENTS_AVAILABLE = "documents_available"
    LOAN_AMOUNT = "loan_amount"
    OCCUPATION_INCOME_MODE = "occupation_income_mode"
    MARKET_VALUE = "market_value"
    TENURE_YEARS = "tenure_years"


class CallStage(str, Enum):
    GREETING = "greeting"
    VERIFICATION = "verification"
    BUSY_CHECK = "busy_check"
    OFFER_PRESENTATION = "offer_presentation"
    QUALIFICATION = "qualification"
    CONFIRM_75L = "confirm_75l"
    SPECIALIST_TRANSFER = "specialist_transfer"
    DISQUALIFIED = "disqualified"
    HANDOFF = "handoff"
    CALL_ENDED = "call_ended"


class RuleEvaluationResult(BaseModel):
    is_eligible: bool
    is_disqualified: bool = False
    disqualification_reason: Optional[str] = None
    is_transfer_required: bool = False
    transfer_reason: Optional[str] = None
    needs_capping_confirmation: bool = False
    details: Optional[str] = None


class ExtractedFacts(BaseModel):
    customer_verified: Optional[bool] = None
    customer_busy: Optional[bool] = None
    callback_time: Optional[str] = None
    property_type: Optional[str] = None
    ownership_status: Optional[str] = None
    documents_available: Optional[str] = None
    loan_amount: Optional[int] = None
    occupation: Optional[str] = None
    income_mode: Optional[str] = None
    market_value: Optional[int] = None
    tenure_years: Optional[int] = None
    existing_property_loan: Optional[bool] = None
    emi_reduction_request: Optional[bool] = None
    is_diversion: bool = False
    diversion_topic: Optional[str] = None
    is_interruption: bool = False
    interruption_query: Optional[str] = None
    confirmation_answer: Optional[bool] = None  # for yes/no capping confirmation


class QualificationState(BaseModel):
    # Customer verification and availability
    customer_verified: Optional[bool] = None
    customer_busy: Optional[bool] = None
    callback_time: Optional[str] = None

    # 7 Core Eligibility Data Points
    property_type: Optional[str] = None
    ownership_status: Optional[str] = None
    documents_available: Optional[str] = None
    loan_amount: Optional[int] = None
    original_requested_loan_amount: Optional[int] = None
    occupation: Optional[str] = None
    income_mode: Optional[str] = None
    market_value: Optional[int] = None
    tenure_years: Optional[int] = None

    # Existing loan / EMI transfer conditions
    existing_property_loan: Optional[bool] = None
    emi_reduction_request: Optional[bool] = None

    # Decision flags
    transfer_required: bool = False
    transfer_reason: Optional[str] = None
    disqualified: bool = False
    disqualification_reason: Optional[str] = None
    awaiting_75l_confirmation: bool = False

    # Progression flags
    current_checklist_item: Optional[str] = None
    handoff_required: bool = False
    call_ended: bool = False
    call_stage: CallStage = CallStage.GREETING

    # Context / Configuration
    company_name: str = "Home Credit"
    customer_name: str = "Rahul Sharma"
    agent_name: str = "Ananya"
    agent_gender: str = "female"
    language_to_speak: str = "English"

    def get_answered_items_count(self) -> int:
        count = 0
        if self.property_type is not None:
            count += 1
        if self.ownership_status is not None:
            count += 1
        if self.documents_available is not None:
            count += 1
        if self.loan_amount is not None:
            count += 1
        if self.occupation is not None and self.income_mode is not None:
            count += 1
        if self.market_value is not None:
            count += 1
        if self.tenure_years is not None:
            count += 1
        return count

    def is_all_seven_answered(self) -> bool:
        return (
            self.property_type is not None
            and self.ownership_status is not None
            and self.documents_available is not None
            and self.loan_amount is not None
            and self.occupation is not None
            and self.income_mode is not None
            and self.market_value is not None
            and self.tenure_years is not None
        )


class UtteranceLog(BaseModel):
    speaker: str  # "agent" or "customer"
    text: str
    timestamp: str
    extracted_facts: Optional[Dict[str, Any]] = None
    stage: Optional[str] = None


class CallSession(BaseModel):
    call_id: str
    start_time: str
    state: QualificationState = Field(default_factory=QualificationState)
    transcript: List[UtteranceLog] = Field(default_factory=list)
    rag_context: Optional[str] = None
