/**
 * Home Credit LAP Voice Agent — Interactive Client Application
 * Connects to FastAPI backend, supports Web Speech API STT/TTS,
 * real-time 7-question checklist tracking, and automated scenario simulation.
 */

let currentCallId = null;
let currentLanguage = "English";
let recognition = null;
let isRecording = false;
let synth = window.speechSynthesis || null;

// DOM Elements
const btnStartCall = document.getElementById("btnStartCall");
const btnEndCall = document.getElementById("btnEndCall");
const btnMic = document.getElementById("btnMic");
const micBtnText = document.getElementById("micBtnText");
const customerInput = document.getElementById("customerInput");
const btnSendUtterance = document.getElementById("btnSendUtterance");
const utteranceForm = document.getElementById("utteranceForm");
const languageSelect = document.getElementById("languageSelect");
const providerSelect = document.getElementById("providerSelect");
const agentStatusBadge = document.getElementById("agentStatusBadge");
const agentStatusText = document.getElementById("agentStatusText");
const callStageBadge = document.getElementById("callStageBadge");
const voiceHub = document.querySelector(".voice-hub");
const transcriptStream = document.getElementById("transcriptStream");
const stateJsonView = document.getElementById("stateJsonView");
const progressIndicator = document.getElementById("progressIndicator");
const decisionCard = document.getElementById("decisionCard");
const decisionIcon = document.getElementById("decisionIcon");
const decisionTitle = document.getElementById("decisionTitle");
const decisionDesc = document.getElementById("decisionDesc");
const scenarioSelector = document.getElementById("scenarioSelector");
const btnRunScenario = document.getElementById("btnRunScenario");
const scenarioDescription = document.getElementById("scenarioDescription");
const btnExportLog = document.getElementById("btnExportLog");

// Initialize Speech Recognition if supported in browser
function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = currentLanguage.toLowerCase() === "hindi" ? "hi-IN" : "en-IN";

    recognition.onstart = () => {
      isRecording = true;
      btnMic.classList.add("recording");
      micBtnText.textContent = "Listening...";
      voiceHub.classList.add("active");
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      customerInput.value = transcript;
      sendMessage(transcript);
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      stopRecording();
    };

    recognition.onend = () => {
      stopRecording();
    };
  } else {
    btnMic.title = "Speech recognition not supported in this browser. Use text input.";
  }
}

function startRecording() {
  if (recognition && !isRecording) {
    try {
      recognition.lang = currentLanguage.toLowerCase() === "hindi" ? "hi-IN" : "en-IN";
      recognition.start();
    } catch (e) {
      console.error(e);
    }
  }
}

function stopRecording() {
  isRecording = false;
  btnMic.classList.remove("recording");
  micBtnText.textContent = "Speak (Mic)";
  voiceHub.classList.remove("active");
}

// Speak Agent Reply
function speakText(text) {
  const selectedProvider = providerSelect.value;

  if (selectedProvider === "browser" && synth) {
    synth.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = currentLanguage.toLowerCase() === "hindi" ? "hi-IN" : "en-IN";
    utterance.rate = 1.0;
    utterance.pitch = 1.05;

    // Set animated speaking visualizer
    voiceHub.classList.add("speaking");
    utterance.onend = () => {
      voiceHub.classList.remove("speaking");
    };
    utterance.onerror = () => {
      voiceHub.classList.remove("speaking");
    };
    synth.speak(utterance);
  } else if (selectedProvider === "local" && currentCallId) {
    // Play synthesized server audio stream
    const audioUrl = `/api/call/${currentCallId}/audio?text=${encodeURIComponent(text)}&language=${encodeURIComponent(currentLanguage)}`;
    const audio = new Audio(audioUrl);
    voiceHub.classList.add("speaking");
    audio.onended = () => voiceHub.classList.remove("speaking");
    audio.onerror = () => voiceHub.classList.remove("speaking");
    audio.play().catch((err) => console.log("Audio playback notice:", err));
  } else {
    // Retell / Bolna simulation: trigger wave animation briefly
    voiceHub.classList.add("speaking");
    setTimeout(() => voiceHub.classList.remove("speaking"), 2500);
  }
}

