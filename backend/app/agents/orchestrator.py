from .intent_agent import detect_intent
from .safety_agent import run_safety_checks
from .inventory_agent import check_inventory
from .action_agent import execute_order

from ..services import recommend_from_symptom, fuzzy_match_medicine
from ..models import PendingOrder


def run_pharmacy_agent(db, user_id, message):

    trace = []

    # =====================================================
    # 🚨 1️⃣ EMERGENCY DETECTION
    # =====================================================
    RED_FLAGS = [
        "chest pain",
        "breathing difficulty",
        "can't breathe",
        "severe bleeding",
        "unconscious",
        "heart attack",
        "stroke"
    ]

    if any(flag in message.lower() for flag in RED_FLAGS):
        return {
            "message": "🚨 This sounds like a medical emergency. Please go to the nearest hospital immediately.",
            "trace": ["Emergency mode triggered"]
        }

    # =====================================================
    # 🔁 2️⃣ CONTINUE PENDING ORDER (MULTI-TURN SUPPORT)
    # =====================================================
    pending = db.query(PendingOrder).filter(
        PendingOrder.patient_id == user_id
    ).first()

    if pending and message.strip().isdigit():

        quantity = int(message.strip())
        medicine = pending.medicine_name

        trace.append("Continuing pending order")

        # Clear pending state
        db.delete(pending)
        db.commit()

        data = {
            "intent": "order",
            "medicine": medicine,
            "quantity": quantity,
            "dosage_frequency": 1
        }

    else:
        # =====================================================
        # 🤖 3️⃣ INTENT DETECTION
        # =====================================================
        data = detect_intent(message)
        trace.append(f"Intent detected: {data}")

    # =====================================================
    # 🩺 4️⃣ RECOMMEND FLOW
    # =====================================================
    if data.get("intent") == "recommend":

        symptom = data.get("symptom")

        if not symptom:
            return {
                "message": "Please describe your symptom clearly.",
                "trace": trace
            }

        recommendations = recommend_from_symptom(db, symptom)

        return {
            "message": f"Based on your symptom '{symptom}', I recommend:",
            "recommendations": recommendations,
            "trace": trace
        }

    # =====================================================
    # 💊 5️⃣ ORDER FLOW
    # =====================================================
    elif data.get("intent") == "order":
        quantity = data.get("quantity")
    dosage = data.get("dosage_frequency") or 1

    # Use extracted medicine string, not full sentence
    medicine_input = data.get("medicine")

    trace.append(f"Medicine extracted from intent: {medicine_input}")

    if not medicine_input:
        return {
            "message": "Please specify the medicine name clearly.",
            "trace": trace
        }

    # Fuzzy match only the medicine name, NOT full sentence
    import re

# Remove numbers
    cleaned = re.sub(r"\b\d+\b", "", medicine_input)

# Remove common filler words
    STOPWORDS = ["i", "need", "want", "give", "me", "please"]
    tokens = cleaned.lower().split()
    filtered = " ".join([t for t in tokens if t not in STOPWORDS])

    trace.append(f"Cleaned medicine input: {filtered}")

    medicine = fuzzy_match_medicine(db, filtered)

    if not medicine:
        return {
            "message": "Medicine not found. Please check spelling.",
            "trace": ["Fuzzy match failed"]
        }

    trace.append(f"Fuzzy matched medicine: {medicine}")

    # If quantity missing → ask
    if not quantity:

        existing = db.query(PendingOrder).filter(
            PendingOrder.patient_id == user_id
        ).first()

        if existing:
            db.delete(existing)
            db.commit()

        pending = PendingOrder(
            patient_id=user_id,
            medicine_name=medicine
        )

        db.add(pending)
        db.commit()

        return {
            "message": f"How many units of {medicine} would you like?",
            "trace": ["Pending order saved"]
        }

    # Stock check
    inventory = check_inventory(db, medicine, quantity)
    trace.append(f"Stock check: {inventory}")

    if inventory["status"] != "available":
        return {
            "message": f"{medicine} is out of stock.",
            "trace": trace
        }

    # Safety check
    safety = run_safety_checks(db, user_id, medicine)
    trace.append(f"Safety check: {safety}")

    if safety["status"] == "blocked":
        return {
            "message": safety.get("message", "Order blocked due to safety policy."),
            "trace": trace
        }

    # Execute
    result = execute_order(db, user_id, medicine, quantity, dosage)

    return {
        "message": f"Order placed successfully for {medicine}.",
        "data": result,
        "trace": trace
    }

    