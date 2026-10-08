# Deployment & Voice Platform Setup Guide — Home Credit LAP AI Voice Agent

## 1. Local Run
To run the server locally on Windows, macOS, or Linux:

```bash
# 1. Clone the repository
git clone https://github.com/REDDIPALLIPHANIKOUSHIK/Voice_Agent_Design.git
cd Voice_Agent_Design

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env from template
copy .env.example .env   # On Windows
# or: cp .env.example .env  # On Linux/macOS

# 4. Launch the application
python run.py
# or with dev reload:
python run.py --dev
```

The application will be live at:
- **Web Dashboard**: `http://localhost:8000/`
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`

---

## 2. Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and frontend
COPY src/ ./src/
COPY public/ ./public/
COPY run.py .
COPY .env.example .

ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["python", "run.py"]
```

### Build & Run
```bash
docker build -t home-credit-voice-agent .
docker run -p 8000:8000 home-credit-voice-agent
```

---

## 3. Retell AI Platform Integration

To connect the agent to **Retell AI** (telephony and WebRTC):
1. Sign up at [https://beta.retellai.com/](https://beta.retellai.com/)
2. Navigate to **Agents** $\rightarrow$ **Create New Agent**.
3. Under **Model / LLM**, select **Custom LLM** or **Retell LLM**.
   - If using Retell LLM: Copy the contents of [`docs/system-prompt.md`](./system-prompt.md) and paste directly into the **General Prompt** field.
   - Set Voice: Select a warm, professional Indian English voice (e.g. `11labs-Adrian` or `Retell Indian Female Voice`).
4. Set **Begin Message**:
   *"Hello, may I speak with {{customer_name}}? This is Ananya calling from Home Credit."*
5. Connect Webhook:
   - In Retell Dashboard, set the Webhook URL to:
     `https://<your-deployed-domain>/api/webhooks/retell`
6. Add your Retell credentials into your `.env`:
   ```env
   RETELL_API_KEY=key_xxxxxxxxxxxxxxxx
   RETELL_AGENT_ID=agent_xxxxxxxxxxxx
   ```

---

## 4. Bolna Platform Integration

To connect the agent to **Bolna AI**:
1. Sign up at [https://www.bolna.dev/](https://www.bolna.dev/)
2. Create a new Voice Agent for **Inbound / Outbound Calls**.
3. Under **Prompts**:
   - Paste the System Prompt from [`docs/system-prompt.md`](./system-prompt.md).
   - Configure language variables: `language_to_speak`: `English` or `Hindi`.
4. Select Voice:
   - English: `Polite Indian English (Female)`
   - Hindi: `Hindi Female (Natural conversational)`
5. Configure Webhook Endpoint:
   `https://<your-deployed-domain>/api/webhooks/bolna`
6. Add Bolna credentials into `.env`:
   ```env
   BOLNA_API_KEY=bolna_xxxxxxxxxxxxxxxx
   BOLNA_AGENT_ID=agent_xxxxxxxxxxxx
   ```

---

## 5. One-Click Cloud Deployment (Render / Railway / Fly.io)

### Deploying to Render
1. Connect your GitHub repository: `https://github.com/REDDIPALLIPHANIKOUSHIK/Voice_Agent_Design`.
2. Select **Web Service** with Python runtime.
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python run.py`
5. Set Environment Variables:
   - `HOST`: `0.0.0.0`
   - `PORT`: `10000`
