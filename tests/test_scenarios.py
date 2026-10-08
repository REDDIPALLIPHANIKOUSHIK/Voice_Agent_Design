"""
Automated End-to-End Scenario Tests for Home Credit LAP Voice Agent.
Validates all required scenarios:
  T01: Perfect Eligible Customer
  T02: Agricultural Property Disqualification
  T03: Cash Income Disqualification
  T04: Missing Originals Disqualification
  T05: Tenure 2 Years Disqualification
  T06: Tenure 20 Years Disqualification
  T07: Loan Amount > ₹75 Lakh Capping Confirmation
  T08: Joint Ownership Qualification
  T09: Existing Property Loan Specialist Transfer
  T10: EMI Reduction Specialist Transfer
  T11: Out-of-Order Multi-Fact Response
  T12: Busy Customer Callback
And Adversarial Scenarios:
  A01: Contradiction Correction (Residential -> Agricultural)
  A02: Multiple Answers in One Response
  A03: Interruption Handling
  A04: Diversion (Interest Rate Question - No Hallucination)
  A05: Corrected Tenure (10 -> 15)
  A06: Corrected Income Mode (Bank -> Cash)
  A07: All 7 Facts in One Response
"""

import pytest
from src.engine.orchestrator import ConversationOrchestrator
from src.engine.models import QualificationState, CallStage


def test_t01_perfect_eligible_customer():
    state = QualificationState(customer_name="Rahul")
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes, this is Rahul speaking.")
    orch.process_utterance("It is a residential house.")
    orch.process_utterance("I am the sole owner.")
    orch.process_utterance("Yes, I have the original documents ready at home.")
    orch.process_utterance("I need around 50 lakhs.")
    orch.process_utterance("I am salaried and my income comes directly into my bank account.")
    orch.process_utterance("The market value is approximately 1 crore.")
    reply, final_state = orch.process_utterance("I would like a repayment period of 10 years.")

    assert final_state.handoff_required is True
    assert final_state.disqualified is False
    assert final_state.transfer_required is False
    assert final_state.call_ended is True
    assert "senior loan expert" in reply.lower()


def test_t02_agricultural_disqualification():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    reply, final_state = orch.process_utterance("The property is agricultural land used for farming.")

    assert final_state.disqualified is True
    assert "Agricultural" in final_state.disqualification_reason
    assert final_state.call_ended is True
    assert "not meet" in reply.lower() or "eligibility" in reply.lower()


def test_t03_cash_income_disqualification():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    orch.process_utterance("It's a residential apartment.")
    orch.process_utterance("Sole owner.")
    orch.process_utterance("Yes original papers are with me.")
    orch.process_utterance("Looking for 30 lakhs.")
    reply, final_state = orch.process_utterance("I am salaried but my employer gives my salary in cash.")

    assert final_state.disqualified is True
    assert "Cash income" in final_state.disqualification_reason
    assert final_state.call_ended is True


def test_t04_missing_originals_disqualification():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    orch.process_utterance("Commercial shop.")
    orch.process_utterance("Jointly owned with my brother.")
    reply, final_state = orch.process_utterance("I only have photocopies, not the originals.")

    assert final_state.disqualified is True
    assert "original property documents" in final_state.disqualification_reason.lower()
    assert final_state.call_ended is True


def test_t05_tenure_two_years_disqualification():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    orch.process_utterance("Residential house.")
    orch.process_utterance("Sole owner.")
    orch.process_utterance("Yes original documents are available.")
    orch.process_utterance("40 lakhs.")
    orch.process_utterance("Salaried, bank account.")
    orch.process_utterance("Market value is 80 lakhs.")
    reply, final_state = orch.process_utterance("I want to repay it in 2 years.")

    assert final_state.disqualified is True
    assert "2 years" in final_state.disqualification_reason
    assert final_state.call_ended is True


def test_t06_tenure_twenty_years_disqualification():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    orch.process_utterance("Residential flat.")
    orch.process_utterance("Sole owner.")
    orch.process_utterance("Yes originals are at home.")
    orch.process_utterance("50 lakhs.")
    orch.process_utterance("Self-employed, income into bank.")
    orch.process_utterance("Market value 90 lakhs.")
    reply, final_state = orch.process_utterance("I need 20 years to repay.")

    assert final_state.disqualified is True
    assert "20 years" in final_state.disqualification_reason
    assert final_state.call_ended is True


