"""
Fact Extraction & Value Normalization Engine for Home Credit LAP Voice Agent.
Extracts structured eligibility data points, handles conversational corrections,
out-of-order information, Hindi/English terms, and normalizes Indian financial numerals.
"""

import re
from typing import Optional, Dict, Any, Tuple
from src.engine.models import (
    PropertyType,
    OwnershipStatus,
    DocumentStatus,
    Occupation,
    IncomeMode,
    ExtractedFacts,
)

# Text to number map for simple quantities
WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-five": 25, "thirty": 30,
    "thirty-five": 35, "forty": 40, "forty-five": 45, "fifty": 50,
    "sixty": 60, "seventy": 70, "seventy-five": 75, "eighty": 80,
    "ninety": 90, "hundred": 100, "crore": 10000000,
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5,
    "das": 10, "barah": 12, "pandrah": 15, "bees": 20, "pachaas": 50,
    "pachattar": 75, "assi": 80, "ek crore": 10000000
}


def normalize_indian_amount(text: str) -> Optional[int]:
    """
    Parses currency strings like:
      - '50 lakh', '50 lakhs', '50L', '₹50,00,000', 'fifty lakhs' -> 5,000,000
      - '1.5 crore', '1 crore', '1 cr', 'one crore' -> 15,000,000 / 10,000,000
      - '7500000', '₹75 lakh' -> 7,500,000
    """
    if not text:
        return None
    cleaned = text.lower().replace("₹", "").replace("rs.", "").replace("inr", "").replace(",", "").strip()

    # Check crore
    cr_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:cr|crore|crores|karod)", cleaned)
    if cr_match:
        val = float(cr_match.group(1))
        return int(val * 10_000_000)

    # Check word crore
    if "one crore" in cleaned or "ek crore" in cleaned:
        return 10_000_000
    if "two crore" in cleaned or "do crore" in cleaned:
        return 20_000_000

    # Check lakh / lac
    lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b", cleaned)
    if lakh_match:
        val = float(lakh_match.group(1))
        return int(val * 100_000)

    # Word lakh: e.g. "fifty lakhs", "seventy five lakhs", "forty lakh"
    for word, num in [
        ("seventy five", 75), ("seventy-five", 75), ("pachattar", 75),
        ("fifty", 50), ("pachaas", 50), ("forty", 40), ("challis", 40),
        ("thirty", 30), ("tees", 30), ("sixty", 60), ("saath", 60),
        ("eighty", 80), ("assi", 80), ("ninety", 90), ("nabbe", 90),
        ("twenty", 20), ("twenty five", 25), ("ten", 10), ("das", 10)
    ]:
        if f"{word} lakh" in cleaned or f"{word} lac" in cleaned:
            return num * 100_000

    # Plain digits >= 10000
    digit_match = re.search(r"\b(\d{5,9})\b", cleaned)
    if digit_match:
        return int(digit_match.group(1))

    return None


def extract_property_type(utterance: str) -> Optional[str]:
    """
    Identifies property type, prioritizing corrections.
    """
    text = utterance.lower()

    # Handle corrections: e.g. "residential... actually it's agricultural"
    chunks = re.split(r"\b(?:actually|no wait|make that|correction|instead of that|rather)\b", text)
    target = chunks[-1] if len(chunks) > 1 else text

    # Agricultural
    if any(k in target for k in ["agricultural", "farmland", "farm land", "farm house", "agriculture", "kheti", "krishi", "khet"]):
        return PropertyType.AGRICULTURAL.value

    # Industrial
    if any(k in target for k in ["industrial", "factory", "warehouse", "manufacturing unit", "godown", "karkhana"]):
        return PropertyType.INDUSTRIAL.value

    # Commercial
    if any(k in target for k in ["commercial", "shop", "office", "retail space", "dukan", "complex"]):
        return PropertyType.COMMERCIAL.value

    # Residential
    if any(k in target for k in ["residential", "house", "flat", "apartment", "home", "villa", "living space", "makan", "ghar"]):
        return PropertyType.RESIDENTIAL.value

    # Fallback check on full text if target didn't yield and no correction was made
    if len(chunks) == 1:
        if any(k in text for k in ["agricultural", "kheti", "krishi"]):
            return PropertyType.AGRICULTURAL.value
        if any(k in text for k in ["industrial", "factory"]):
            return PropertyType.INDUSTRIAL.value
        if any(k in text for k in ["commercial", "shop", "dukan"]):
            return PropertyType.COMMERCIAL.value
        if any(k in text for k in ["residential", "house", "flat"]):
            return PropertyType.RESIDENTIAL.value

    return None


