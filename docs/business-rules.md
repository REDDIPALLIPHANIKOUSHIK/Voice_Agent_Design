# Business Rules & Qualification Logic — Home Credit LAP AI Voice Agent

## 1. Overview
The Home Credit Loan Against Property (LAP) qualification process is defined by strict credit and operational policies. The AI Voice Agent enforces these rules deterministically to prevent false approvals and maintain lending compliance.

---

## 2. Exhaustive Rule Definitions

### Rule 1: Property Type
- **Requirement**: The customer's pledged collateral must fall into approved property classifications.
- **Allowed Property Types**:
  - `Residential` (Independent house, villa, flat, apartment)
  - `Commercial` (Shop, office space, retail complex)
  - `Industrial` (Factory, warehouse, manufacturing unit)
- **Disqualified Property Types**:
  - `Agricultural` (Farmland, agricultural plot, plantation)
- **Enforcement**:
  - If `agricultural` is detected at ANY point, immediately stop the call.
  - Explanation: *"Agricultural properties are not eligible for this Loan Against Property offer. Only residential, commercial, or industrial properties can be considered."*
  - End Call immediately.

### Rule 2: Ownership Status
- **Requirement**: Ascertain legal title and applicant stake.
- **Allowed Statuses**:
  - `Sole` ownership (100% owned by applicant)
  - `Joint` ownership (Co-owned with spouse, parents, siblings, or business partners)
- **Enforcement**:
  - Both Sole and Joint ownership are **fully eligible**.
  - **CRITICAL CONSTRAINT**: Joint ownership must NEVER be treated as a rejection or penalty.

### Rule 3: Original Documents Availability
- **Requirement**: Physical verification of property title documents is mandatory for collateral registration.
- **Allowed**:
  - `Original` documents available (at home, in locker, or retrievable for inspection).
- **Disqualified**:
  - `Photocopy` only, `xerox` only, certified copies only, or `lost/missing` documents.
- **Enforcement**:
  - The customer is NOT required to physically hold the documents during the call. Stating they are at home or ready for verification is eligible.
  - If only photocopies are available or originals are missing, immediately disqualify and end call.

### Rule 4: Loan Amount
- **Requirement**: Standard LAP promotional offer ceiling is ₹75,00,000 (75 Lakhs INR).
- **Allowed**:
  - Any amount $\le ₹75,00,000$.
- **Amount $> ₹75,00,000$ (e.g. ₹90 Lakhs, ₹1.5 Crore)**:
  - **DO NOT IMMEDIATELY DISQUALIFY.**
  - Agent must prompt:
    *"The current offer is available for up to ₹75 lakh. Would you like to proceed with the maximum eligible amount of ₹75 lakh?"*
  - If Customer answers **YES**:
    - Record `loan_amount = 75,00,000`.
    - Record `original_requested_loan_amount = <original_amount>`.
    - Continue qualification flow.
  - If Customer answers **NO**:
    - Explain politely that this specific offer cannot exceed ₹75 Lakh.
    - End call.

### Rule 5: Occupation & Income Mode
- **Requirement**: Applicant must demonstrate verifiable repayment capability through formal banking channels.
- **Occupation Categories**:
  - `Salaried` (Corporate, Government, Private sector) $\rightarrow$ **Eligible**
  - `Self-Employed` (Business owner, Freelancer, Professional, Merchant) $\rightarrow$ **Eligible**
- **Income Receipt Mode**:
  - `Bank` (Direct salary credit, NEFT, RTGS, Cheque, Bank statement deposit) $\rightarrow$ **Eligible**
  - `Cash` (Salary in hand, cash payments, unbanked earnings) $\rightarrow$ **Disqualified**
- **Enforcement Matrix**:
  | Occupation | Income Mode | Result |
  | :--- | :--- | :--- |
  | Salaried | Bank | **ELIGIBLE** |
  | Salaried | Cash | **DISQUALIFIED (Immediate)** |
  | Self-Employed | Bank | **ELIGIBLE** |
  | Self-Employed | Cash | **DISQUALIFIED (Immediate)** |

### Rule 6: Current Market Valuation
- **Requirement**: Capture the customer's approximate estimate of the property's market value.
- **Enforcement & Crucial Boundary**:
  - The assignment **DOES NOT specify a minimum property value**.
  - **DO NOT INVENT A MINIMUM FLOOR** (Never say *"Your property must be worth at least ₹1 Crore"*).
  - Accept and store whatever realistic figure the customer provides.

### Rule 7: Repayment Tenure
- **Requirement**: Repayment term requested by the applicant.
- **Allowed Tenure**:
  - $3 \text{ to } 15 \text{ years inclusive}$.
- **Disqualified Tenure**:
  - $< 3 \text{ years}$ (e.g., 1 or 2 years) $\rightarrow$ **Disqualified**
  - $> 15 \text{ years}$ (e.g., 16, 20, 25 years) $\rightarrow$ **Disqualified**
- **Boundary Test Cases**:
  - 2 years $\rightarrow$ Reject
  - 3 years $\rightarrow$ Eligible
  - 10 years $\rightarrow$ Eligible
  - 15 years $\rightarrow$ Eligible
  - 16 years $\rightarrow$ Reject

---

## 3. Special Flow Switches

### 3.1 Existing Loan / EMI Reduction Transfer Switch
- **Trigger**: Customer states at ANY point:
  - *"I already have a loan on this property"*
  - *"I want to reduce my EMI"*
  - *"Looking for a balance transfer / loan transfer"*
- **Action**:
  1. Immediately stop fresh-loan qualification.
  2. Do NOT ask remaining checklist questions.
  3. Respond:
     *"Thank you for clarifying. Since you already have an existing loan on the property, this would need to be handled by our loan-transfer specialist. A specialist will contact you shortly regarding this. Thank you for your time."*
  4. End Call.

### 3.2 Busy Customer Flow
- **Trigger**: Customer states *"I'm busy"*, *"In a meeting"*, *"Driving"*, or *"Call me later"*.
- **Action**:
  1. Acknowledge immediately: *"Certainly, I understand. What would be a convenient time for us to call you back?"*
  2. Capture requested callback time.
  3. Conclude politely and End Call.

### 3.3 Final Handoff Gate
- **Requirement**: Strictly enforces that ALL 7 checklist questions are answered, no disqualifications occurred, and no transfer condition was triggered.
- **Action**:
  *"Thank you for providing all the details. Based on our preliminary check, you successfully meet our eligibility criteria! A senior loan expert will contact you shortly to discuss the next steps and provide the exact interest rate. Thank you for your time, and have a great day!"*
- **Crucial Boundary**: Never state *"You are fully approved"*. The agent only conducts preliminary qualification.
