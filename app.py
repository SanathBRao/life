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

    # Record a readable line in wallet history
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

if "user_role" not in st.session_state:
    st.session_state.user_role = None

# -----------------------
# Authentication
# -----------------------
st.set_page_config(page_title="Blockchain Waste Credit System", page_icon="♻️", layout="centered")
st.title("♻️ Blockchain Waste Credit System — Demo")

# Simple login system
roles = {"user": "user123", "worker": "worker123"}  # demo passwords

if not st.session_state.user_role:
    st.subheader("🔑 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username == "user" and password == roles["user"]:
            st.session_state.user_role = "user"
            st.success("✅ Logged in as Citizen (Normal User)")
        elif username == "worker" and password == roles["worker"]:
            st.session_state.user_role = "worker"
            st.success("✅ Logged in as Worker / Green Champion")
        else:
            st.error("❌ Invalid credentials")

else:
    st.sidebar.success(f"Logged in as: {st.session_state.user_role.upper()}")
    if st.sidebar.button("Logout"):
        st.session_state.user_role = None
        st.experimental_rerun()

    # -----------------------
    # Normal User Dashboard
    # -----------------------
    if st.session_state.user_role == "user":
        st.header("🏠 Citizen Dashboard")

        household = st.selectbox("Select Your Household", list(st.session_state.wallets.keys()))
        wallet = st.session_state.wallets[household]

        st.metric("Wallet Balance (Waste Credits)", wallet["credits"])

        st.subheader("Transaction History")
        if wallet["transactions"]:
            for tx in reversed(wallet["transactions"]):
                st.write("✅", tx)
        else:
            st.info("No transactions yet.")

        st.subheader("🎟️ Redeem Credits")
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

    # -----------------------
    # Worker Dashboard
    # -----------------------
    elif st.session_state.user_role == "worker":
        st.header("🛠️ Worker Dashboard")

        menu = st.sidebar.radio("Menu", ["Verify Segregation", "Leaderboard", "Blockchain Ledger"])

        # Verify segregation
        if menu == "Verify Segregation":
            household = st.selectbox("Select Household", list(st.session_state.wallets.keys()))
            segregated = st.radio("Was waste properly segregated?", ["Yes", "No"])

            if st.button("Verify & Allocate Credits"):
                if segregated == "Yes":
                    points = random.randint(2, 5)
                    st.session_state.wallets[household]["credits"] += points
                    add_block(household, "Segregation Verified", points)
                    st.success(f"✅ {points} credits added to {household}")
                else:
                    st.warning("❌ No credits allocated.")

        # Leaderboard
        elif menu == "Leaderboard":
            st.header("🏆 Leaderboard")
            leaderboard = sorted(st.session_state.wallets.items(), key=lambda x: x[1]["credits"], reverse=True)
            for rank, (house, data) in enumerate(leaderboard, 1):
                st.write(f"{rank}. {house} — {data['credits']} credits")

        # Blockchain Ledger
        elif menu == "Blockchain Ledger":
            st.header("🔗 Blockchain Ledger (last 10 blocks)")
            if not st.session_state.blockchain:
                st.info("No blocks yet.")
            else:
                for block in reversed(st.session_state.blockchain[-10:]):
                    st.json(block, expanded=False)
