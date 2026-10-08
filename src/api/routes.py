"""
FastAPI Routes for Home Credit LAP Voice Agent.
Provides REST and WebSocket endpoints for call lifecycle, real-time voice,
preset scenario execution, Retell/Bolna webhooks, and state inspection.
"""

import uuid
import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.engine.models import QualificationState, CallSession, UtteranceLog
from src.engine.orchestrator import ConversationOrchestrator
from src.providers.local_tts import LocalTTSProvider
from src.providers.retell import RetellAIProvider
from src.providers.bolna import BolnaProvider

router = APIRouter(prefix="/api")

# In-memory session store
sessions: Dict[str, CallSession] = {}
orchestrators: Dict[str, ConversationOrchestrator] = {}

tts_provider = LocalTTSProvider()
retell_provider = RetellAIProvider()
bolna_provider = BolnaProvider()


class StartCallRequest(BaseModel):
    customer_name: str = "Rahul Sharma"
    company_name: str = "Home Credit"
    agent_name: str = "Ananya"
    agent_gender: str = "female"
    language_to_speak: str = "English"
    rag_context: Optional[str] = None


class SendMessageRequest(BaseModel):
    call_id: str
    message: str


class RunScenarioRequest(BaseModel):
    scenario_id: str


# Preset Test Scenarios (T01-T12, A01-A08)
PRESET_SCENARIOS = {
    "T01": {
        "title": "T01 - Perfect Eligible Customer",
        "description": "Residential, Sole owner, Original docs, ₹50 Lakh, Salaried, Bank income, ₹1 Crore value, 10 Years tenure.",
        "expected": "QUALIFIED -> HANDOFF to Senior Loan Expert",
        "utterances": [
            "Yes, this is Rahul speaking.",
            "It is a residential house.",
            "I am the sole owner of the property.",
            "Yes, I have the original documents ready at home.",
            "I need around 50 lakhs.",
            "I am salaried and my income comes directly into my bank account.",
            "The market value is approximately 1 crore.",
            "I would like a repayment period of 10 years."
        ]
    },
    "T02": {
        "title": "T02 - Agricultural Property Disqualification",
        "description": "Customer specifies agricultural land -> immediate disqualification.",
        "expected": "Immediate Disqualification -> Call Ended",
        "utterances": [
            "Speaking.",
            "The property is agricultural land used for farming."
        ]
    },
    "T03": {
        "title": "T03 - Cash Income Disqualification",
        "description": "Salaried but receives income in cash -> immediate disqualification.",
        "expected": "Immediate Disqualification -> Call Ended",
        "utterances": [
            "Yes Rahul here.",
            "It's a residential apartment.",
            "Sole owner.",
            "Yes original papers are with me.",
            "Looking for 30 lakhs.",
            "I am salaried but my employer gives my salary in cash."
        ]
    },
    "T04": {
        "title": "T04 - Missing Originals (Photocopy only)",
        "description": "Customer has only photocopies / duplicates -> immediate disqualification.",
        "expected": "Immediate Disqualification -> Call Ended",
        "utterances": [
            "Yes speaking.",
            "It's a commercial shop.",
            "Jointly owned with my brother.",
            "I only have photocopies, not the originals."
        ]
    },
    "T05": {
        "title": "T05 - Tenure Too Short (2 Years)",
        "description": "Repayment tenure requested is 2 years (minimum is 3 years) -> rejected.",
        "expected": "Immediate Disqualification -> Call Ended",
        "utterances": [
            "Yes speaking.",
            "Residential house.",
            "Sole owner.",
            "Yes original documents are available.",
            "40 lakhs.",
            "Salaried, bank account.",
            "Market value is 80 lakhs.",
            "I want to repay it in 2 years."
        ]
    },
    "T06": {
        "title": "T06 - Tenure Too Long (20 Years)",
        "description": "Repayment tenure requested is 20 years (maximum is 15 years) -> rejected.",
        "expected": "Immediate Disqualification -> Call Ended",
        "utterances": [
            "Yes Rahul here.",
            "Residential flat.",
            "Sole owner.",
            "Yes originals are at home.",
            "50 lakhs.",
            "Self-employed, income credited into bank account.",
            "Market value around 90 lakhs.",
            "I need 20 years to repay."
        ]
    },
    "T07": {
        "title": "T07 - Loan Amount > ₹75 Lakh Capping",
        "description": "Customer asks for ₹90 Lakh -> Offered max ₹75 Lakh -> Customer agrees -> Continues.",
        "expected": "Offer Max ₹75L -> Customer Agrees -> Qualification Continues",
        "utterances": [
            "Yes speaking.",
            "Commercial office space.",
            "Sole ownership.",
            "Original papers ready.",
            "I need 90 lakhs.",
            "Yes, I would like to proceed with the maximum eligible amount of 75 lakhs.",
            "Self-employed with bank deposits.",
            "Market value is 1.5 crore.",
            "12 years tenure."
        ]
    },
    "T08": {
        "title": "T08 - Joint Ownership (Fully Eligible)",
        "description": "Customer has joint ownership with spouse -> Both sole and joint are eligible.",
        "expected": "Eligible -> Continues Qualification",
        "utterances": [
            "Speaking.",
            "It's a residential flat.",
            "It is jointly owned with my wife.",
            "Yes original documents are available.",
            "35 lakhs.",
            "Salaried, bank account.",
            "Market value 70 lakhs.",
            "8 years tenure."
        ]
    },
    "T09": {
        "title": "T09 - Existing Property Loan Transfer",
        "description": "Customer mentions existing loan on the property -> routed to loan-transfer specialist.",
        "expected": "Specialist Transfer -> Call Ended",
        "utterances": [
            "Yes speaking.",
            "I already have a loan running on this property."
        ]
    },
    "T10": {
        "title": "T10 - EMI Reduction Intent",
        "description": "Customer wants to reduce EMI -> balance transfer specialist handoff.",
        "expected": "Specialist Transfer -> Call Ended",
        "utterances": [
            "Yes speaking.",
            "I want to reduce my EMI on my current property loan."
        ]
    },
    "T11": {
        "title": "T11 - Out-of-Order Multi-Fact Response",
        "description": "Customer states: 'It is a residential house, jointly owned with my wife, and worth around 80 lakhs.' -> Bot remembers all three without re-asking.",
        "expected": "Extracts 3 facts simultaneously -> Skips redundant questions -> Asks Document availability next",
        "utterances": [
            "Yes speaking.",
            "It's a residential house, jointly owned with my wife, and worth around 80 lakhs."
        ]
    },
    "T12": {
        "title": "T12 - Busy Customer Flow",
        "description": "Customer is in a meeting -> Bot captures preferred callback time and ends call politely.",
        "expected": "Callback Scheduled -> Call Ended",
        "utterances": [
            "I'm in a meeting right now, please call me back around 5 pm."
        ]
    },
    "A01": {
        "title": "A01 - Adversarial Contradiction",
        "description": "'It's residential... actually it's agricultural.' -> Corrects to agricultural and disqualifies.",
        "expected": "Correction detected -> Agricultural Disqualification",
        "utterances": [
            "Yes speaking.",
            "It's residential... actually it's agricultural."
        ]
    },
    "A02": {
        "title": "A02 - Adversarial Multi-Fact Utterance",
        "description": "'It's my own house, original papers are available and I need around 40 lakhs.'",
        "expected": "Extracts: Residential, Sole, Originals, 40 Lakhs -> Asks Occupation next",
        "utterances": [
            "Yes speaking.",
            "It's my own house, original papers are available and I need around 40 lakhs."
        ]
    },
    "A03": {
        "title": "A03 - Customer Interruption",
        "description": "Customer interrupts: 'Wait, what documents do you need?' -> Bot explains and returns to flow.",
        "expected": "Interruption Answered -> Returns to current checklist question",
        "utterances": [
            "Yes speaking.",
            "Wait, what documents do you need?"
        ]
    },
    "A04": {
        "title": "A04 - Adversarial Interest Rate Diversion",
        "description": "Customer asks 'What interest rate do you offer?' -> No hallucination, defers to senior expert.",
        "expected": "No Rate Hallucination -> Defer to Senior Expert -> Continue Qualification",
        "utterances": [
            "Yes speaking.",
            "What interest rate do you offer?"
        ]
    },
    "A05": {
        "title": "A05 - Corrected Tenure",
        "description": "'10 years... actually make that 15.' -> Accurately updates tenure to 15.",
        "expected": "Tenure stored as 15 years",
        "utterances": [
            "Yes speaking.",
            "Residential house.",
            "Sole owner.",
            "Original papers ready.",
            "50 lakhs.",
            "Salaried, bank.",
            "Market value 90 lakhs.",
            "10 years... actually make that 15."
        ]
    },
    "A06": {
        "title": "A06 - Corrected Income Mode to Cash",
        "description": "'Bank... actually cash.' -> Corrects to cash and triggers immediate disqualification.",
        "expected": "Cash Disqualification",
        "utterances": [
            "Yes speaking.",
            "Residential flat.",
            "Sole owner.",
            "Original documents available.",
            "40 lakhs.",
            "Salaried, bank... actually cash."
        ]
    },
    "A07": {
        "title": "A07 - All 7 Facts in a Single Utterance",
        "description": "Customer provides all 7 eligibility data points in one single burst.",
        "expected": "Extracts all 7 -> Qualifies immediately -> Senior Expert Handoff",
        "utterances": [
            "Yes speaking.",
            "It is a residential property sole owned with original papers, I need 50 lakhs, I am salaried with bank credit, market value is 1 crore and tenure is 10 years."
        ]
    }
}


