"""
Deterministic Business Rule Engine for Home Credit LAP (Loan Against Property) Qualification.
Enforces all business constraints strictly without delegating rule decisions to LLM guesswork.
"""

from typing import Optional, Tuple
from src.engine.models import (
    PropertyType,
    OwnershipStatus,
    DocumentStatus,
    Occupation,
    IncomeMode,
    RuleEvaluationResult,
    QualificationState,
)

MAX_LOAN_AMOUNT = 75_00_000  # 75 Lakhs INR
MIN_TENURE_YEARS = 3
MAX_TENURE_YEARS = 15


def evaluate_property_type(property_type: Optional[str]) -> RuleEvaluationResult:
    """
    Allowed: Residential, Commercial, Industrial.
    Agricultural: Immediately disqualify.
    """
    if property_type is None:
        return RuleEvaluationResult(is_eligible=True)

    norm = property_type.strip().lower()
    if norm in [PropertyType.AGRICULTURAL.value, "farm", "farmland", "kheti", "krishi", "agriculture"]:
        return RuleEvaluationResult(
            is_eligible=False,
            is_disqualified=True,
            disqualification_reason="Agricultural properties are not eligible for this Loan Against Property offer. Only residential, commercial, or industrial properties can be considered.",
        )
    elif norm in [
        PropertyType.RESIDENTIAL.value,
        PropertyType.COMMERCIAL.value,
        PropertyType.INDUSTRIAL.value,
    ]:
        return RuleEvaluationResult(is_eligible=True, details=f"Property type '{norm}' is eligible.")
    else:
        return RuleEvaluationResult(
            is_eligible=False,
            is_disqualified=True,
            disqualification_reason=f"Property type '{property_type}' is not eligible. Only residential, commercial, or industrial properties are accepted.",
        )


def evaluate_ownership(ownership_status: Optional[str]) -> RuleEvaluationResult:
    """
    Allowed: Sole, Joint.
    Both are fully eligible. Joint ownership must NEVER be rejected.
    """
    if ownership_status is None:
        return RuleEvaluationResult(is_eligible=True)

    norm = ownership_status.strip().lower()
    if norm in [OwnershipStatus.SOLE.value, OwnershipStatus.JOINT.value]:
        return RuleEvaluationResult(
            is_eligible=True,
            details=f"Ownership status '{norm}' is eligible.",
        )
    return RuleEvaluationResult(
        is_eligible=True,
        details=f"Ownership recorded: {ownership_status}",
    )


def evaluate_documents(documents_status: Optional[str]) -> RuleEvaluationResult:
    """
    Original property documents must be available for verification.
    Original at home / available -> Eligible.
    Photocopy only / Missing / Lost -> Disqualify.
    """
    if documents_status is None:
        return RuleEvaluationResult(is_eligible=True)

    norm = documents_status.strip().lower()
    if norm == DocumentStatus.ORIGINAL.value:
        return RuleEvaluationResult(
            is_eligible=True,
            details="Original property documents are available.",
        )
    elif norm in [DocumentStatus.PHOTOCOPY.value, DocumentStatus.MISSING.value]:
        return RuleEvaluationResult(
            is_eligible=False,
            is_disqualified=True,
            disqualification_reason="Physical availability of original property documents is mandatory for verification under this offer.",
        )
    return RuleEvaluationResult(is_eligible=True)


def evaluate_loan_amount(amount: Optional[int]) -> RuleEvaluationResult:
    """
    Maximum loan amount is ₹75,00,000 (75 Lakhs).
    If <= 75 Lakhs: eligible.
    If > 75 Lakhs: DO NOT immediately disqualify; prompt to proceed with maximum ₹75 Lakh.
    """
    if amount is None:
        return RuleEvaluationResult(is_eligible=True)

    if amount <= MAX_LOAN_AMOUNT:
        return RuleEvaluationResult(
            is_eligible=True,
            details=f"Requested amount ₹{amount:,} is within the limit of ₹{MAX_LOAN_AMOUNT:,}.",
        )
    else:
        return RuleEvaluationResult(
            is_eligible=True,
            needs_capping_confirmation=True,
            details=f"Requested amount ₹{amount:,} exceeds ₹75 Lakh maximum. Customer confirmation required.",
        )