// Start Call
async function startCall() {
  try {
    currentLanguage = languageSelect.value;
    const res = await fetch("/api/call/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_name: "Rahul Sharma",
        company_name: "Home Credit",
        agent_name: "Ananya",
        agent_gender: "female",
        language_to_speak: currentLanguage,
      }),
    });
    const data = await res.json();
    currentCallId = data.call_id;

    // Update UI state
    btnStartCall.disabled = true;
    btnEndCall.disabled = false;
    btnMic.disabled = false;
    customerInput.disabled = false;
    btnSendUtterance.disabled = false;
    languageSelect.disabled = true;

    agentStatusBadge.innerHTML = '<span class="status-dot live"></span><span>Call Active</span>';
    callStageBadge.textContent = `STAGE: ${data.call_stage.toUpperCase()}`;

    // Reset checklist & transcript
    resetChecklist();
    transcriptStream.innerHTML = "";
    appendTranscript("agent", data.greeting, "Greeting");

    // Speak initial greeting
    speakText(data.greeting);

    // Update state view
    updateStateView(data.state);
  } catch (err) {
    console.error("Start call failed:", err);
    alert("Failed to start call. Ensure the server is running.");
  }
}

// Send Customer Message
async function sendMessage(text) {
  if (!currentCallId || !text.trim()) return;

  appendTranscript("customer", text);
  customerInput.value = "";

  try {
    const res = await fetch("/api/call/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        call_id: currentCallId,
        message: text,
      }),
    });
    const data = await res.json();

    appendTranscript("agent", data.reply, data.call_stage);
    speakText(data.reply);
    updateStateView(data.state);

    callStageBadge.textContent = `STAGE: ${data.call_stage.toUpperCase()}`;

    if (data.call_ended) {
      handleCallEndOutcome(data);
    }
  } catch (err) {
    console.error("Send message error:", err);
  }
}

// End Call Manually
async function endCall() {
  if (!currentCallId) return;

  try {
    await fetch(`/api/call/${currentCallId}/end`, { method: "POST" });
  } catch (e) {}

  finishCallUI("Call Ended Manually");
}

function handleCallEndOutcome(data) {
  if (data.disqualified) {
    finishCallUI("Customer Disqualified", "disqualified");
    decisionCard.className = "decision-card disqualified";
    decisionIcon.textContent = "❌";
    decisionTitle.textContent = "Disqualified";
    decisionDesc.textContent = data.state.disqualification_reason || "Criteria not met.";
  } else if (data.transfer_required) {
    finishCallUI("Specialist Transfer", "transfer");
    decisionCard.className = "decision-card transfer";
    decisionIcon.textContent = "🔄";
    decisionTitle.textContent = "Transferred to Specialist";
    decisionDesc.textContent = data.state.transfer_reason || "Existing loan / EMI transfer.";
  } else if (data.handoff_required) {
    finishCallUI("Qualified & Handed Off", "qualified");
    decisionCard.className = "decision-card qualified";
    decisionIcon.textContent = "✅";
    decisionTitle.textContent = "Qualified for LAP Offer!";
    decisionDesc.textContent = "All 7 data points verified. Lead handed off to Senior Loan Expert.";
  } else {
    finishCallUI("Call Ended");
  }
}

function finishCallUI(statusText, type = "standby") {
  btnStartCall.disabled = false;
  btnEndCall.disabled = true;
  btnMic.disabled = true;
  customerInput.disabled = true;
  btnSendUtterance.disabled = true;
  languageSelect.disabled = false;
  voiceHub.classList.remove("active", "speaking");

  agentStatusBadge.innerHTML = `<span class="status-dot ${type}"></span><span>${statusText}</span>`;
  callStageBadge.textContent = "STAGE: TERMINATED";
}

