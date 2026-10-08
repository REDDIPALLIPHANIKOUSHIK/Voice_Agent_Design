"""
Main Application Entry Point for Home Credit LAP Voice Agent.
Serves the REST API, WebSocket streams, and mounts the interactive frontend dashboard.
"""

import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from src.api.routes import router as api_router, sessions, orchestrators, tts_provider
from src.engine.models import UtteranceLog

app = FastAPI(
    title="Home Credit LAP AI Voice Agent",
    description="SalesAgents AI Voice Agent for Home Credit Loan Against Property Qualification",
    version="1.0.0",
)

# Enable CORS for local testing / cross-origin web calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


# WebSocket endpoint for real-time live voice & state streaming
@app.websocket("/ws/call/{call_id}")
async def websocket_call_endpoint(websocket: WebSocket, call_id: str):
    await websocket.accept()
    if call_id not in sessions:
        await websocket.send_json({"error": "Call session not found"})
        await websocket.close()
        return

    session = sessions[call_id]
    orchestrator = orchestrators[call_id]

    # Send initial state
    await websocket.send_json({
        "type": "connected",
        "call_id": call_id,
        "state": session.state.model_dump(),
        "transcript": [t.model_dump() for t in session.transcript],
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "customer_utterance":
                text = data.get("text", "").strip()
                if not text:
                    continue

                # Process customer utterance
                reply_text, updated_state = orchestrator.process_utterance(text)

                # Broadcast updated state & agent reply
                await websocket.send_json({
                    "type": "agent_reply",
                    "reply": reply_text,
                    "state": updated_state.model_dump(),
                    "call_stage": updated_state.call_stage.value,
                    "call_ended": updated_state.call_ended,
                    "disqualified": updated_state.disqualified,
                    "transfer_required": updated_state.transfer_required,
                    "handoff_required": updated_state.handoff_required,
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass


# Mount static files for the dashboard UI
public_dir = Path(__file__).resolve().parent.parent / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=str(public_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.main:app", host=host, port=port, reload=True)
