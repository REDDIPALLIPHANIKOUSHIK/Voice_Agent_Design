"""
Unit tests for deterministic business rules in src/engine/rules.py.
Validates all boundary conditions and eligibility constraints.
"""

import pytest
from src.engine.rules import (
    evaluate_property_type,
    evaluate_ownership,
    evaluate_documents,
    evaluate_loan_amount,
    evaluate_occupation,
    evaluate_income_mode,
    evaluate_market_value,
    evaluate_tenure,
    evaluate_transfer_condition,
    evaluate_overall_eligibility,
    MAX_LOAN_AMOUNT,
    MIN_TENURE_YEARS,
    MAX_TENURE_YEARS,
)
from src.engine.models import QualificationState


def test_property_type_rules():
    # Eligible types
    for pt in ["residential", "commercial", "industrial", "Residential", "Commercial", "Industrial"]:
        res = evaluate_property_type(pt)
        assert res.is_eligible is True
        assert res.is_disqualified is False

    # Agricultural is immediately disqualified
    for pt in ["agricultural", "Agricultural", "farm", "kheti"]:
        res = evaluate_property_type(pt)
        assert res.is_eligible is False
        assert res.is_disqualified is True
        assert "Agricultural" in res.disqualification_reason


def test_ownership_rules():
    # Both Sole and Joint are eligible; joint must NEVER be rejected
    sole_res = evaluate_ownership("sole")
    assert sole_res.is_eligible is True
    assert sole_res.is_disqualified is False

    joint_res = evaluate_ownership("joint")
    assert joint_res.is_eligible is True
    assert joint_res.is_disqualified is False


def test_document_rules():
    # Original documents available -> eligible
    orig_res = evaluate_documents("original")
    assert orig_res.is_eligible is True
    assert orig_res.is_disqualified is False

    # Photocopy or missing -> disqualified
    photo_res = evaluate_documents("photocopy")
    assert photo_res.is_eligible is False
    assert photo_res.is_disqualified is True
    assert "original property documents" in photo_res.disqualification_reason.lower()

    miss_res = evaluate_documents("missing")
    assert miss_res.is_eligible is False
    assert miss_res.is_disqualified is True


def test_loan_amount_rules():
    # <= 75 Lakhs is eligible
    res_50l = evaluate_loan_amount(50_00_000)
    assert res_50l.is_eligible is True
    assert res_50l.needs_capping_confirmation is False

    res_75l = evaluate_loan_amount(75_00_000)
    assert res_75l.is_eligible is True
    assert res_75l.needs_capping_confirmation is False

    # > 75 Lakhs: Do NOT immediately disqualify, flag for capping confirmation
    res_90l = evaluate_loan_amount(90_00_000)
    assert res_90l.is_eligible is True
    assert res_90l.needs_capping_confirmation is True


def test_occupation_rules():
    # Both Salaried and Self-employed are eligible
    assert evaluate_occupation("salaried").is_eligible is True
    assert evaluate_occupation("self-employed").is_eligible is True


def test_income_mode_rules():
    # Bank -> eligible
    bank_res = evaluate_income_mode("bank")
    assert bank_res.is_eligible is True
    assert bank_res.is_disqualified is False

    # Cash -> immediately disqualified
    cash_res = evaluate_income_mode("cash")
    assert cash_res.is_eligible is False
    assert cash_res.is_disqualified is True
    assert "Cash income cannot be considered" in cash_res.disqualification_reason


def test_market_value_rules():
    # No minimum property value should be enforced
    res_10l = evaluate_market_value(10_00_000)
    assert res_10l.is_eligible is True

    res_1cr = evaluate_market_value(10_000_000)
    assert res_1cr.is_eligible is True


def test_tenure_rules():
    # Allowed: 3 to 15 years inclusive
    assert evaluate_tenure(3).is_eligible is True
    assert evaluate_tenure(10).is_eligible is True
    assert evaluate_tenure(15).is_eligible is True

    # 2 years -> reject
    res_2 = evaluate_tenure(2)
    assert res_2.is_eligible is False
    assert res_2.is_disqualified is True

    # 16 years -> reject
    res_16 = evaluate_tenure(16)
    assert res_16.is_eligible is False
    assert res_16.is_disqualified is True

    # 20 years -> reject
    res_20 = evaluate_tenure(20)
    assert res_20.is_eligible is False
    assert res_20.is_disqualified is True


def test_transfer_condition_rules():
    # Existing loan -> transfer
    t1 = evaluate_transfer_condition(existing_property_loan=True, emi_reduction_request=False)
    assert t1.is_transfer_required is True
    assert t1.is_eligible is False

    # EMI reduction -> transfer
    t2 = evaluate_transfer_condition(existing_property_loan=False, emi_reduction_request=True)
    assert t2.is_transfer_required is True
    assert t2.is_eligible is False

    # Fresh loan -> eligible
    t3 = evaluate_transfer_condition(existing_property_loan=False, emi_reduction_request=False)
    assert t3.is_transfer_required is False
    assert t3.is_eligible is True


def test_overall_eligibility_and_handoff_gate():
    # Incomplete state (missing tenure) -> cannot qualify
    incomplete_state = QualificationState(
        property_type="residential",
        ownership_status="sole",
        documents_available="original",
        loan_amount=50_00_000,
        occupation="salaried",
        income_mode="bank",
        market_value=10_000_000,
        tenure_years=None,  # missing
    )
    is_qual, disq, trans = evaluate_overall_eligibility(incomplete_state)
    assert is_qual is False

    # Complete state with all 7 answered -> qualifies for handoff
    complete_state = QualificationState(
        property_type="residential",
        ownership_status="sole",
        documents_available="original",
        loan_amount=50_00_000,
        occupation="salaried",
        income_mode="bank",
        market_value=10_000_000,
        tenure_years=10,
    )
    is_qual, disq, trans = evaluate_overall_eligibility(complete_state)
    assert is_qual is True
    assert disq is None
    assert trans is None
