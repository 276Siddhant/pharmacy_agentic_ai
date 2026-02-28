import uuid
import streamlit as st

# ── Utils ─────────────────────────────────────────────
from utils.session import init_session
from utils.emergency_detector import is_emergency
from utils.drug_detector import is_restricted_drug, get_detected_drug

# ── Components ────────────────────────────────────────
from components.chat import render_chat_history
from components.sidebar import render_sidebar
from components.quick_actions import render_quick_actions
from components.emergency_alert import render_emergency_alert
from components.prescription_upload import render_prescription_upload
from components.receipt import render_receipt

# ── Services ──────────────────────────────────────────
from services.api_client import call_chat, safe_call


# ═══════════════════════════════════════════════════════
# ⚙️ PAGE CONFIG
# ═══════════════════════════════════════════════════════

st.set_page_config(
    page_title="AI Pharmacy Assistant",
    page_icon="💊",
    layout="wide",
)

init_session()
render_sidebar()


# ═══════════════════════════════════════════════════════
# 🚨 EMERGENCY ROUTE
# ═══════════════════════════════════════════════════════

if st.session_state.ui_phase == "emergency_alert":
    render_emergency_alert(st.session_state.get("last_user_input", ""))
    st.stop()


# ═══════════════════════════════════════════════════════
# 📋 PRESCRIPTION ROUTE
# ═══════════════════════════════════════════════════════

if st.session_state.ui_phase == "prescription_upload":
    render_prescription_upload()
    st.stop()


# ═══════════════════════════════════════════════════════
# 💬 NORMAL CHAT FLOW
# ═══════════════════════════════════════════════════════

clicked_prompt = render_quick_actions()
render_chat_history()
render_receipt()

prefill = clicked_prompt or ""

user_input = st.chat_input(
    placeholder="Ask about medications, symptoms, or drug interactions..."
)

if not user_input and prefill:
    user_input = prefill


# ═══════════════════════════════════════════════════════
# 🧠 MESSAGE HANDLER
# ═══════════════════════════════════════════════════════

if user_input:

    st.session_state.last_user_input = user_input
    st.session_state.is_first_message = False

    # 🚨 Emergency guard
    if is_emergency(user_input):
        st.session_state.ui_phase = "emergency_alert"
        st.rerun()

    # 📋 Prescription guard
    if is_restricted_drug(user_input):
        st.session_state.ui_phase = "prescription_upload"
        st.session_state.pending_prescription = get_detected_drug(user_input)
        st.rerun()

    # Append user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
    })

    # 🔥 REAL BACKEND CALL
    user_id = "PAT004"  # can make dynamic later

    backend_response = safe_call(call_chat, user_id, user_input)

    # Handle backend safely
    if isinstance(backend_response, str):
        ai_message = backend_response
        trace_logs = []
        recommendations = []
    else:
        ai_message = backend_response.get("message", "")
        trace_logs = backend_response.get("trace", [])
        recommendations = backend_response.get("recommendations", [])

    # ✅ Inject recommendations into message
    if recommendations:
        ai_message += "\n\n---\n"
        ai_message += "### 🩺 Recommended Medicines\n"
        for item in recommendations:
            ai_message += (
            f"\n**{item['name']}**  \n"
            f"💶 €{item['price']} | 📦 Stock: {item['stock']}  \n"
            f"🧠 *Why recommended:* {item.get('reason', 'Supports your symptom.')}  \n"
        )
        


    # Append assistant message
    st.session_state.messages.append({
        "role": "assistant",
        "content": ai_message,
        "agent_logs": [
            {
                "agent": "🧠 Backend Trace",
                "log": "\n".join(trace_logs) if trace_logs else "No trace available."
            }
        ]
    })

    st.rerun()