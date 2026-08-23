import streamlit as st
import os
from supabase import create_client, Client
from huggingface_hub import InferenceClient

# ─── PAGE CONFIG & CUSTOM DARK THEME ───
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
        padding: 20px;
        border: 1px solid #334155;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ─── CLIENT INITIALIZATION ───
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
HF_TOKEN = st.secrets["HF_TOKEN"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
hf_client = InferenceClient(model="meta-llama/Llama-3.1-8B-Instruct", token=HF_TOKEN)

APP_URL = "https://torqix-ai.streamlit.app"

# ─── DATABASE HELPER FUNCTIONS ───
def sync_user_profile(user_id, email):
    """Retrieves or upserts user details into public.user_profiles without data loss."""
    profile_payload = {
        "id": str(user_id),
        "email": str(email),
        "tier": "free",
        "credits_remaining": 1000,
        "max_daily_credits": 1000,
        "total_messages_sent": 0
    }

    try:
        res = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        
        upsert_res = supabase.table("user_profiles").upsert(
            profile_payload, 
            on_conflict="id"
        ).execute()
        
        if upsert_res.data and len(upsert_res.data) > 0:
            return upsert_res.data[0]
            
    except Exception:
        pass
        
    return profile_payload


def update_user_credits(user_id, new_credits, total_messages):
    """Syncs credit deductions and message counters to Supabase."""
    try:
        supabase.table("user_profiles").update({
            "credits_remaining": new_credits,
            "total_messages_sent": total_messages
        }).eq("id", user_id).execute()
    except Exception:
        pass

# ─── SESSION RESTORATION & STRIPE RETURN HANDLING ───
query_params = st.query_params

if "user_id" in query_params and "user" not in st.session_state:
    saved_id = query_params["user_id"]
    saved_email = query_params.get("email", "user@torqix.ai")
    st.session_state.user_id = saved_id
    st.session_state.user_email = saved_email
    st.session_state.user = {"id": saved_id, "email": saved_email}
    st.session_state.profile = sync_user_profile(saved_id, saved_email)

if "payment" in query_params and query_params["payment"] == "success":
    paid_tier = query_params.get("tier", "pro")
    
    if "user_id" in st.session_state:
        target_uid = st.session_state.user_id
        credits_cap = 3000000 if paid_tier == "infinity" else 1000000
        
        if "profile" in st.session_state:
            st.session_state.profile["tier"] = paid_tier
            st.session_state.profile["credits_remaining"] = credits_cap
            st.session_state.profile["max_daily_credits"] = credits_cap

        try:
            supabase.table("user_profiles").update({
                "tier": paid_tier,
                "credits_remaining": credits_cap,
                "max_daily_credits": credits_cap
            }).eq("id", target_uid).execute()
        except Exception:
            pass
            
        st.toast(f"🎉 Payment Verified! Welcome to Torqix {paid_tier.upper()} Tier.", icon="🔥")

# ─── BRAND HEADER ───
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)
with col_title:
    st.markdown("<h1 class='main-header'>TORQIX AI</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>The AI Engine for Disciplined Builders</p>", unsafe_allow_html=True)

st.markdown("<hr style='border-color: #1E293B;'>", unsafe_allow_html=True)

# ─── AUTHENTICATION LAYER ───
if "user" not in st.session_state:
    st.subheader("🔒 Access Torqix System Portal")
    
    tab_login, tab_signup, tab_google = st.tabs(["🔑 Sign In", "📝 Create Account", "🌐 Google OAuth"])
    
    with tab_login:
        login_email = st.text_input("Email", key="l_email")
        login_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Sign In to Workspace"):
            try:
                res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                if res.user:
                    st.session_state.user = res.user
                    st.session_state.user_id = res.user.id
                    st.session_state.user_email = res.user.email
                    st.session_state.profile = sync_user_profile(res.user.id, res.user.email)
                    
                    st.query_params["user_id"] = res.user.id
                    st.query_params["email"] = res.user.email
                    st.success("Successfully authenticated!")
                    st.rerun()
            except Exception as err:
                st.error(f"Authentication Failed: {err}")

    with tab_signup:
        signup_email = st.text_input("Email", key="s_email")
        signup_pass = st.text_input("Password", type="password", key="s_pass")
        if st.button("Create Account"):
            try:
                res = supabase.auth.sign_up({"email": signup_email, "password": signup_pass})
                if res.user:
                    st.session_state.user = res.user
                    st.session_state.user_id = res.user.id
                    st.session_state.user_email = res.user.email
                    st.session_state.profile = sync_user_profile(res.user.id, res.user.email)
                    
                    st.query_params["user_id"] = res.user.id
                    st.query_params["email"] = res.user.email
                    st.success("Account registered!")
                    st.rerun()
            except Exception as err:
                st.error(f"Registration Failed: {err}")

    with tab_google:
        st.write("Sign in via Google OAuth integration.")
        if st.button("Continue with Google"):
            try:
                res = supabase.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {"redirect_to": APP_URL}
                })
                st.markdown(f"[👉 Complete Google Authentication]({res.url})")
            except Exception as err:
                st.error(f"OAuth Initialization Error: {err}")