@router.post("/call/start")
async def start_call(req: StartCallRequest):
    call_id = str(uuid.uuid4())
    state = QualificationState(
        customer_name=req.customer_name,
        company_name=req.company_name,
        agent_name=req.agent_name,
        agent_gender=req.agent_gender,
        language_to_speak=req.language_to_speak,
    )
    orchestrator = ConversationOrchestrator(state=state, rag_context=req.rag_context)
    greeting = orchestrator.generate_initial_greeting()

    now = datetime.datetime.now().isoformat()
    session = CallSession(
        call_id=call_id,
        start_time=now,
        state=state,
        transcript=[
            UtteranceLog(speaker="agent", text=greeting, timestamp=now, stage=state.call_stage.value)
        ],
        rag_context=req.rag_context,
    )

    sessions[call_id] = session
    orchestrators[call_id] = orchestrator

    return {
        "call_id": call_id,
        "greeting": greeting,
        "state": state.model_dump(),
        "call_stage": state.call_stage.value,
    }


@router.post("/call/message")
async def send_message(req: SendMessageRequest):
    call_id = req.call_id
    if call_id not in sessions:
        raise HTTPException(status_code=404, detail="Call session not found")

    session = sessions[call_id]
    orchestrator = orchestrators[call_id]

    # Log customer utterance
    now = datetime.datetime.now().isoformat()
    session.transcript.append(
        UtteranceLog(speaker="customer", text=req.message, timestamp=now, stage=session.state.call_stage.value)
    )

    # Process through orchestrator
    reply_text, updated_state = orchestrator.process_utterance(req.message)
    session.state = updated_state

    # Log agent reply
    now_reply = datetime.datetime.now().isoformat()
    session.transcript.append(
        UtteranceLog(speaker="agent", text=reply_text, timestamp=now_reply, stage=updated_state.call_stage.value)
    )

    return {
        "call_id": call_id,
        "reply": reply_text,
        "state": updated_state.model_dump(),
        "call_stage": updated_state.call_stage.value,
        "call_ended": updated_state.call_ended,
        "disqualified": updated_state.disqualified,
        "transfer_required": updated_state.transfer_required,
        "handoff_required": updated_state.handoff_required,
    }


