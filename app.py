import streamlit as st
import hashlib
import time
import pandas as pd
import random

# --- Blockchain Functions ---
def hash_block(block):
    block_string = f"{block['timestamp']}{block['household']}{block['action']}{block['credits']}{block['prev_hash']}"
    return hashlib.sha256(block_string.encode()).hexdigest()

def add_block(household, action, credits):
    prev_hash = st.session_state.blockchain[-1]["hash"] if st.session_state.blockchain else "0"
    block = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "household": household,
        "action": action,
        "credits": credits,
        "prev_hash": prev_hash,
        "hash": ""
    }
    block["hash"] = hash_block(block)
    st.session_state.blockchain.append(block)

# --- Initialize State ---
if "wallets" not in st.session_state:
    st.session_state.wallets = {
        "Household_101": {"credits": 20},
        "Household_102": {"credits": 10},
        "Household_103": {"credits": 0},
    }

if "blockchain" not in st.session_state:
    st.session_state.blockchain = []

# --- Streamlit UI ---
st.set_page_config(page_title="Blockchain Waste Credit System", page_icon="♻️")
st.title("♻️ Blockchain-based Waste Credit System (Prototype)")

menu = st.sidebar.radio("Menu", ["Citizen Wallet", "Verify Segregation", "Redeem Credits", "Leaderboard", "Blockchain Ledger"])

# --- Citizen Wallet ---
if menu == "Citizen Wallet":
    st.header("🏠 Citizen Digital Wallet")
    household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))
    wallet = st.session_state.wallets[household]

    st.metric(label="Wallet Balance (Waste Credits)", value=wallet["credits"])

# --- Verify Segregation ---
elif menu == "Verify Segregation":
    st.header("🗑️ Waste Segregation Verification")
    household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))
    segregated = st.radio("Was the waste properly segregated?", ["Yes", "No"])

    if st.button("Verify & Allocate Credits"):
        if segregated == "Yes":
            points = random.randint(2, 5)
            st.session_state.wallets[household]["credits"] += points
            add_block(household, "Segregation Verified", points)
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
            add_block(household, f"Redeemed {reward}", -cost)
            st.success(f"🎉 Successfully redeemed: {reward}")
        else:
            st.error("⚠️ Not enough credits to redeem this reward.")

# --- Leaderboard ---
elif menu == "Leaderboard":
    st.header("🏆 Community Leaderboard")
    leaderboard = sorted(st.session_state.wallets.items(), key=lambda x: x[1]["credits"], reverse=True)
    for rank, (house, data) in enumerate(leaderboard, 1):
        st.write(f"**{rank}. {house}** — {data['credits']} credits")

# --- Blockchain Ledger ---
elif menu == "Blockchain Ledger":
    st.header("🔗 Blockchain Ledger (Immutable Records)")
    if st.session_state.blockchain:
        df = pd.DataFrame(st.session_state.blockchain)
        st.dataframe(df)
    else:
        st.info("No transactions yet recorded on blockchain.")