def extract_ownership_status(utterance: str) -> Optional[str]:
    """
    Identifies Sole vs Joint ownership, respecting corrections.
    """
    text = utterance.lower()
    chunks = re.split(r"\b(?:actually|no wait|make that|correction)\b", text)
    target = chunks[-1] if len(chunks) > 1 else text

    # Joint
    if any(k in target for k in [
        "joint", "jointly", "with my wife", "with wife", "with my husband",
        "with husband", "with family", "with partner", "with my brother",
        "with my father", "co-owner", "shared property", "along with my", "joint property"
    ]):
        return OwnershipStatus.JOINT.value

    # Sole
    if any(k in target for k in [
        "sole", "individual", "my own", "single owner", "only me", "myself",
        "purely mine", "alone", "in my name", "own property", "single ownership"
    ]):
        return OwnershipStatus.SOLE.value

    return None


def extract_documents_available(utterance: str) -> Optional[str]:
    """
    Identifies original vs photocopy vs missing/lost documents.
    Checks negative and photocopy patterns FIRST before matching 'original'.
    """
    text = utterance.lower()

    # Negative / photocopy patterns FIRST
    if any(k in text for k in [
        "don't have original", "do not have original", "no original",
        "don't have the original", "do not have the original", "no originals",
        "don't have the originals", "lost the original", "photocopy",
        "photocopies", "xerox", "only copy", "only copies", "duplicate",
        "only have photocopies", "missing original"
    ]):
        return DocumentStatus.PHOTOCOPY.value

    # Missing / lost
    if any(k in text for k in ["lost", "missing", "don't have them", "do not have documents", "papers lost"]):
        return DocumentStatus.MISSING.value

    # Positive: Original available
    if any(k in text for k in [
        "original", "originals", "original documents", "registry",
        "have the original", "original papers", "ready at home",
        "have them at home", "papers are ready", "yes i have them",
        "available at home", "original available", "at home with me"
    ]):
        return DocumentStatus.ORIGINAL.value

    return None


