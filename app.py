# app.py
import streamlit as st
import hashlib
import json
import time
import random

# Try to import pandas (used only for nicer ledger export/display). If missing, show friendly message.
try:
    import pandas as pd
except Exception as e:
    pd = None
    st = st  # keep linter happy
    # We'll show a helpful error in the UI below.

# -----------------------
# Helpers
# -----------------------
def hash_block(block: dict) -> str:
    """Hash block deterministically (exclude 'hash' field)."""
    # produce canonical JSON of the block excluding 'hash'
    canonical = {k: block[k] for k in sorted(block) if k != "hash"}
    block_string = json.dumps(canonical, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(block_string.encode()).hexdigest()

def add_block(household: str, action: str, credits: int):
    """Create a block, compute its hash and append to blockchain and wallet txs."""
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

    # Record a readable transaction line in the household's transaction history
    tx_line = f"{block['timestamp']} | {action} | {'+' if credits>0 else ''}{credits} | h:{block['hash'][:8]}"
    st.session_state.wallets.setdefault(household, {"credits": 0, "transactions": []})
    st.session_state.wallets[household]["transactions"].append(tx_line)

# -----------------------
# Initialize session state
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
st.set_page_config(page_title="Blockchain Waste Credit System", page_icon="♻️", layout="wide")
st.title("♻️ Blockchain-based Waste Credit System — Prototype")

menu = st.sidebar.radio("Menu", ["Citizen Wallet", "Verify Segregation", "Redeem Credits", "Leaderboard", "Blockchain Ledger", "Debug"])

# --- Citizen Wallet ---
if menu == "Citizen Wallet":
    st.header("🏠 Citizen Digital Wallet")
    household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))
    wallet = st.session_state.wallets[household]
    st.metric(label="Wallet Balance (Waste Credits)", value=wallet["credits"])

    st.subheader("Transaction history")
    if wallet["transactions"]:
        for tx in reversed(wallet["transactions"]):
            st.write(tx)
    else:
        st.info("No transactions yet for this household.")

# --- Verify Segregation ---
elif menu == "Verify Segregation":
    st.header("🗑️ Waste Segregation Verification (Green Champion / IoT)")
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
            add_block(household, f"Redeemed: {reward}", -cost)
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
    if not st.session_state.blockchain:
        st.info("No transactions yet recorded on blockchain.")
    else:
        # Display ledger nicely
        if pd:
            df = pd.DataFrame(st.session_state.blockchain)
            st.dataframe(df[["timestamp", "household", "action", "credits", "prev_hash", "hash"]])
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download ledger as CSV", csv, file_name="ledger.csv", mime="text/csv")
        else:
            st.write(st.session_state.blockchain)

# --- Debug ---
elif menu == "Debug":
    st.header("🧰 Debug / Diagnostics")
    st.write("Python/pandas availability:", "pandas imported" if pd else "pandas NOT available")
    st.subheader("Session state wallets")
    st.write(st.session_state.wallets)
    st.subheader("Session state blockchain")
    st.write(st.session_state.blockchain)
    st.info("If you see module errors (ImportError / ModuleNotFoundError), install missing packages and restart the app.")