@router.get("/call/{call_id}/state")
async def get_call_state(call_id: str):
    if call_id not in sessions:
        raise HTTPException(status_code=404, detail="Call session not found")
    session = sessions[call_id]
    return {
        "call_id": call_id,
        "state": session.state.model_dump(),
        "answered_count": session.state.get_answered_items_count(),
        "is_complete": session.state.is_all_seven_answered(),
    }


@router.get("/call/{call_id}/transcript")
async def get_call_transcript(call_id: str):
    if call_id not in sessions:
        raise HTTPException(status_code=404, detail="Call session not found")
    session = sessions[call_id]
    return {
        "call_id": call_id,
        "start_time": session.start_time,
        "transcript": [t.model_dump() for t in session.transcript],
        "state": session.state.model_dump(),
    }


@router.post("/call/{call_id}/end")
async def end_call(call_id: str):
    if call_id not in sessions:
        raise HTTPException(status_code=404, detail="Call session not found")
    sessions[call_id].state.call_ended = True
    return {"status": "call_ended", "call_id": call_id}


@router.get("/call/{call_id}/audio")
async def get_audio_speech(call_id: str, text: str, language: str = "English"):
    """
    Generates and returns streaming MP3 audio for agent speech.
    """
    try:
        audio_bytes = await tts_provider.synthesize_speech(text, language=language)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio synthesis error: {str(e)}")


