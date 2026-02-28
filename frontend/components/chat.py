"""
components/chat.py
------------------
UI-only chat renderer.
Now supports backend 'trace' field automatically.
"""

import streamlit as st


# ── Agent colour map ──────────────────────────────────────────
AGENT_COLORS = {
    "🩺 Pharmacist":  "#7C3AED",
    "🛡️ Safety":      "#DC2626",
    "📦 Fulfillment": "#059669",
}

DEFAULT_AGENT_COLOR = "#6B7280"


# ── Utility: map trace → agent sections ──────────────────────
def _map_trace_to_agents(trace: list) -> list:
    """
    Converts backend trace list into styled agent_logs format.
    """

    if not trace:
        return []

    pharmacist_logs = []
    safety_logs = []
    fulfillment_logs = []
    other_logs = []

    for entry in trace:
        text = str(entry)

        if any(word in text.lower() for word in ["symptom", "recommend", "intent"]):
            pharmacist_logs.append(text)

        elif any(word in text.lower() for word in ["safety", "prescription", "blocked", "overdose", "emergency"]):
            safety_logs.append(text)

        elif any(word in text.lower() for word in ["stock", "order", "inventory", "refill"]):
            fulfillment_logs.append(text)

        else:
            other_logs.append(text)

    agent_logs = []

    if pharmacist_logs:
        agent_logs.append({
            "agent": "🩺 Pharmacist",
            "log": "\n".join(pharmacist_logs)
        })

    if safety_logs:
        agent_logs.append({
            "agent": "🛡️ Safety",
            "log": "\n".join(safety_logs)
        })

    if fulfillment_logs:
        agent_logs.append({
            "agent": "📦 Fulfillment",
            "log": "\n".join(fulfillment_logs)
        })

    if other_logs:
        agent_logs.append({
            "agent": "🤖 System",
            "log": "\n".join(other_logs)
        })

    return agent_logs


# ── Agent logs renderer ───────────────────────────────────────
def _render_agent_logs(agent_logs: list) -> None:
    if not agent_logs:
        return

    st.markdown(
        "<p style='font-size:0.72rem; color:#6B7280; margin: 6px 0 4px 0;'>"
        "🤖 Agent reasoning</p>",
        unsafe_allow_html=True,
    )

    


# ── Single message renderer ───────────────────────────────────
def _render_message(message: dict, index: int) -> None:

    role       = message.get("role", "user")
    content    = message.get("content", "")
    trace      = message.get("trace", [])
    agent_logs = message.get("agent_logs", [])

    # If backend trace exists, convert it
    if trace and not agent_logs:
        agent_logs = _map_trace_to_agents(trace)

    if role == "user":
        st.markdown(
            f"""
            <div style="
                display: flex;
                justify-content: flex-end;
                width: 100%;
                padding: 4px 0;
            ">
                <div style="
                    background: linear-gradient(135deg, #7C3AED, #5B21B6);
                    border-radius: 14px 14px 2px 14px;
                    padding: 10px 16px;
                    max-width: 75%;
                    font-size: 0.92rem;
                    line-height: 1.55;
                    color: #ffffff;
                    box-shadow: 0 2px 12px rgba(124,58,237,0.35);
                    word-wrap: break-word;
                ">
                {content}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif role == "assistant":
        with st.chat_message("assistant"):

            st.markdown(
                f"""
                <div style="
                    background: #1a0a2e;
                    border: 1px solid #2d1a4e;
                    border-radius: 14px 14px 14px 2px;
                    padding: 12px 16px;
                    max-width: 90%;
                    font-size: 0.92rem;
                    line-height: 1.6;
                    color: #f0f0f0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                ">
                {content}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if agent_logs:
                st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
                _render_agent_logs(agent_logs)


# ── Main render function ───────────────────────────────────────
def render_chat_history() -> None:

    messages: list = st.session_state.get("messages", [])

    if not messages:
        st.info("No messages yet. Start chatting below!")
        return

    for i, message in enumerate(messages):
        _render_message(message, index=i)


# ── Streaming assistant message ───────────────────────────────
def render_streaming_response(stream_generator) -> str:

    full_text = ""

    try:
        with st.chat_message("assistant"):
            placeholder = st.empty()

            for chunk in stream_generator:
                full_text += chunk
                placeholder.markdown(
                    f"""
                    <div style="
                        background: #1a0a2e;
                        border: 1px solid #2d1a4e;
                        border-radius: 14px 14px 14px 2px;
                        padding: 12px 16px;
                        max-width: 90%;
                        font-size: 0.92rem;
                        line-height: 1.6;
                        color: #f0f0f0;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                    ">
                    {full_text} ▌
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            placeholder.markdown(
                f"""
                <div style="
                    background: #1a0a2e;
                    border: 1px solid #2d1a4e;
                    border-radius: 14px 14px 14px 2px;
                    padding: 12px 16px;
                    max-width: 90%;
                    font-size: 0.92rem;
                    line-height: 1.6;
                    color: #f0f0f0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
                ">
                {full_text}
                </div>
                """,
                unsafe_allow_html=True,
            )

    except Exception as e:
        st.warning(f"Stream interrupted: {e}. Partial response captured.")

    return full_text