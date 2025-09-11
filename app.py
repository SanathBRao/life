import streamlit as st
import random
import time

# --- Simulated Database (in-memory for demo) ---
if "wallets" not in st.session_state:
    st.session_state.wallets = {
        "Household_101": {"credits": 20, "transactions": []},
        "Household_102": {"credits": 10, "transactions": []},
        "Household_103": {"credits": 0, "transactions": []},
    }

# --- UI ---
st.set_page_config(page_title="Blockchain Waste Credit System", page_icon="♻️")

st.title("♻️ Blockchain-based Waste Credit System (Prototype)")

menu = st.sidebar.radio("Menu", ["Citizen Wallet", "Verify Segregation", "Redeem Credits", "Leaderboard"])

# --- Citizen Wallet ---
if menu == "Citizen Wallet":
    st.header("🏠 Citizen Digital Wallet")
    household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))

    wallet = st.session_state.wallets[household]
    st.metric(label="Wallet Balance (Waste Credits)", value=wallet["credits"])

    st.subheader("Transaction History")
    if wallet["transactions"]:
        for tx in wallet["transactions"]:
            st.write(f"✅ {tx}")
    else:
        st.info("No transactions yet.")

# --- Verify Segregation ---
elif menu == "Verify Segregation":
    st.header("🗑️ Waste Segregation Verification")

    household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))
    segregated = st.radio("Was the waste properly segregated?", ["Yes", "No"])

    if st.button("Verify & Allocate Credits"):
        if segregated == "Yes":
            points = random.randint(2, 5)  # random credit reward
            st.session_state.wallets[household]["credits"] += points
            tx = f"{points} Waste Credits earned for proper segregation"
            st.session_state.wallets[household]["transactions"].append(tx)
            st.success(f"✅ Verified! {points} credits added to {household}")
        else:
            st.warning("❌ No credits allocated. Waste not segregated properly.")

# --- Redeem Credits ---
elif menu == "Redeem Credits":
    st.header("🎟️ Redeem Waste Credits")

    household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))
    wallet = st.session_state.wallets[household]

    st.metric(label="Available Credits", value=wallet["credits"])

    reward_options = {
        "Utility Bill Discount (10 credits)": 10,
        "Metro/Bus Ticket (5 credits)": 5,
        "Local Shop Coupon (8 credits)": 8,
    }

    reward = st.selectbox("Choose Reward", list(reward_options.keys()))

    if st.button("Redeem"):
        cost = reward_options[reward]
        if wallet["credits"] >= cost:
            wallet["credits"] -= cost
            tx = f"Redeemed {reward} (-{cost} credits)"
            wallet["transactions"].append(tx)
            st.success(f"🎉 Successfully redeemed: {reward}")
        else:
            st.error("⚠️ Not enough credits to redeem this reward.")

# --- Leaderboard ---
elif menu == "Leaderboard":
    st.header("🏆 Community Leaderboard")
    leaderboard = sorted(st.session_state.wallets.items(), key=lambda x: x[1]["credits"], reverse=True)
    for rank, (house, data) in enumerate(leaderboard, 1):
        st.write(f"**{rank}. {house}** — {data['credits']} credits")