@router.get("/scenarios")
async def list_scenarios():
    """
    Returns list of preset scenarios for the evaluator dashboard.
    """
    return [
        {"id": k, "title": v["title"], "description": v["description"], "expected": v["expected"]}
        for k, v in PRESET_SCENARIOS.items()
    ]


@router.post("/scenarios/run")
async def run_scenario(req: RunScenarioRequest):
    """
    Runs a preset scenario through the live orchestrator and returns full execution trace.
    """
    sc_id = req.scenario_id
    if sc_id not in PRESET_SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Scenario '{sc_id}' not found")

    sc_data = PRESET_SCENARIOS[sc_id]
    call_id = f"test_{sc_id.lower()}_{uuid.uuid4().hex[:6]}"
    state = QualificationState(customer_name="Rahul Sharma")
    orchestrator = ConversationOrchestrator(state=state)

    trace = []
    greeting = orchestrator.generate_initial_greeting()
    trace.append({"speaker": "agent", "text": greeting, "stage": state.call_stage.value})

    for customer_msg in sc_data["utterances"]:
        trace.append({"speaker": "customer", "text": customer_msg})
        reply, curr_state = orchestrator.process_utterance(customer_msg)
        trace.append({
            "speaker": "agent",
            "text": reply,
            "stage": curr_state.call_stage.value,
            "disqualified": curr_state.disqualified,
            "transfer": curr_state.transfer_required,
            "handoff": curr_state.handoff_required,
        })
        if curr_state.call_ended:
            break

    return {
        "scenario_id": sc_id,
        "title": sc_data["title"],
        "expected": sc_data["expected"],
        "trace": trace,
        "final_state": state.model_dump(),
        "decision": {
            "disqualified": state.disqualified,
            "disqualification_reason": state.disqualification_reason,
            "transfer_required": state.transfer_required,
            "transfer_reason": state.transfer_reason,
            "handoff_required": state.handoff_required,
            "all_seven_answered": state.is_all_seven_answered(),
        }
    }


# Webhook endpoints for Retell AI & Bolna
@router.post("/webhooks/retell")
async def retell_webhook(payload: Dict[str, Any]):
    return await retell_provider.handle_webhook_event(payload)


@router.post("/webhooks/bolna")
async def bolna_webhook(payload: Dict[str, Any]):
    return {"status": "received", "provider": "bolna"}
