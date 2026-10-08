# Test Plan & Verification Strategy — Home Credit LAP AI Voice Agent

## 1. Overview
The testing architecture for the Home Credit LAP AI Voice Agent combines unit verification of mathematical and business boundaries with end-to-end conversational scenario tests. Every requirement in the SalesAgents AI specification is backed by automated tests.

---

## 2. Test Pyramid & Scope

```
             ┌─────────────────────────┐
             │  Live Audio & Voice     │  (Browser Web Speech / Retell Telephony)
             ├─────────────────────────┤
             │  Conversational E2E     │  (T01-T12 Core + A01-A07 Adversarial)
             ├─────────────────────────┤
             │  Fact Extractor & Regex │  (Multi-fact, Indian Currency, Corrections)
             ├─────────────────────────┤
             │  Deterministic Rules    │  (7 Eligibility Points, Transfer Gates)
             └─────────────────────────┘
```

---

## 3. Core Test Scenarios (T01 - T12)

| Test ID | Scenario Description | Customer Input / Utterance | Expected State & Outcome |
| :--- | :--- | :--- | :--- |
| **T01** | Perfect Eligible Customer | Residential, Sole owner, Original docs, ₹50L, Salaried, Bank, ₹1 Cr value, 10 yrs | **QUALIFIED $\rightarrow$ HANDOFF** to Senior Loan Expert |
| **T02** | Agricultural Property | "The property is agricultural land used for farming." | **Immediate Disqualification** $\rightarrow$ Call Ended |
| **T03** | Cash Income | Salaried, but "employer gives my salary in cash." | **Immediate Disqualification** $\rightarrow$ Call Ended |
| **T04** | Missing Originals | "I only have photocopies, not the originals." | **Immediate Disqualification** $\rightarrow$ Call Ended |
| **T05** | Tenure 2 Years ($<3\text{ yrs}$) | "I want to repay it in 2 years." | **Immediate Disqualification** $\rightarrow$ Call Ended |
| **T06** | Tenure 20 Years ($>15\text{ yrs}$) | "I need 20 years to repay." | **Immediate Disqualification** $\rightarrow$ Call Ended |
| **T07** | Loan Amount $> ₹75\text{ Lakh}$ | "I need 90 lakhs." $\rightarrow$ "Yes proceed with 75 lakhs." | **Cap at ₹75 Lakh** $\rightarrow$ Qualification Continues |
| **T08** | Joint Ownership | "It is jointly owned with my wife." | **ELIGIBLE** $\rightarrow$ Qualification Continues |
| **T09** | Existing Property Loan | "I already have a loan running on this property." | **Specialist Transfer** $\rightarrow$ Call Ended |
| **T10** | EMI Reduction Intent | "I want to reduce my EMI on my current property loan." | **Specialist Transfer** $\rightarrow$ Call Ended |
| **T11** | Out-of-Order Multi-Fact | "Residential house, jointly owned with wife, worth 80 lakhs." | **Extracts all 3 facts** $\rightarrow$ Asks next missing (Docs) |
| **T12** | Busy Customer Flow | "I'm in a meeting right now, please call me back around 5 pm." | **Callback Recorded** $\rightarrow$ Call Ended Politely |

---

## 4. Adversarial & Edge Case Scenarios (A01 - A07)

| Test ID | Adversarial Challenge | Customer Input / Utterance | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **A01** | Contradiction Correction | "It's residential... actually it's agricultural." | Overwrites with agricultural $\rightarrow$ **Immediate Disqualification** |
| **A02** | Multi-Fact Utterance | "My own house, original papers ready, need 40 lakhs." | Extracts 4 facts $\rightarrow$ Asks Occupation next |
| **A03** | Customer Interruption | "Wait, what documents do you need?" | Answers document query $\rightarrow$ Resumes checklist |
| **A04** | Interest Rate Diversion | "What interest rate do you offer?" | **Zero hallucination** $\rightarrow$ Defers to senior expert $\rightarrow$ Continues |
| **A05** | Corrected Tenure | "10 years... actually make that 15." | Overwrites tenure to 15 $\rightarrow$ Continues to completion |
| **A06** | Corrected Income to Cash | "Salaried, bank... actually cash." | Overwrites to cash $\rightarrow$ **Immediate Disqualification** |
| **A07** | All 7 Facts in One Burst | All 7 data points in one single sentence | Extracts all 7 $\rightarrow$ Validates all $\rightarrow$ **Senior Expert Handoff** |

---

## 5. Execution Command
To run the automated suite:
```bash
python -m pytest tests/ -v
```
To run the interactive UI simulator:
1. Start the server: `python run.py`
2. Open `http://localhost:8000/`
3. Select any scenario from the **Automated Scenario Simulator** dropdown and click **Run Simulation**.
