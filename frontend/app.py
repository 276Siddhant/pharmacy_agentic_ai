"""
app.py
-------
Master entry point for AI Pharmacy Assistant.
Run with:
    streamlit run app.py
"""

import streamlit as st

# ── Utils ─────────────────────────────────────────────
from utils.session import init_session
from utils.emergency_detector import is_emergency
from utils.drug_detector import is_restricted_drug, get_detected_drug

# ── Components ────────────────────────────────────────
from components.onboarding import render_onboarding
from components.chat import render_chat_history, render_streaming_response
from components.agent_display import run_all_agents
from components.sidebar import render_sidebar
from components.quick_actions import render_quick_actions
from components.emergency_alert import render_emergency_alert
from components.prescription_upload import render_prescription_upload
from components.receipt import render_receipt
from styles.injector import inject_global_css

# ── Services ──────────────────────────────────────────
from services.api_client import (
    call_final_streamed,
    call_transcribe,
    safe_call,
    call_finalize_checkout
)

# ═══════════════════════════════════════════════════════
# ⚙️ PAGE CONFIG
# ═══════════════════════════════════════════════════════

st.set_page_config(
    page_title="AI Pharmacy Assistant",
    page_icon="💊",
    layout="wide",
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# 🔧 SESSION INIT
# ═══════════════════════════════════════════════════════

init_session()
inject_global_css()

if st.session_state.ui_phase == "onboarding":
    render_onboarding()
    st.stop()

render_sidebar()

# ═══════════════════════════════════════════════════════
# 🚨 SPECIAL ROUTES
# ═══════════════════════════════════════════════════════

if st.session_state.ui_phase == "emergency_alert":
    render_emergency_alert(st.session_state.get("last_user_input", ""))
    st.stop()

if st.session_state.ui_phase == "prescription_upload":
    render_prescription_upload()
    st.stop()

if st.session_state.ui_phase == "storefront":
    from components.storefront import render_storefront
    render_storefront()
    st.stop()

# ═══════════════════════════════════════════════════════
# 💬 NORMAL CHAT FLOW
# ═══════════════════════════════════════════════════════

clicked_prompt = render_quick_actions()
render_chat_history()
render_receipt()

# 🎙️ Voice Input
voice_text = None
with st.expander("🎙️ Voice Input", expanded=False):
    audio = st.audio_input("Speak your question")
    if audio:
        with st.spinner("Transcribing..."):
            voice_text = safe_call(call_transcribe, audio.read())

user_input = st.chat_input("Ask about medications...")

display_input = None
llm_input = None

if st.session_state.get("checkout_prompt"):
    llm_input = st.session_state.checkout_prompt
    display_input = "🛒 I would like to purchase the items in my cart."
    st.session_state.checkout_prompt = None
else:
    active_input = user_input or voice_text or clicked_prompt
    if active_input:
        llm_input = active_input
        display_input = active_input

# ═══════════════════════════════════════════════════════
# 🧠 PROCESSING LOGIC
# ═══════════════════════════════════════════════════════

if llm_input and display_input:

    st.session_state.last_user_input = llm_input
    st.session_state.is_first_message = False

    # 🚨 Emergency
    if is_emergency(llm_input):
        st.session_state.ui_phase = "emergency_alert"
        st.rerun()

    # 📋 Prescription upload redirect
    if is_restricted_drug(llm_input):
        st.session_state.ui_phase = "prescription_upload"
        st.session_state.pending_prescription = get_detected_drug(llm_input)
        st.rerun()

    # Append user message
    st.session_state.messages.append({
        "role": "user",
        "content": display_input
    })

    # Call backend normally (validation phase)
    backend_response = safe_call(call_final_streamed, llm_input)

    # 🟢 READY TO CONFIRM ORDER
    if isinstance(backend_response, dict) and backend_response.get("status") == "ready_to_confirm":

        st.session_state.pending_order = backend_response["order_data"]

        st.session_state.messages.append({
            "role": "assistant",
            "content": backend_response["message"]
        })

        st.rerun()

    # 🟢 NORMAL STREAMING RESPONSE
    full_response = render_streaming_response(
        call_final_streamed(llm_input)
    )

    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response
    })

    st.rerun()

# ═══════════════════════════════════════════════════════
# 🟢 CONFIRM ORDER SECTION (AFTER CHAT RENDER)
# ═══════════════════════════════════════════════════════

if st.session_state.get("pending_order"):

    st.markdown("### 🛒 Confirm Your Order")

    if st.button("✅ Confirm Order", use_container_width=True):

        user_id = st.session_state.get("user_id", "PAT001")

        result = call_finalize_checkout(
            user_id,
            st.session_state.pending_order
        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["message"]
        })

        st.session_state.pending_order = None

        st.rerun()