def test_t07_loan_amount_greater_than_75l():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    orch.process_utterance("Commercial office.")
    orch.process_utterance("Sole ownership.")
    orch.process_utterance("Original papers ready.")
    reply_cap, state_cap = orch.process_utterance("I need 90 lakhs.")

    # Must prompt customer to accept ₹75 Lakh max
    assert state_cap.awaiting_75l_confirmation is True
    assert state_cap.original_requested_loan_amount == 90_00_000
    assert "75 lakh" in reply_cap.lower()

    # Customer accepts
    reply_acc, state_acc = orch.process_utterance("Yes, I would like to proceed with 75 lakhs.")
    assert state_acc.loan_amount == 75_00_000
    assert state_acc.awaiting_75l_confirmation is False


def test_t08_joint_ownership_eligible():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    orch.process_utterance("Residential flat.")
    reply, intermediate_state = orch.process_utterance("It is jointly owned with my wife.")

    # Joint ownership must NOT disqualify
    assert intermediate_state.ownership_status == "joint"
    assert intermediate_state.disqualified is False
    assert intermediate_state.call_ended is False


def test_t09_existing_property_loan_transfer():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    reply, final_state = orch.process_utterance("I already have a loan running on this property.")

    assert final_state.transfer_required is True
    assert final_state.call_ended is True
    assert "specialist" in reply.lower()


def test_t10_emi_reduction_transfer():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    reply, final_state = orch.process_utterance("I want to reduce my EMI on my current property loan.")

    assert final_state.transfer_required is True
    assert final_state.call_ended is True
    assert "specialist" in reply.lower()


def test_t11_out_of_order_answer():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    reply, current_state = orch.process_utterance(
        "It's a residential house, jointly owned with my wife, and worth around 80 lakhs."
    )

    # Must extract property_type, ownership, and market_value
    assert current_state.property_type == "residential"
    assert current_state.ownership_status == "joint"
    assert current_state.market_value == 80_00_000

    # Next missing question must be document availability!
    # It must NOT ask ownership or market value again!
    assert "document" in reply.lower() or "original" in reply.lower()


def test_t12_busy_customer():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    reply, final_state = orch.process_utterance("I'm in a meeting right now, please call me back around 5 pm.")
    assert final_state.customer_busy is True
    assert final_state.call_ended is True
    assert "5 pm" in final_state.callback_time or "5 pm" in reply.lower()


def test_a01_adversarial_contradiction():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    reply, final_state = orch.process_utterance("It's residential... actually it's agricultural.")
    assert final_state.disqualified is True
    assert "Agricultural" in final_state.disqualification_reason


def test_a02_adversarial_multi_fact():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    reply, s = orch.process_utterance("It's my own house, original papers are available and I need around 40 lakhs.")
    assert s.property_type == "residential"
    assert s.ownership_status == "sole"
    assert s.documents_available == "original"
    assert s.loan_amount == 40_00_000
    # Next question should be occupation
    assert "occupation" in reply.lower() or "salaried" in reply.lower()


def test_a03_adversarial_interruption():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    reply, s = orch.process_utterance("Wait, what documents do you need?")
    # Must answer about documents and not crash or forget flow
    assert "document" in reply.lower() or "deed" in reply.lower()


def test_a04_adversarial_interest_rate_diversion():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    reply, s = orch.process_utterance("What interest rate do you offer?")
    # Must NOT hallucinate an interest rate like "8.5%" or "10%"
    assert "expert" in reply.lower() or "senior" in reply.lower()
    assert "%" not in reply


def test_a05_adversarial_corrected_tenure():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    orch.process_utterance("Residential house.")
    orch.process_utterance("Sole owner.")
    orch.process_utterance("Original papers ready.")
    orch.process_utterance("50 lakhs.")
    orch.process_utterance("Salaried, bank.")
    orch.process_utterance("Market value 90 lakhs.")
    reply, s = orch.process_utterance("10 years... actually make that 15.")

    assert s.tenure_years == 15
    assert s.handoff_required is True


def test_a06_adversarial_corrected_income_mode_to_cash():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    orch.process_utterance("Residential flat.")
    orch.process_utterance("Sole owner.")
    orch.process_utterance("Original documents available.")
    orch.process_utterance("40 lakhs.")
    reply, s = orch.process_utterance("Salaried, bank... actually cash.")

    assert s.income_mode == "cash"
    assert s.disqualified is True


def test_a07_adversarial_all_seven_facts_single_utterance():
    state = QualificationState()
    orch = ConversationOrchestrator(state=state)
    orch.generate_initial_greeting()

    orch.process_utterance("Yes speaking.")
    reply, s = orch.process_utterance(
        "It is a residential property sole owned with original papers, I need 50 lakhs, I am salaried with bank credit, market value is 1 crore and tenure is 10 years."
    )

    assert s.is_all_seven_answered() is True
    assert s.handoff_required is True
    assert "senior loan expert" in reply.lower()
