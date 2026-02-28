import os
import requests
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 30


# ═══════════════════════════════════════════════════════════════
# 💬 MAIN CHAT CALL (Non-streaming version)
# ═══════════════════════════════════════════════════════════════

def call_chat(user_id: str, text: str) -> dict:
    """
    Calls your FastAPI /chat endpoint.
    """

    response = requests.post(
        f"{BACKEND_URL}/chat",
        params={
            "user_id": user_id,
            "message": text
        },
        timeout=TIMEOUT
    )

    response.raise_for_status()
    return response.json()


# ═══════════════════════════════════════════════════════════════
# 📊 REFILL ALERT CHECK
# ═══════════════════════════════════════════════════════════════

def call_refill_check(user_id: str):
    """
    Calls backend refill endpoint.
    """

    response = requests.get(
        f"{BACKEND_URL}/admin/refill/{user_id}",
        timeout=TIMEOUT
    )

    response.raise_for_status()
    return response.json()


# ═══════════════════════════════════════════════════════════════
# 📦 INVENTORY CHECK (Admin)
# ═══════════════════════════════════════════════════════════════

def call_inventory():
    response = requests.get(
        f"{BACKEND_URL}/admin/inventory",
        timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()


# ═══════════════════════════════════════════════════════════════
# 📜 ORDER HISTORY
# ═══════════════════════════════════════════════════════════════

def call_user_orders(user_id: str):
    response = requests.get(
        f"{BACKEND_URL}/user/orders/{user_id}",
        timeout=TIMEOUT
    )
    response.raise_for_status()
    return response.json()


# ═══════════════════════════════════════════════════════════════
# 🎙️ VOICE (if you later implement backend whisper)
# ═══════════════════════════════════════════════════════════════

def call_transcribe(audio_bytes: bytes) -> str:

    response = requests.post(
        f"{BACKEND_URL}/voice/transcribe",
        files={"audio": ("audio.wav", audio_bytes, "audio/wav")},
        timeout=TIMEOUT
    )

    response.raise_for_status()
    return response.json().get("text", "")


# ═══════════════════════════════════════════════════════════════
# 🛡 SAFE WRAPPER
# ═══════════════════════════════════════════════════════════════

def safe_call(func, *args, fallback="Backend unavailable.", **kwargs):
    try:
        return func(*args, **kwargs)
    except requests.exceptions.ConnectionError:
        return {"message": "⚠️ Backend unreachable."}
    except requests.exceptions.Timeout:
        return {"message": "⚠️ Backend timeout."}
    except requests.exceptions.HTTPError as e:
        return {"message": f"⚠️ Backend error {e.response.status_code}"}
    except Exception as e:
        return {"message": f"⚠️ Unexpected error: {str(e)}"}