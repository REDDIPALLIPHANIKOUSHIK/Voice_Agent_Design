"""
Unit tests for fact extraction & value normalization in src/engine/extractor.py.
"""

import pytest
from src.engine.extractor import (
    normalize_indian_amount,
    extract_property_type,
    extract_ownership_status,
    extract_documents_available,
    extract_occupation_and_income_mode,
    extract_amounts,
    extract_tenure,
    extract_transfer_intent,
    extract_facts,
)


def test_normalize_indian_amount():
    assert normalize_indian_amount("50 lakh") == 50_00_000
    assert normalize_indian_amount("50 lakhs") == 50_00_000
    assert normalize_indian_amount("₹50L") == 50_00_000
    assert normalize_indian_amount("50L") == 50_00_000
    assert normalize_indian_amount("fifty lakhs") == 50_00_000
    assert normalize_indian_amount("75 lakh") == 75_00_000
    assert normalize_indian_amount("1 crore") == 10_000_000
    assert normalize_indian_amount("1.5 crore") == 15_000_000
    assert normalize_indian_amount("1 cr") == 10_000_000
    assert normalize_indian_amount("one crore") == 10_000_000
    assert normalize_indian_amount("5000000") == 50_00_000


def test_extract_property_type():
    assert extract_property_type("It's a residential house") == "residential"
    assert extract_property_type("We own a commercial shop") == "commercial"
    assert extract_property_type("It is an industrial factory") == "industrial"
    assert extract_property_type("It's farmland used for agriculture") == "agricultural"


def test_extract_ownership_status():
    assert extract_ownership_status("I am the sole owner") == "sole"
    assert extract_ownership_status("It's my own property alone") == "sole"
    assert extract_ownership_status("Jointly owned with my wife") == "joint"
    assert extract_ownership_status("It is a joint property with my brother") == "joint"


def test_extract_documents_available():
    assert extract_documents_available("Yes I have the original documents at home") == "original"
    assert extract_documents_available("I have original registry papers") == "original"
    assert extract_documents_available("I only have photocopies") == "photocopy"
    assert extract_documents_available("I don't have the originals") == "photocopy"
    assert extract_documents_available("The papers are lost and missing") == "missing"


def test_extract_occupation_and_income_mode():
    occ, mode = extract_occupation_and_income_mode("I am salaried and my income comes into my bank account")
    assert occ == "salaried"
    assert mode == "bank"

    occ2, mode2 = extract_occupation_and_income_mode("Self-employed businessman, income is in cash")
    assert occ2 == "self-employed"
    assert mode2 == "cash"


def test_extract_tenure():
    assert extract_tenure("10 years") == 10
    assert extract_tenure("Around 15 yrs") == 15
    assert extract_tenure("5 saal") == 5
    assert extract_tenure("10 years... actually make that 12") == 12


def test_extract_corrections():
    # Tenure correction
    assert extract_tenure("10 years... actually make that 12") == 12
    assert extract_tenure("10 years... actually 15") == 15

    # Income mode correction
    _, mode = extract_occupation_and_income_mode("Bank... actually cash")
    assert mode == "cash"

    # Property type correction
    pt = extract_property_type("It's residential... actually it's agricultural")
    assert pt == "agricultural"


def test_extract_out_of_order_multi_facts():
    # Customer: "It's a residential house, jointly owned with my wife, and worth around 80 lakhs."
    facts = extract_facts("It's a residential house, jointly owned with my wife, and worth around 80 lakhs.")
    assert facts.property_type == "residential"
    assert facts.ownership_status == "joint"
    assert facts.market_value == 80_00_000
    assert facts.documents_available is None  # not mentioned, so remains None!


def test_extract_transfer_intent():
    ex1, emi1 = extract_transfer_intent("I already have a loan on this property.")
    assert ex1 is True
    assert emi1 is False

    ex2, emi2 = extract_transfer_intent("I want to reduce my EMI.")
    assert ex2 is False
    assert emi2 is True