else:
    # ─── ACTIVE USER WORKSPACE ───
    user_id = st.session_state.user_id
    user_email = st.session_state.user_email

    if "profile" not in st.session_state:
        st.session_state.profile = sync_user_profile(user_id, user_email)

    profile = st.session_state.profile

    st.sidebar.markdown("### 🚀 Torqix Control Center")
    page = st.sidebar.radio("Navigation", ["🤖 Chat Core Terminal", "💎 Subscriptions & Billing"])
    st.sidebar.markdown("---")
    
    st.sidebar.markdown(f"**Logged in:** `{user_email}`")
    if st.sidebar.button("Log Out"):
        supabase.auth.sign_out()
        st.query_params.clear()
        for key in ["user", "user_id", "user_email", "profile", "messages"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 System Telemetry")
    
    if profile['tier'] == 'infinity':
        st.sidebar.markdown("### Tier: <span style='color:#FFD700;'>🔥 TORQIX INFINITY</span>", unsafe_allow_html=True)
    elif profile['tier'] == 'pro':
        st.sidebar.markdown("### Tier: <span style='color:#A020F0;'>👑 TORQIX PRO</span>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("### Tier: <span style='color:#808495;'>STANDARD EXPLORER</span>", unsafe_allow_html=True)

    st.sidebar.metric("Daily Credit Capacity", f"{profile['credits_remaining']:,} / {profile['max_daily_credits']:,}")
    st.sidebar.metric("Total Prompts Processed", f"{profile['total_messages_sent']:,}")

    # ─── TERMINAL PAGE ───
    if page == "🤖 Chat Core Terminal":
        if profile["credits_remaining"] < 10:
            st.error("⚠️ Daily credit balance depleted. Upgrade your parameters in the Subscription Portal.")
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

                formatted_messages = [
                    {"role": "system", "content": "You are Torqix AI, an elite AI engine designed to assist disciplined builders, developers, and creators. Always introduce and refer to yourself strictly as Torqix AI."}
                ]
                for m in st.session_state.messages:
                    formatted_messages.append({"role": m["role"], "content": m["content"]})

                try:
                    res = hf_client.chat_completion(
                        messages=formatted_messages,
                        max_tokens=700,
                        stream=False
                    )
                    reply = res.choices[0].message.content
                except Exception as err:
                    reply = f"Inference Error: {str(err)}"

                with st.chat_message("assistant"):
                    st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

                # Deduct credits locally and sync to database
                st.session_state.profile["credits_remaining"] -= 10
                st.session_state.profile["total_messages_sent"] += 1
                
                update_user_credits(
                    user_id=user_id,
                    new_credits=st.session_state.profile["credits_remaining"],
                    total_messages=st.session_state.profile["total_messages_sent"]
                )
                
                st.rerun()

    # ─── BILLING PAGE ───
    elif page == "💎 Subscriptions & Billing":
        st.subheader("💎 Scale Computational System Ceilings")
        st.write("Select an operational tier below. When completed, you will automatically return directly to your AI session with unlocked privileges.")

        col1, col2, col3 = st.columns(3)

        pro_redirect = f"{APP_URL}?payment=success&tier=pro&user_id={user_id}&email={user_email}"
        infinity_redirect = f"{APP_URL}?payment=success&tier=infinity&user_id={user_id}&email={user_email}"

        with col1:
            st.markdown("<div class='credit-box'>", unsafe_allow_html=True)
            st.markdown("### Standard Explorer")
            st.markdown("<h2>Free</h2>", unsafe_allow_html=True)
            st.write("• 1,000 Daily Credits")
            st.write("• Standard AI throughput")
            st.button("Active Plan", disabled=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='credit-box' style='border: 2px solid #A020F0;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color:#A020F0;'>👑 TORQIX Pro</h3>", unsafe_allow_html=True)
            st.markdown("<h2>₹499 <span style='font-size:14px;color:#94A3B8;'>/mo</span></h2>", unsafe_allow_html=True)
            st.write("• 1,000,000 Daily Credits")
            st.write("• High-priority queue lanes")
            
            st.link_button("Upgrade to Pro", f"https://buy.stripe.com/test_5kQeVd2VR24OeCJ67W8IU00={pro_redirect}")
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='credit-box' style='border: 2px solid #FFD700;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color:#FFD700;'>🔥 TORQIX Infinity</h3>", unsafe_allow_html=True)
            st.markdown("<h2>₹999 <span style='font-size:14px;color:#94A3B8;'>/mo</span></h2>", unsafe_allow_html=True)
            st.write("• 3,000,000 Daily Credits")
            st.write("• Uncapped priority inference engine")
            st.write("• Dedicated priority developer support")
            
            st.link_button("Unlock Infinity Tier", f"https://buy.stripe.com/test_dRm3cv9kf38S8el67W8IU02={infinity_redirect}")
            st.markdown("</div>", unsafe_allow_html=True)