// Append Chat Bubble
function appendTranscript(speaker, text, stage) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${speaker}`;

  const meta = document.createElement("div");
  meta.className = "bubble-meta";
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  meta.innerHTML = `<span>${speaker === "agent" ? "🤖 Agent Ananya" : "👤 Customer"}</span> · <span>${time}</span>`;
  if (stage) {
    meta.innerHTML += ` · <span class="stage-tag">${stage}</span>`;
  }

  const content = document.createElement("div");
  content.className = "bubble-content";
  content.textContent = text;

  bubble.appendChild(meta);
  bubble.appendChild(content);
  transcriptStream.appendChild(bubble);
  transcriptStream.scrollTop = transcriptStream.scrollHeight;
}

// Update Checklist & State View
function updateStateView(state) {
  stateJsonView.textContent = JSON.stringify(state, null, 2);

  let completedCount = 0;

  // 1. Property Type
  updateCheckItem(
    "property_type",
    state.property_type,
    state.property_type ? state.property_type.toUpperCase() : null
  );
  if (state.property_type) completedCount++;

  // 2. Ownership
  updateCheckItem(
    "ownership_status",
    state.ownership_status,
    state.ownership_status ? state.ownership_status.toUpperCase() : null
  );
  if (state.ownership_status) completedCount++;

  // 3. Documents
  updateCheckItem(
    "documents_available",
    state.documents_available,
    state.documents_available ? state.documents_available.toUpperCase() : null
  );
  if (state.documents_available) completedCount++;

  // 4. Loan Amount
  const laText = state.loan_amount ? `₹${(state.loan_amount / 100000).toFixed(1)} Lakh` : null;
  updateCheckItem("loan_amount", state.loan_amount, laText);
  if (state.loan_amount) completedCount++;

  // 5. Occupation & Income
  let occText = null;
  if (state.occupation && state.income_mode) {
    occText = `${state.occupation} (${state.income_mode})`;
  } else if (state.occupation) {
    occText = state.occupation;
  }
  updateCheckItem("occupation_income_mode", state.occupation && state.income_mode, occText);
  if (state.occupation && state.income_mode) completedCount++;

  // 6. Market Value
  const mvText = state.market_value
    ? state.market_value >= 10000000
      ? `₹${(state.market_value / 10000000).toFixed(2)} Crore`
      : `₹${(state.market_value / 100000).toFixed(1)} Lakh`
    : null;
  updateCheckItem("market_value", state.market_value, mvText);
  if (state.market_value) completedCount++;

  // 7. Tenure
  const tenText = state.tenure_years ? `${state.tenure_years} Years` : null;
  updateCheckItem("tenure_years", state.tenure_years, tenText);
  if (state.tenure_years) completedCount++;

  progressIndicator.textContent = `${completedCount} / 7 Completed`;

  // Highlight current missing item
  highlightCurrentItem(state.current_checklist_item);
}

function updateCheckItem(id, isAnswered, displayText) {
  const itemEl = document.getElementById(`item_${id}`);
  const valEl = document.getElementById(`val_${id}`);
  const badgeEl = document.getElementById(`badge_${id}`);

  if (isAnswered) {
    itemEl.classList.add("completed");
    valEl.textContent = `✓ ${displayText}`;
    badgeEl.textContent = "Verified";
  } else {
    itemEl.classList.remove("completed");
    valEl.textContent = "— Pending";
    badgeEl.textContent = "Pending";
  }
}

function highlightCurrentItem(currentItem) {
  const items = [
    "property_type",
    "ownership_status",
    "documents_available",
    "loan_amount",
    "occupation_income_mode",
    "market_value",
    "tenure_years",
  ];
  items.forEach((id) => {
    const el = document.getElementById(`item_${id}`);
    if (el) el.classList.remove("active");
  });

  if (currentItem) {
    const activeEl = document.getElementById(`item_${currentItem}`);
    if (activeEl) activeEl.classList.add("active");
  }
}

function resetChecklist() {
  const items = [
    "property_type",
    "ownership_status",
    "documents_available",
    "loan_amount",
    "occupation_income_mode",
    "market_value",
    "tenure_years",
  ];
  items.forEach((id) => {
    const itemEl = document.getElementById(`item_${id}`);
    const valEl = document.getElementById(`val_${id}`);
    const badgeEl = document.getElementById(`badge_${id}`);
    itemEl.classList.remove("completed", "active");
    valEl.textContent = "— Pending";
    badgeEl.textContent = "Pending";
  });
  progressIndicator.textContent = "0 / 7 Completed";
  decisionCard.className = "decision-card";
  decisionIcon.textContent = "⚖️";
  decisionTitle.textContent = "Evaluating Lead...";
  decisionDesc.textContent = "Awaiting customer eligibility responses.";
}

// Preset Scenario Simulation Runner
async function runPresetScenario() {
  const scenarioId = scenarioSelector.value;
  if (!scenarioId) {
    alert("Please select a scenario to simulate.");
    return;
  }

  btnRunScenario.disabled = true;
  btnRunScenario.textContent = "Running...";
  resetChecklist();
  transcriptStream.innerHTML = "";

  try {
    const res = await fetch("/api/scenarios/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_id: scenarioId }),
    });
    const data = await res.json();

    // Render dialogue turn by turn with delay for realistic preview
    for (let i = 0; i < data.trace.length; i++) {
      const turn = data.trace[i];
      appendTranscript(turn.speaker, turn.text, turn.stage);
      await new Promise((r) => setTimeout(r, 200));
    }

    // Update state & decision
    updateStateView(data.final_state);
    const dec = data.decision;

    if (dec.disqualified) {
      decisionCard.className = "decision-card disqualified";
      decisionIcon.textContent = "❌";
      decisionTitle.textContent = "Disqualified";
      decisionDesc.textContent = dec.disqualification_reason || "Disqualified by deterministic rule.";
      agentStatusBadge.innerHTML = '<span class="status-dot disqualified"></span><span>Disqualified</span>';
    } else if (dec.transfer_required) {
      decisionCard.className = "decision-card transfer";
      decisionIcon.textContent = "🔄";
      decisionTitle.textContent = "Transferred to Specialist";
      decisionDesc.textContent = dec.transfer_reason || "Existing loan / EMI transfer.";
      agentStatusBadge.innerHTML = '<span class="status-dot transfer"></span><span>Specialist Transfer</span>';
    } else if (dec.handoff_required) {
      decisionCard.className = "decision-card qualified";
      decisionIcon.textContent = "✅";
      decisionTitle.textContent = "Qualified for LAP Offer!";
      decisionDesc.textContent = "All 7 data points satisfied. Transferred to Senior Loan Expert.";
      agentStatusBadge.innerHTML = '<span class="status-dot live"></span><span>Qualified & Handed Off</span>';
    }

    callStageBadge.textContent = `SIMULATION COMPLETE: ${scenarioId}`;
  } catch (err) {
    console.error("Scenario simulation error:", err);
  } finally {
    btnRunScenario.disabled = false;
    btnRunScenario.textContent = "Run Simulation";
  }
}

// Export Call Log
function exportCallLog() {
  const bubbles = document.querySelectorAll(".chat-bubble");
  if (bubbles.length === 0) {
    alert("No active conversation log to export.");
    return;
  }

  let textLog = "=====================================================\n";
  textLog += "Home Credit LAP AI Voice Agent — Call Transcript Log\n";
  textLog += `Exported: ${new Date().toISOString()}\n`;
  textLog += "=====================================================\n\n";

  bubbles.forEach((b) => {
    const speaker = b.classList.contains("agent") ? "Agent Ananya" : "Customer";
    const text = b.querySelector(".bubble-content").textContent;
    textLog += `[${speaker}]: ${text}\n\n`;
  });

  textLog += "\n=====================================================\n";
  textLog += "Final Qualification State:\n";
  textLog += stateJsonView.textContent;
  textLog += "\n=====================================================\n";

  const blob = new Blob([textLog], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `home_credit_call_log_${Date.now()}.txt`;
  a.click();
}

// Event Listeners
btnStartCall.addEventListener("click", startCall);
btnEndCall.addEventListener("click", endCall);

btnMic.addEventListener("click", () => {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
});

utteranceForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(customerInput.value);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    if (!currentCallId) {
      startCall().then(() => {
        setTimeout(() => sendMessage(chip.getAttribute("data-phrase")), 500);
      });
    } else {
      customerInput.value = chip.getAttribute("data-phrase");
      sendMessage(chip.getAttribute("data-phrase"));
    }
  });
});

scenarioSelector.addEventListener("change", () => {
  const selected = scenarioSelector.value;
  if (selected) {
    scenarioDescription.textContent = `Ready to simulate scenario ${selected}. Click "Run Simulation" to observe sequential execution.`;
  }
});

btnRunScenario.addEventListener("click", runPresetScenario);
btnExportLog.addEventListener("click", exportCallLog);

// Initialize Web Speech on load
setupSpeechRecognition();
