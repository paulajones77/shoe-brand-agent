import os, asyncio, requests
from flask import Flask, request, jsonify

# --- Agents SDK imports ---
from agents import Agent, Runner, function_tool  # Agents SDK (Python)
# Docs: https://openai.github.io/openai-agents-python/quickstart/

# ========== TOOL: Google Sheet FAQ lookup ==========
@function_tool
def lookup_faq(question: str) -> str:
    """
    Fetch a live FAQ answer from our Google Sheet via the hosted API.
    Args:
        question: The customer's question to look up.
    """
    url = "https://shoe-faq-agent-production.up.railway.app/lookup"
    r = requests.post(url, json={"question": question}, timeout=12)
    r.raise_for_status()
    data = r.json()
    return data.get("answer", "No matching answer found.")

# ========== AGENT ==========
agent = Agent(
    name="Shoe Brand Agent",
    instructions=(
        "You are the support & catalog agent for our shoe brand. "
        "For FAQs, policies, campaigns or promotions, call the `lookup_faq` tool. "
        "Answer clearly and keep it brand-consistent."
    ),
    tools=[lookup_faq],   # You can add Shopify later as a separate tool.
)

# ========== Tiny web API so you can call the agent ==========
app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    """
    Body: { "question": "user message" }
    Returns: { "answer": "agent reply" }
    """
    q = (request.json or {}).get("question", "").strip()
    if not q:
        return jsonify({"error": "Missing 'question'"}), 400

    # Runner.run is async → run once synchronously
    result = asyncio.run(Runner.run(agent, q))
    return jsonify({"answer": result.final_output})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "agent": agent.name})

if __name__ == "__main__":
    # Local dev run; on Railway we just need a web process listening on $PORT
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
