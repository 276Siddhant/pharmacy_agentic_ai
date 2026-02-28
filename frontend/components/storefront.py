import streamlit as st
import requests

BACKEND_URL = "http://127.0.0.1:8000"


# ─────────────────────────────────────────────
# 🔄 Fetch Live Inventory From Backend
# ─────────────────────────────────────────────
def fetch_products():
    try:
        response = requests.get(f"{BACKEND_URL}/products")
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except:
        return []


# ─────────────────────────────────────────────
# 🛒 Storefront UI
# ─────────────────────────────────────────────
def render_storefront():

    st.title("🛒 Pharmacy Storefront")
    st.write("Browse over-the-counter medications. All checkouts are reviewed by our AI Safety Agent.")

    if st.button("← Back to Chat"):
        st.session_state.ui_phase = "chatting"
        st.rerun()

    # 🔥 LIVE PRODUCTS FROM DATABASE
    products = fetch_products()

    col_products, col_cart = st.columns([2, 1])

    # ─────────────────────────────
    # 📦 PRODUCTS GRID
    # ─────────────────────────────
    with col_products:
        st.subheader("Available Products")

        if not products:
            st.warning("Unable to load inventory.")
            return

        grid_cols = st.columns(2)

        for index, product in enumerate(products):

            with grid_cols[index % 2]:
                with st.container(border=True):

                    st.markdown(f"**{product['name']}**")
                    st.write(f"Price: ${product['price']:.2f}")

                    # Optional category fallback
                    category = product.get("category", "General")
                    st.write(f"Category: {category}")

                    # 🛑 Out of Stock
                    if product["stock"] <= 0:
                        st.error("Out of Stock")

                    # 🛡️ Prescription Required
                    elif product.get("prescription_required"):
                        st.warning("Prescription Required")
                        if st.button("Upload Rx", key=f"rx_{index}"):
                            st.session_state.pending_prescription = product["name"]
                            st.session_state.ui_phase = "prescription_upload"
                            st.rerun()

                    # ✅ In Stock
                    else:
                        st.success(f"In Stock: {product['stock']}")

                        if st.button("Add to Cart", key=f"add_{index}"):

                            found = False
                            for item in st.session_state.cart:
                                if item["name"] == product["name"]:
                                    item["quantity"] += 1
                                    found = True
                                    break

                            if not found:
                                new_item = {
                                    "id": product["id"],
                                    "name": product["name"],
                                    "price": product["price"],
                                    "quantity": 1
                                }
                                st.session_state.cart.append(new_item)

                            st.rerun()

    # ─────────────────────────────
    # 🛍️ CART SECTION
    # ─────────────────────────────
    with col_cart:
        st.subheader("Your Cart")

        if not st.session_state.cart:
            st.info("Cart is empty.")
        else:
            total = 0.0

            for item in st.session_state.cart:
                item_total = item["price"] * item["quantity"]
                st.write(f"- **{item['name']}** (x{item['quantity']}) : ${item_total:.2f}")
                total += item_total

            st.markdown("---")
            st.markdown(f"**Total: ${total:.2f}**")

            # 💳 Generate Payment Link
            if st.button("💳 Generate Payment Link", use_container_width=True, type="primary"):

                from services.api_client import call_create_payment_link
                name = st.session_state.get("patient_name", "Guest")

                with st.spinner("Connecting to Paypal..."):
                    link = call_create_payment_link(total, name)

                    if link:
                        st.session_state.payment_link = link
                    else:
                        st.error("Payment gateway unavailable.")

            # 🔗 Show Pay Button
            if st.session_state.get("payment_link"):
                st.success("Payment link generated securely!")

                st.link_button(
                    "Redirect to Paypal Checkout ↗",
                    st.session_state.payment_link,
                    type="secondary",
                    use_container_width=True
                )

                # ✅ After Payment → Trigger AI Review
                if st.button("✅ I have completed the payment", use_container_width=True, type="primary"):
                     from services.api_client import call_finalize_checkout

                     cart_payload = [
                         {"name": item["name"], "quantity": item["quantity"]}
                        for item in st.session_state.cart
                ]

                with st.spinner("Finalizing checkout and validating safety..."):
                             result = call_finalize_checkout(
                                 st.session_state.get("patient_id", "PAT001"),
                             cart_payload
                        )

                if result.get("status") == "success":
                    purchased_items = [
                        f"{item['name']} x{item['quantity']}"
                        for item in st.session_state.cart
                    ]

                    total_amount = sum(
                        item["price"] * item["quantity"]
                        for item in st.session_state.cart
                    )

    # Build AI prompt for receipt + validation summary
                    checkout_prompt = (
                    f"I have completed payment for the following medicines: "
                    f"{', '.join(purchased_items)}. "
                    f"Total amount paid: ${total_amount:.2f}. "
                    f"Please generate a purchase summary, dosage instructions, "
                    f"safety advice, and consultation receipt."
                )

    # Clear cart AFTER building summary
                st.session_state.cart = []
                st.session_state.payment_link = None

    # Send to chat system
                st.session_state.checkout_prompt = checkout_prompt
                st.session_state.ui_phase = "chatting"

                st.rerun()

        # Clear cart
                st.session_state.cart = []
                st.session_state.payment_link = None

        # Refresh stock
                st.rerun()

            else:

                    st.error(result.get("message", "Checkout failed."))
                     
                     

    


   

            if st.button("Clear Cart", use_container_width=True):
                st.session_state.cart = []
                st.session_state.payment_link = None
                st.rerun()