def evaluate_occupation(occupation: Optional[str]) -> RuleEvaluationResult:
    """
    Allowed: Salaried, Self-employed. Both eligible.
    """
    if occupation is None:
        return RuleEvaluationResult(is_eligible=True)

    norm = occupation.strip().lower()
    if norm in [Occupation.SALARIED.value, Occupation.SELF_EMPLOYED.value]:
        return RuleEvaluationResult(is_eligible=True, details=f"Occupation '{norm}' is eligible.")
    return RuleEvaluationResult(is_eligible=True)


def evaluate_income_mode(income_mode: Optional[str]) -> RuleEvaluationResult:
    """
    Allowed: Bank.
    Not allowed: Cash.
    Cash -> Immediately disqualify.
    """
    if income_mode is None:
        return RuleEvaluationResult(is_eligible=True)

    norm = income_mode.strip().lower()
    if norm == IncomeMode.BANK.value:
        return RuleEvaluationResult(is_eligible=True, details="Bank income receipt is eligible.")
    elif norm == IncomeMode.CASH.value:
        return RuleEvaluationResult(
            is_eligible=False,
            is_disqualified=True,
            disqualification_reason="Income must be credited via bank transfer or account deposit to be eligible for this offer. Cash income cannot be considered.",
        )
    return RuleEvaluationResult(is_eligible=True)


def evaluate_market_value(market_value: Optional[int]) -> RuleEvaluationResult:
    """
    Captures estimated current property market value.
    The assignment does NOT specify a minimum property value. DO NOT INVENT A MINIMUM.
    """
    if market_value is None:
        return RuleEvaluationResult(is_eligible=True)

    if market_value > 0:
        return RuleEvaluationResult(
            is_eligible=True,
            details=f"Estimated market value ₹{market_value:,} recorded.",
        )
    return RuleEvaluationResult(is_eligible=True)


def evaluate_tenure(tenure_years: Optional[int]) -> RuleEvaluationResult:
    """
    Allowed: 3 to 15 years inclusive.
    < 3 years or > 15 years: Reject.
    """
    if tenure_years is None:
        return RuleEvaluationResult(is_eligible=True)

    if MIN_TENURE_YEARS <= tenure_years <= MAX_TENURE_YEARS:
        return RuleEvaluationResult(
            is_eligible=True,
            details=f"Tenure of {tenure_years} years is within the allowed 3-15 year range.",
        )
    else:
        return RuleEvaluationResult(
            is_eligible=False,
            is_disqualified=True,
            disqualification_reason=f"Repayment tenure must be between {MIN_TENURE_YEARS} and {MAX_TENURE_YEARS} years. {tenure_years} years is not supported for this offer.",
        )


def evaluate_transfer_condition(
    existing_property_loan: Optional[bool],
    emi_reduction_request: Optional[bool],
) -> RuleEvaluationResult:
    """
    If customer mentions existing loan on property or wanting to reduce EMI:
    Stop fresh-loan qualification and trigger specialist transfer.
    """
    if existing_property_loan is True:
        return RuleEvaluationResult(
            is_eligible=False,
            is_transfer_required=True,
            transfer_reason="Customer has an existing loan on the property.",
        )
    if emi_reduction_request is True:
        return RuleEvaluationResult(
            is_eligible=False,
            is_transfer_required=True,
            transfer_reason="Customer requested EMI reduction / balance transfer.",
        )
    return RuleEvaluationResult(is_eligible=True)


def evaluate_overall_eligibility(state: QualificationState) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Evaluates the complete state against all deterministic rules.
    Returns:
      (is_qualified, disqualification_reason, transfer_reason)
    """
    # 1. Transfer check
    transfer_res = evaluate_transfer_condition(
        state.existing_property_loan, state.emi_reduction_request
    )
    if transfer_res.is_transfer_required:
        return False, None, transfer_res.transfer_reason

    # 2. Immediate Disqualification Checks
    prop_res = evaluate_property_type(state.property_type)
    if prop_res.is_disqualified:
        return False, prop_res.disqualification_reason, None

    doc_res = evaluate_documents(state.documents_available)
    if doc_res.is_disqualified:
        return False, doc_res.disqualification_reason, None

    income_res = evaluate_income_mode(state.income_mode)
    if income_res.is_disqualified:
        return False, income_res.disqualification_reason, None

    tenure_res = evaluate_tenure(state.tenure_years)
    if tenure_res.is_disqualified:
        return False, tenure_res.disqualification_reason, None

    # 3. Completeness check for full qualification
    if state.is_all_seven_answered():
        return True, None, None

    return False, None, None
