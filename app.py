import streamlit as st
import hashlib
import json
import time
import random

# -----------------------
# Blockchain helpers
# -----------------------
def hash_block(block: dict) -> str:
    """Deterministic hash for a block (ignore 'hash')."""
    canonical = {k: block[k] for k in sorted(block) if k != "hash"}
    block_string = json.dumps(canonical, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def add_block(household: str, action: str, credits: int):
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

    # Record readable line in wallet history
    tx_line = f"{block['timestamp']} | {action} | {'+' if credits>0 else ''}{credits} | h:{block['hash'][:6]}"
    st.session_state.wallets[household]["transactions"].append(tx_line)

# -----------------------
# Init session state
# -----------------------
if "wallets" not in st.session_state:
    st.session_state.wallets = {
        "Household_101": {"credits": 20, "transactions": []},
        "Household_102": {"credits": 10, "transactions": []},
        "Household_103": {"credits": 0,  "transactions": []},
    }

if "blockchain" not in st.session_state:
    st.session_state.blockchain = []

# -----------------------
# UI
# -----------------------
st.set_page_config(page_title="Blockchain Waste Credit System", page_icon="♻️", layout="centered")
st.title("♻️ Blockchain-based Waste Credit System — Fast Demo Mode")

menu = st.sidebar.radio("Menu", ["Citizen Wallet", "Verify Segregation", "Redeem Credits", "Leaderboard", "Blockchain Ledger"])

# --- Citizen Wallet ---
if menu == "Citizen Wallet":
    household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))
    wallet = st.session_state.wallets[household]

    st.metric("Wallet Balance (Waste Credits)", wallet["credits"])
    st.subheader("Transaction history")
    if wallet["transactions"]:
        for tx in reversed(wallet["transactions"]):
            st.write("✅", tx)
    else:
        st.info("No transactions yet.")

# --- Verify Segregation ---
elif menu == "Verify Segregation":
    household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))
    segregated = st.radio("Was waste properly segregated?", ["Yes", "No"])

    if st.button("Verify & Allocate Credits"):
        if segregated == "Yes":
            points = random.randint(2, 5)
            st.session_state.wallets[household]["credits"] += points
            add_block(household, "Segregation Verified", points)
            st.success(f"✅ {points} credits added to {household}")
        else:
            st.warning("❌ No credits added.")

# --- Redeem Credits ---
elif menu == "Redeem Credits":
    household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))
    wallet = st.session_state.wallets[household]
    st.metric("Available Credits", wallet["credits"])

    rewards = {
        "Utility Bill Discount (10 credits)": 10,
        "Metro/Bus Ticket (5 credits)": 5,
        "Local Shop Coupon (8 credits)": 8,
    }
    reward = st.selectbox("Choose Reward", list(rewards.keys()))

    if st.button("Redeem"):
        cost = rewards[reward]
        if wallet["credits"] >= cost:
            wallet["credits"] -= cost
            add_block(household, f"Redeemed {reward}", -cost)
            st.success(f"🎉 Redeemed: {reward}")
        else:
            st.error("⚠️ Not enough credits.")

# --- Leaderboard ---
elif menu == "Leaderboard":
    st.header("🏆 Leaderboard")
    leaderboard = sorted(st.session_state.wallets.items(), key=lambda x: x[1]["credits"], reverse=True)
    for rank, (house, data) in enumerate(leaderboard, 1):
        st.write(f"{rank}. {house} — {data['credits']} credits")

# --- Blockchain Ledger ---
elif menu == "Blockchain Ledger":
    st.header("🔗 Blockchain Ledger (last 10 blocks)")
    if not st.session_state.blockchain:
        st.info("No blocks yet.")
    else:
        for block in reversed(st.session_state.blockchain[-10:]):  # show last 10
            st.json(block, expanded=False)
