import streamlit as st
import os
import requests
from supabase import create_client, Client
from huggingface_hub import InferenceClient

# ─── PAGE CONFIG & CUSTOM DARK THEME STYLING ───
st.set_page_config(page_title="Torqix AI Workspace", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-color: #0B0E14;
        color: #E2E8F0;
    }
    div[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1E293B;
    }
    .main-header {
        background: linear-gradient(90deg, #A020F0 0%, #6366F1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
    }
    .sub-header {
        color: #94A3B8;
        font-size: 1.1rem;
        margin-bottom: 20px;
    }
    .stButton>button {
        background: linear-gradient(90deg, #A020F0 0%, #6366F1 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }
    .credit-box {
        background: #1E293B;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #334155;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ─── SECRETS & CLIENT INITIALIZATION ───
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HF_TOKEN = st.secrets["HF_TOKEN"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=HF_TOKEN)

# ─── HANDLE STRIPE RETURN CALLBACK ───
query_params = st.query_params
if "payment" in query_params and query_params["payment"] == "success":
    paid_tier = query_params.get("tier", "pro")
    st.toast(f"🎉 Payment successful! Tier upgraded to {paid_tier.upper()}.", icon="🚀")

# ─── HELPER: SYNC USER TO SUPABASE ───
def sync_user_profile(user_id, email):
    try:
        res = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        else:
            new_profile = {
                "id": user_id,
                "email": email,
                "tier": "free",
                "credits_remaining": 1000,
                "max_daily_credits": 1000,
                "total_messages_sent": 0
            }
            supabase.table("user_profiles").upsert(new_profile).execute()
            return new_profile
    except Exception:
        # Fallback dictionary if table schema/RLS blocks query
        return {
            "id": user_id,
            "email": email,
            "tier": "free",
            "credits_remaining": 1000,
            "max_daily_credits": 1000,
            "total_messages_sent": 0
        }

# ─── BRAND HEADER ───
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)
with col_title:
    st.markdown("<h1 class='main-header'>TORQIX AI</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>The AI Engine for Disciplined Builders</p>", unsafe_allow_html=True)

st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

# ─── AUTHENTICATION ROUTING ───
if "user" not in st.session_state:
    st.subheader("🔒 Sign In to Access Workspace")
    
    tab_login, tab_signup, tab_google = st.tabs(["🔑 Sign In", "📝 Create Account", "🌐 Google OAuth"])
    
    with tab_login:
        login_email = st.text_input("Email", key="l_email")
        login_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                st.session_state.user = res.user
                profile = sync_user_profile(res.user.id, res.user.email)
                st.session_state.profile = profile
                st.success("Authenticated successfully!")
                st.rerun()
            except Exception as err:
                st.error(f"Login Error: {err}")

    with tab_signup:
        signup_email = st.text_input("Email", key="s_email")
        signup_pass = st.text_input("Password", type="password", key="s_pass")
        if st.button("Register Account"):
            try:
                res = supabase.auth.sign_up({"email": signup_email, "password": signup_pass})
                if res.user:
                    st.session_state.user = res.user
                    profile = sync_user_profile(res.user.id, res.user.email)
                    st.session_state.profile = profile
                    st.success("Account created successfully!")
                    st.rerun()
            except Exception as err:
                st.error(f"Registration Error: {err}")

    with tab_google:
        st.write("Click below to sign in using your Google Account.")
        if st.button("Continue with Google"):
            try:
                res = supabase.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {"redirect_to": "https://torqix-ai.streamlit.app"}
                })
                st.markdown(f"[👉 Complete Google Login Here]({res.url})")
            except Exception as err:
                st.error(f"OAuth Initialization Error: {err}")

else:
    # ─── LOGGED IN WORKSPACE ───
    user = st.session_state.user
    if "profile" not in st.session_state:
        st.session_state.profile = sync_user_profile(user.id, user.email)

    # Check query params for post-stripe tier upgrades
    if "payment" in query_params and query_params["payment"] == "success":
        new_tier = query_params.get("tier", "pro")
        st.session_state.profile["tier"] = new_tier
        st.session_state.profile["credits_remaining"] = 1000000 if new_tier == "pro" else 3000000
        st.session_state.profile["max_daily_credits"] = 1000000 if new_tier == "pro" else 3000000

    profile = st.session_state.profile

    # Sidebar Controls
    st.sidebar.markdown("### 🚀 Torqix Navigation")
    page = st.sidebar.radio("Matrix", ["🤖 Chat Terminal", "💎 Subscriptions & Billing"])
    st.sidebar.markdown("---")
    
    st.sidebar.markdown(f"**Logged in as:**\n`{user.email}`")
    if st.sidebar.button("Log Out"):
        supabase.auth.sign_out()
        del st.session_state["user"]
        if "profile" in st.session_state:
            del st.session_state["profile"]
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 Account Balance")
    st.sidebar.markdown(f"**Active Tier:** `{profile['tier'].upper()}`")
    st.sidebar.metric("Daily Credits", f"{profile['credits_remaining']:,} / {profile['max_daily_credits']:,}")
    st.sidebar.metric("Messages Sent", f"{profile['total_messages_sent']:,}")

    # ─── VIEW 1: CHAT TERMINAL ───
    if page == "🤖 Chat Terminal":
        if profile["credits_remaining"] < 10:
            st.error("⚠️ Daily credit limit reached. Please upgrade your plan in the Billing menu.")
        else:
            if "messages" not in st.session_state:
                st.session_state.messages = []

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            if prompt := st.chat_input("Command Torqix AI..."):
                with st.chat_message("user"):
                    st.write(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

                # Injected System Prompt enforcing TORQIX AI Identity
                formatted_messages = [
                    {"role": "system", "content": "You are Torqix AI, an intelligent, high-performance AI assistant created specifically to aid disciplined builders and developers. Always refer to yourself as Torqix AI."}
                ]
                for m in st.session_state.messages:
                    formatted_messages.append({"role": m["role"], "content": m["content"]})

                try:
                    res = hf_client.chat_completion(
                        messages=formatted_messages,
                        max_tokens=600,
                        stream=False
                    )
                    reply = res.choices[0].message.content
                except Exception as err:
                    reply = f"System Error: {str(err)}"

                with st.chat_message("assistant"):
                    st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

                # Deduct 10 Credits locally & push to Supabase
                st.session_state.profile["credits_remaining"] -= 10
                st.session_state.profile["total_messages_sent"] += 1
                try:
                    supabase.table("user_profiles").update({
                        "credits_remaining": st.session_state.profile["credits_remaining"],
                        "total_messages_sent": st.session_state.profile["total_messages_sent"]
                    }).eq("id", user.id).execute()
                except Exception:
                    pass
                st.rerun()

    # ─── VIEW 2: BILLING & STRIPE REDIRECTS ───
    elif page == "💎 Subscriptions & Billing":
        st.subheader("💎 Computational Upgrades")
        st.write("Upgrade your workspace tier to expand daily credits and pipeline limits.")

        c1, c2, c3 = st.columns(3)
        app_url = "https://torqix-ai.streamlit.app"

        with c1:
            st.markdown("<div class='credit-box'>", unsafe_allow_html=True)
            st.markdown("### Standard")
            st.markdown("## Free")
            st.write("• 1,000 daily credits")
            st.write("• Basic pipeline access")
            st.button("Active Plan", disabled=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='credit-box' style='border-color: #A020F0;'>", unsafe_allow_html=True)
            st.markdown("### 👑 Pro Tier")
            st.markdown("## ₹499 / mo")
            st.write("• 1,000,000 daily credits")
            st.write("• High-priority inference")
            # Replace link with your actual Stripe Checkout URL appending the success query string
            pro_stripe_link = f"https://buy.stripe.com/test_5kQeVd2VR24OeCJ67W8IU00"
            st.link_button("Upgrade to Pro", pro_stripe_link)
            st.markdown("</div>", unsafe_allow_html=True)

        with c3:
            st.markdown("<div class='credit-box' style='border-color: #FFD700;'>", unsafe_allow_html=True)
            st.markdown("### 🔥 Infinity Tier")
            st.markdown("## ₹999 / mo")
            st.write("• 3,000,000 daily credits")
            st.write("• Uncapped priority execution")
            infinity_stripe_link = f"https://buy.stripe.com/test_dRm3cv9kf38S8el67W8IU02"
            st.link_button("Upgrade to Infinity", infinity_stripe_link)
            st.markdown("</div>", unsafe_allow_html=True)
