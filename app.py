import streamlit as st
import os
from supabase import create_client, Client
from huggingface_hub import InferenceClient

# ─── PAGE CONFIG & CUSTOM DARK THEME ───
st.set_page_config(page_title="Torqix AI Workspace", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0B0E14; color: #E2E8F0; }
    div[data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1E293B; }
    .main-header {
        background: linear-gradient(90deg, #A020F0 0%, #6366F1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
    }
    .sub-header { color: #94A3B8; font-size: 1.1rem; margin-bottom: 20px; }
    .stButton>button {
        background: linear-gradient(90deg, #A020F0 0%, #6366F1 100%);
        color: white; border: none; border-radius: 8px; font-weight: 600; padding: 0.5rem 1rem;
    }
    .credit-box { background: #1E293B; border-radius: 10px; padding: 20px; border: 1px solid #334155; margin-bottom: 15px; }
    .tier-badge-pro { background-color: #581C87; color: #E9D5FF; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
    .tier-badge-infinity { background-color: #713F12; color: #FEF08A; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
    .tier-badge-free { background-color: #1E293B; color: #94A3B8; padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
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
def sync_user_profile(user_id, email="builder@torqix.ai"):
    profile_payload = {
        "id": str(user_id),
        "email": str(email),
        "tier": "free",
        "credits_remaining": 1000,
        "max_daily_credits": 1000,
        "total_messages_sent": 0
    }
    try:
        res = supabase.table("user_profiles").select("*").eq("id", str(user_id)).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        
        upsert_res = supabase.table("user_profiles").upsert(profile_payload, on_conflict="id").execute()
        if upsert_res.data and len(upsert_res.data) > 0:
            return upsert_res.data[0]
    except Exception as e:
        st.error(f"Database Sync Warning: {e}")
    return profile_payload


def update_user_credits(user_id, new_credits, total_messages):
    try:
        supabase.table("user_profiles").update({
            "credits_remaining": int(new_credits),
            "total_messages_sent": int(total_messages)
        }).eq("id", str(user_id)).execute()
    except Exception as e:
        st.error(f"Credit Sync Error: {e}")

# ─── SESSION AUTO-RECOVERY & STRIPE RETURN ───
query_params = st.query_params

# Check URL for returned session parameters
if "uid" in query_params:
    st.session_state.user_id = query_params["uid"]
    st.session_state.user_email = query_params.get("email", "user@torqix.ai")
    st.session_state.user = {"id": query_params["uid"], "email": st.session_state.user_email}

# Payment Return Listener
if "payment" in query_params and query_params["payment"] == "success":
    paid_tier = query_params.get("tier", "pro")
    target_uid = st.session_state.get("user_id", query_params.get("uid", None))
    
    if target_uid:
        credits_cap = 3000000 if paid_tier == "infinity" else 1000000
        
        # Force database sync
        try:
            supabase.table("user_profiles").update({
                "tier": str(paid_tier),
                "credits_remaining": int(credits_cap),
                "max_daily_credits": int(credits_cap)
            }).eq("id", str(target_uid)).execute()
        except Exception as e:
            st.error(f"Tier Upgrade Error: {e}")

        st.session_state.profile = sync_user_profile(target_uid)
        st.toast(f"🎉 Upgrade Successful! Switched to {paid_tier.upper()} mode.", icon="🔥")

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
                    
                    st.query_params["uid"] = res.user.id
                    st.query_params["email"] = res.user.email
                    st.rerun()
            except Exception as err:
                st.error(f"Sign In Failed: {err}")

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
                    
                    st.query_params["uid"] = res.user.id
                    st.query_params["email"] = res.user.email
                    st.success("Account created!")
                    st.rerun()
            except Exception as err:
                st.error(f"Sign Up Failed: {err}")

    with tab_google:
        st.write("OAuth Direct Auth")
        if st.button("Continue with Google"):
            try:
                res = supabase.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {"redirect_to": APP_URL}
                })
                if res.url:
                    st.markdown(f"[👉 Complete Google Authentication]({res.url})")
            except Exception as err:
                st.error(f"OAuth Error: {err}")

else:
    # ─── ACTIVE USER WORKSPACE ───
    user_id = st.session_state.user_id
    user_email = st.session_state.user_email

    if "profile" not in st.session_state:
        st.session_state.profile = sync_user_profile(user_id, user_email)

    profile = st.session_state.profile
    user_tier = profile.get("tier", "free")

    st.sidebar.markdown("### 🚀 Torqix Control Center")
    page = st.sidebar.radio("Navigation", ["🤖 Chat Core Terminal", "💎 Subscriptions & Billing"])
    st.sidebar.markdown("---")
    
    st.sidebar.markdown(f"**Logged in:** `{user_email}`")
    if st.sidebar.button("Log Out"):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        st.query_params.clear()
        for key in ["user", "user_id", "user_email", "profile", "messages"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📋 System Telemetry")
    
    if user_tier == 'infinity':
        st.sidebar.markdown("### Tier: <span style='color:#FFD700;'>🔥 TORQIX INFINITY</span>", unsafe_allow_html=True)
    elif user_tier == 'pro':
        st.sidebar.markdown("### Tier: <span style='color:#A020F0;'>👑 TORQIX PRO</span>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("### Tier: <span style='color:#808495;'>STANDARD EXPLORER</span>", unsafe_allow_html=True)

    st.sidebar.metric("Daily Credit Capacity", f"{profile['credits_remaining']:,} / {profile['max_daily_credits']:,}")
    st.sidebar.metric("Total Prompts Processed", f"{profile['total_messages_sent']:,}")

    # ─── TERMINAL PAGE ───
    if page == "🤖 Chat Core Terminal":
        
        if user_tier == "infinity":
            st.markdown("""
                <div style='background: #121000; border: 1px solid #FFD700; padding: 12px 20px; border-radius: 10px; margin-bottom: 20px;'>
                    <span class='tier-badge-infinity'>🔥 INFINITY ENGINE UNLOCKED</span>
                    <p style='margin: 5px 0 0 0; font-size: 0.9rem; color: #E2E8F0;'>Maximum Context Window (1,500 Tokens) • Priority Processing</p>
                </div>
            """, unsafe_allow_html=True)
            max_response_tokens = 1500
            system_persona = "You are Torqix AI operating in 🔥 INFINITY ENGINE MODE."

        elif user_tier == "pro":
            st.markdown("""
                <div style='background: #0C0812; border: 1px solid #A020F0; padding: 12px 20px; border-radius: 10px; margin-bottom: 20px;'>
                    <span class='tier-badge-pro'>👑 PRO TERMINAL ACTIVE</span>
                    <p style='margin: 5px 0 0 0; font-size: 0.9rem; color: #E2E8F0;'>Expanded Output Window (1,000 Tokens)</p>
                </div>
            """, unsafe_allow_html=True)
            max_response_tokens = 1000
            system_persona = "You are Torqix AI operating in 👑 PRO MODE."

        else:
            st.markdown("""
                <div style='background: #111827; border: 1px solid #334155; padding: 12px 20px; border-radius: 10px; margin-bottom: 20px;'>
                    <span class='tier-badge-free'>STANDARD TERMINAL</span>
                    <p style='margin: 5px 0 0 0; font-size: 0.9rem; color: #94A3B8;'>Standard Rate Limit • 500 Token Output Cap</p>
                </div>
            """, unsafe_allow_html=True)
            max_response_tokens = 500
            system_persona = "You are Torqix AI, an intelligent assistant for builders."

        if profile["credits_remaining"] < 10:
            st.error("⚠️ Daily credit balance depleted. Upgrade in Subscriptions & Billing to continue.")
        else:
            if "messages" not in st.session_state:
                st.session_state.messages = []

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            if prompt := st.chat_input(f"Command Torqix AI ({user_tier.upper()} Mode)..."):
                with st.chat_message("user"):
                    st.write(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

                formatted_messages = [{"role": "system", "content": system_persona}]
                for m in st.session_state.messages:
                    formatted_messages.append({"role": m["role"], "content": m["content"]})

                try:
                    res = hf_client.chat_completion(
                        messages=formatted_messages,
                        max_tokens=max_response_tokens,
                        stream=False
                    )
                    reply = res.choices[0].message.content
                except Exception as err:
                    reply = f"Inference Error: {str(err)}"

                with st.chat_message("assistant"):
                    st.write(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

                # Deduct credits locally and update Supabase
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
        st.subheader("💎 Operational Tiers & Computational Systems")

        col1, col2, col3 = st.columns(3)

        pro_stripe_base = f"https://buy.stripe.com/test_5kQeVd2VR24OeCJ67W8IU00"
        infinity_stripe_base = f"https://buy.stripe.com/test_5kQ14n8gbaBkgKR53S8IU01"

        with col1:
            st.markdown("<div class='credit-box'>", unsafe_allow_html=True)
            st.markdown("### Standard Explorer")
            st.markdown("<h2>Free</h2>", unsafe_allow_html=True)
            st.write("• 1,000 Daily Credits")
            st.write("• 500 Token Output Cap")
            if user_tier == "free":
                st.button("Active Plan", disabled=True, key="free_active")
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='credit-box' style='border: 2px solid #A020F0;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color:#A020F0;'>👑 TORQIX Pro</h3>", unsafe_allow_html=True)
            st.markdown("<h2>₹499 <span style='font-size:14px;color:#94A3B8;'>/mo</span></h2>", unsafe_allow_html=True)
            st.write("• 1,000,000 Daily Credits")
            st.write("• 1,000 Token Output Cap")
            if user_tier == "pro":
                st.button("Active Plan", disabled=True, key="pro_active")
            else:
                st.link_button("Upgrade to Pro", pro_stripe_base)
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='credit-box' style='border: 2px solid #FFD700;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color:#FFD700;'>🔥 TORQIX Infinity</h3>", unsafe_allow_html=True)
            st.markdown("<h2>₹999 <span style='font-size:14px;color:#94A3B8;'>/mo</span></h2>", unsafe_allow_html=True)
            st.write("• 3,000,000 Daily Credits")
            st.write("• 1,500 Max Token Output")
            if user_tier == "infinity":
                st.button("Active Plan", disabled=True, key="inf_active")
            else:
                st.link_button("Unlock Infinity Tier", infinity_stripe_base)
            st.markdown("</div>", unsafe_allow_html=True)
