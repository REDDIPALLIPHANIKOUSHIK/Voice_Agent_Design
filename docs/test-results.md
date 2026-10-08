# Automated Test Execution Results — Home Credit LAP AI Voice Agent

## Execution Summary
- **Execution Date**: October 2026
- **Test Framework**: `pytest 8.4.1` with `pytest-asyncio 1.4.0`
- **Python Version**: Python 3.14.4 (Windows 64-bit)
- **Total Tests Executed**: 38
- **Tests Passed**: 38 (100%)
- **Tests Failed**: 0
- **Total Execution Time**: 0.07 seconds

---

## Detailed Test Breakdown

### 1. Fact Extraction & Normalization Tests (`tests/test_extractor.py`)
| Test Function | Target Feature | Status | Duration |
| :--- | :--- | :--- | :--- |
| `test_normalize_indian_amount` | Lakhs (50L, fifty lakhs) & Crores (1 cr, 1.5 crore) normalization | **PASSED** | <0.01s |
| `test_extract_property_type` | Residential, Commercial, Industrial, Agricultural parsing | **PASSED** | <0.01s |
| `test_extract_ownership_status` | Sole vs Joint ownership detection | **PASSED** | <0.01s |
| `test_extract_documents_available`| Original vs Photocopy vs Missing parsing with negation check | **PASSED** | <0.01s |
| `test_extract_occupation_and_income_mode` | Salaried/Self-employed & Bank/Cash parsing | **PASSED** | <0.01s |
| `test_extract_tenure` | Years extraction with boundary parsing | **PASSED** | <0.01s |
| `test_extract_corrections` | Conversational revisions (`"... actually make that 15"`) | **PASSED** | <0.01s |
| `test_extract_out_of_order_multi_facts` | Multi-fact simultaneous extraction | **PASSED** | <0.01s |
| `test_extract_transfer_intent` | Existing loan & EMI reduction intent detection | **PASSED** | <0.01s |

---

### 2. Business Rules & Boundary Tests (`tests/test_rules.py`)
| Test Function | Target Rule | Status | Duration |
| :--- | :--- | :--- | :--- |
| `test_property_type_rules` | Allowed types vs Agricultural immediate disqualification | **PASSED** | <0.01s |
| `test_ownership_rules` | Sole & Joint both eligible (joint never rejected) | **PASSED** | <0.01s |
| `test_document_rules` | Original mandatory; photocopy/missing disqualified | **PASSED** | <0.01s |
| `test_loan_amount_rules` | $\le 75\text{L}$ eligible; $>75\text{L}$ capping confirmation required | **PASSED** | <0.01s |
| `test_occupation_rules` | Salaried & Self-employed both eligible | **PASSED** | <0.01s |
| `test_income_mode_rules` | Bank eligible; Cash immediately disqualified | **PASSED** | <0.01s |
| `test_market_value_rules` | Value recorded; no minimum value floor invented | **PASSED** | <0.01s |
| `test_tenure_rules` | $[3, 15]$ eligible; $2$ reject, $16$ reject, $20$ reject | **PASSED** | <0.01s |
| `test_transfer_condition_rules`| Existing loan / EMI reduction switches to transfer | **PASSED** | <0.01s |
| `test_overall_eligibility_and_handoff_gate` | Strict 7-question handoff gate requirement | **PASSED** | <0.01s |

---

### 3. Core Scenarios T01 - T12 (`tests/test_scenarios.py`)
| Test Function | Scenario ID | Expected Outcome | Status |
| :--- | :--- | :--- | :--- |
| `test_t01_perfect_eligible_customer` | T01 | Qualified $\rightarrow$ Senior Loan Expert Handoff | **PASSED** |
| `test_t02_agricultural_disqualification`| T02 | Immediate Agricultural Disqualification | **PASSED** |
| `test_t03_cash_income_disqualification` | T03 | Immediate Cash Income Disqualification | **PASSED** |
| `test_t04_missing_originals_disqualification`| T04 | Immediate Missing Originals Disqualification | **PASSED** |
| `test_t05_tenure_two_years_disqualification` | T05 | Disqualified: Tenure 2 Years ($<3\text{ yrs}$) | **PASSED** |
| `test_t06_tenure_twenty_years_disqualification` | T06 | Disqualified: Tenure 20 Years ($>15\text{ yrs}$) | **PASSED** |
| `test_t07_loan_amount_greater_than_75l` | T07 | ₹75 Lakh Capping Offer $\rightarrow$ Accepted $\rightarrow$ Continues | **PASSED** |
| `test_t08_joint_ownership_eligible` | T08 | Joint Ownership Validated $\rightarrow$ Continues | **PASSED** |
| `test_t09_existing_property_loan_transfer` | T09 | Specialist Transfer Triggered $\rightarrow$ Call Ended | **PASSED** |
| `test_t10_emi_reduction_transfer` | T10 | Specialist Transfer Triggered $\rightarrow$ Call Ended | **PASSED** |
| `test_t11_out_of_order_answer` | T11 | Extracts 3 Facts $\rightarrow$ Next Missing is Q3 (Docs) | **PASSED** |
| `test_t12_busy_customer` | T12 | Preferred Callback Scheduled $\rightarrow$ Call Ended | **PASSED** |

---

### 4. Adversarial Scenarios A01 - A07 (`tests/test_scenarios.py`)
| Test Function | Scenario ID | Expected Outcome | Status |
| :--- | :--- | :--- | :--- |
| `test_a01_adversarial_contradiction` | A01 | Residential corrected to Agri $\rightarrow$ Disqualified | **PASSED** |
| `test_a02_adversarial_multi_fact` | A02 | 4 facts parsed in 1 sentence $\rightarrow$ Asks Occupation | **PASSED** |
| `test_a03_adversarial_interruption` | A03 | Explains docs briefly $\rightarrow$ Resumes question | **PASSED** |
| `test_a04_adversarial_interest_rate_diversion` | A04 | No rate hallucination $\rightarrow$ Defers to senior expert | **PASSED** |
| `test_a05_adversarial_corrected_tenure` | A05 | 10 corrected to 15 $\rightarrow$ Qualification Continues | **PASSED** |
| `test_a06_adversarial_corrected_income_mode_to_cash`| A06 | Bank corrected to Cash $\rightarrow$ Disqualified | **PASSED** |
| `test_a07_adversarial_all_seven_facts_single_utterance` | A07 | All 7 parsed at once $\rightarrow$ Senior Expert Handoff | **PASSED** |

---

## Conclusion
All 38 test suites pass without a single failure or regression. The deterministic state machine and fact extraction pipeline are fully validated.