def extract_occupation_and_income_mode(utterance: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts occupation (salaried, self-employed) and income mode (bank, cash).
    Handles corrections like: 'Bank... actually cash' -> (None, cash).
    """
    text = utterance.lower()

    # Split for corrections
    chunks = re.split(r"\b(?:actually|no wait|make that|correction)\b", text)
    latest_chunk = chunks[-1] if len(chunks) > 1 else text

    occupation = None
    income_mode = None

    # Occupation check
    if any(k in text for k in [
        "salaried", "job", "private job", "government job", "govt job",
        "employee", "working in", "work at", "software engineer", "service"
    ]):
        occupation = Occupation.SALARIED.value
    elif any(k in text for k in [
        "self-employed", "self employed", "business", "own business",
        "shopkeeper", "businessman", "freelancer", "proprietor", "contractor"
    ]):
        occupation = Occupation.SELF_EMPLOYED.value

    # Income Mode check in latest chunk
    if any(k in latest_chunk for k in ["cash", "haath me", "rokad", "hard cash", "by cash", "in cash"]):
        income_mode = IncomeMode.CASH.value
    elif any(k in latest_chunk for k in [
        "bank", "account", "direct deposit", "cheque", "neft", "rtgs",
        "online transfer", "salary account", "in bank", "into my bank"
    ]):
        income_mode = IncomeMode.BANK.value
    else:
        # Check full text if not found in latest chunk
        if any(k in text for k in ["cash", "haath me", "rokad"]):
            income_mode = IncomeMode.CASH.value
        elif any(k in text for k in ["bank", "account", "cheque", "neft", "transfer"]):
            income_mode = IncomeMode.BANK.value

    return occupation, income_mode


def extract_amounts(utterance: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Differentiates between requested loan amount and property market value.
    Returns: (loan_amount, market_value)
    """
    text = utterance.lower()
    loan_amount = None
    market_value = None

    # Market value patterns: 'worth 80 lakhs', 'market value is 1 crore', 'valued at 60L'
    mv_match = re.search(
        r"(?:worth|market\s*value|valued\s*at|valuation|cost(?:s)?\s*around|price\s*is|evaluated\s*at)\s*(?:is|around|about|of)?\s*([₹\d\w\s.,]+?(?:lakh|lakhs|lac|lacs|cr|crore|crores|l)\b|\d{6,9})",
        text,
    )
    if mv_match:
        market_value = normalize_indian_amount(mv_match.group(1))

    # Loan amount patterns: 'need 40 lakhs', 'borrow 50 lakhs', 'loan of 75 lakhs', 'looking for 50L'
    la_match = re.search(
        r"(?:need|borrow|loan\s*(?:of|amount|is)?|looking\s*for|want|require)\s*(?:around|about|of)?\s*([₹\d\w\s.,]+?(?:lakh|lakhs|lac|lacs|cr|crore|crores|l)\b|\d{6,9})",
        text,
    )
    if la_match:
        loan_amount = normalize_indian_amount(la_match.group(1))

    # If neither specific pattern matched, extract general amounts
    if not loan_amount and not market_value:
        general_amount = normalize_indian_amount(text)
        if any(w in text for w in ["worth", "property value", "market value", "valuation"]):
            market_value = general_amount
        else:
            loan_amount = general_amount

    return loan_amount, market_value


def extract_tenure(utterance: str) -> Optional[int]:
    """
    Extracts tenure in years, respecting corrections like:
    '10 years... actually make that 15' -> 15
    Never matches numbers associated with currency/amounts (lakhs, crores).
    """
    text = utterance.lower()
    chunks = re.split(r"\b(?:actually|no wait|make that|correction|changed my mind)\b", text)
    target = chunks[-1].strip("., !?") if len(chunks) > 1 else text

    # Digit followed by years / saal
    match = re.search(r"\b(\d{1,2})\s*(?:years?|yrs?|yr|saal)\b", target)
    if match:
        return int(match.group(1))

    # Preceded by tenure phrases: e.g. 'repayment period of 10', 'tenure of 12', 'term of 15'
    phrase_match = re.search(r"\b(?:period|tenure|term|repay in|repayment of)\s*(?:of|is|around)?\s*(\d{1,2})\b", target)
    if phrase_match:
        return int(phrase_match.group(1))

    # Word numbers with years: 'ten years', 'fifteen years'
    for word, num in WORD_NUMS.items():
        if f"{word} year" in target or f"{word} saal" in target:
            return num

    # Standalone single number ONLY if utterance is purely a short digit (e.g. "10", "12", "15")
    # AND does not contain lakh, crore, rs, or amount words
    if not any(k in target for k in ["lakh", "lac", "cr", "crore", "₹", "rs", "thousand"]):
        cleaned_words = target.split()
        if len(cleaned_words) <= 3:
            raw_digit_match = re.search(r"\b(\d{1,2})\b", target)
            if raw_digit_match:
                val = int(raw_digit_match.group(1))
                if 1 <= val <= 30:
                    return val

    # Fallback to full text if no correction chunk matched
    if len(chunks) > 1:
        match = re.search(r"\b(\d{1,2})\s*(?:years?|yrs?|yr|saal)\b", text)
        if match:
            return int(match.group(1))

    return None


def extract_transfer_intent(utterance: str) -> Tuple[bool, bool]:
    """
    Detects existing property loan or EMI reduction / balance transfer intent.
    Returns: (existing_property_loan, emi_reduction_request)
    """
    text = utterance.lower()

    existing_loan = False
    emi_reduction = False

    if any(k in text for k in [
        "already have a loan", "existing loan", "already taking loan",
        "running loan", "current loan on this property", "loan running on this house"
    ]):
        existing_loan = True

    if any(k in text for k in [
        "reduce my emi", "lower my emi", "emi reduction", "balance transfer",
        "transfer my loan", "lower interest transfer", "decrease my emi"
    ]):
        emi_reduction = True

    return existing_loan, emi_reduction


def extract_busy_or_callback(utterance: str) -> Tuple[bool, Optional[str]]:
    """
    Detects if the customer is busy or requests a callback.
    Returns: (customer_busy, callback_time)
    """
    text = utterance.lower()
    busy = False
    callback_time = None

    if any(k in text for k in [
        "busy", "in a meeting", "call me later", "call back later",
        "not a good time", "driving", "can't talk right now",
        "cannot talk", "reach out later", "call after", "call tomorrow"
    ]):
        busy = True

    # Check for time expression
    time_match = re.search(
        r"(?:call\s*(?:me)?\s*(?:back)?|after|at|around)?\s*(\b\d{1,2}(?::\d{2})?\s*(?:am|pm|o'clock)?\b|\btomorrow\b|\bevening\b|\bafternoon\b)",
        text,
    )
    if time_match and busy:
        callback_time = time_match.group(0).strip()

    return busy, callback_time


def extract_diversion_or_interruption(utterance: str) -> Tuple[bool, Optional[str], bool, Optional[str]]:
    """
    Detects if the customer asked an interrupting question or diverted to interest rates, fees, etc.
    Returns: (is_diversion, diversion_topic, is_interruption, interruption_query)
    """
    text = utterance.lower()

    # Interest rate diversion
    if any(k in text for k in ["interest rate", "rate of interest", "roi", "biyaj", "byaaj"]):
        return True, "interest_rate", False, None

    # Fees / charges diversion
    if any(k in text for k in ["processing fee", "charges", "hidden fee", "penalty"]):
        return True, "charges", False, None

    # General interruption question
    if any(k in text for k in ["wait", "what documents", "what papers", "how does this work", "why do you need"]):
        return False, None, True, utterance

    return False, None, False, None


def extract_confirmation_answer(utterance: str) -> Optional[bool]:
    """
    Detects Yes/No confirmation (e.g. for >75L capping acceptance).
    Uses regex word boundaries to avoid substring false positives.
    """
    text = utterance.lower().strip()
    if re.search(r"\b(yes|yeah|sure|ok|okay|fine|proceed|alright|agree|let's do 75|ha|haan)\b", text):
        return True
    if re.search(r"\b(no|nope|that won't work|too less|not enough|cancel|nahi)\b", text):
        return False
    return None


def extract_facts(utterance: str, current_expected_item: Optional[str] = None) -> ExtractedFacts:
    """
    Master fact extraction combining all sub-extractors.
    Extracts all facts mentioned out-of-order in a single customer response.
    """
    prop_type = extract_property_type(utterance)
    ownership = extract_ownership_status(utterance)
    docs = extract_documents_available(utterance)
    occ, inc_mode = extract_occupation_and_income_mode(utterance)
    la, mv = extract_amounts(utterance)

    # Contextual adjustment: If the agent specifically asked for loan_amount or market_value,
    # assign a lone amount accordingly
    if current_expected_item == "loan_amount" and la is None and mv is not None:
        la = mv
        mv = None
    elif current_expected_item == "market_value" and mv is None and la is not None:
        mv = la
        la = None

    tenure = extract_tenure(utterance)
    existing_loan, emi_red = extract_transfer_intent(utterance)
    busy, cb_time = extract_busy_or_callback(utterance)
    is_div, div_topic, is_int, int_query = extract_diversion_or_interruption(utterance)
    confirm_ans = extract_confirmation_answer(utterance)

    # Verification detection
    text = utterance.lower()
    customer_verified = None
    if any(k in text for k in ["yes speaking", "speaking", "this is", "i am", "haan bol raha hu", "speaking here"]):
        customer_verified = True

    return ExtractedFacts(
        customer_verified=customer_verified,
        customer_busy=busy,
        callback_time=cb_time,
        property_type=prop_type,
        ownership_status=ownership,
        documents_available=docs,
        loan_amount=la,
        occupation=occ,
        income_mode=inc_mode,
        market_value=mv,
        tenure_years=tenure,
        existing_property_loan=True if existing_loan else None,
        emi_reduction_request=True if emi_red else None,
        is_diversion=is_div,
        diversion_topic=div_topic,
        is_interruption=is_int,
        interruption_query=int_query,
        confirmation_answer=confirm_ans,
    )
