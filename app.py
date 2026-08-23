import streamlit as st
import os
from supabase import create_client, Client
from groq import Groq

# Initialize cloud integrations safely via secrets
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.set_page_config(page_title="Torqix AI Workspace", page_icon="🚀", layout="wide")

# --- BRAND HEADER LAYOUT ---
logo_path = "logo.png"
logo_col, text_col = st.columns([1, 5])

with logo_col:
    if os.path.exists(logo_path):
        st.image(logo_path, width=90)
    else:
        st.title("🔮")

with text_col:
    st.markdown("<h1 style='margin-bottom: 0px; color: #FFFFFF;'>TORQIX AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #A020F0; font-size: 1.2rem; font-weight: bold; margin-top: 0px;'>The AI Engine for Disciplined Builders</p>", unsafe_allow_html=True)

st.markdown("<hr style='border-top: 1px solid #121214;'>", unsafe_allow_html=True)

# --- GOOGLE AUTHENTICATION LAYER ---
if "user" not in st.session_state:
    st.subheader("🔒 Access the Torqix System Portal")
    st.write("Sign in with your Google account to log performance data, calculate credit balances, and initialize your workspace.")
    
    if st.button("Sign in with Google"):
        # This generates the login link using the newest library standard
res = supabase.auth.sign_in_with_oauth({"provider": "google"})
auth_url = res.url
        st.write(f"[👉 Click here to login securely via Google]({auth_url})")
else:
    user_id = st.session_state.user.id
    user_email = st.session_state.user.email

    # Initialize user profile record in database if it doesn't exist
    try:
        profile_query = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
        profile_data = profile_query.data
    except Exception:
        new_profile = {
            "id": user_id,
            "email": user_email,
            "tier": "free",
            "credits_remaining": 1000,
            "max_daily_credits": 1000
        }
        supabase.table("user_profiles").insert(new_profile).execute()
        profile_data = new_profile

    tier = profile_data["tier"]
    credits = profile_data["credits_remaining"]
    max_credits = profile_data["max_daily_credits"]
    msg_count = profile_data["total_messages_sent"]

    # --- BRAND NAVIGATION CONTROL PANEL ---
    st.sidebar.title("🚀 Torqix Engine")
    page = st.sidebar.radio("Navigation Matrix", ["🤖 Chat Core Terminal", "💎 Subscriptions & Billing"])
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Account Balance")
    
    # Render Tier badges dynamically
    if tier == "free":
        st.sidebar.markdown("### Tier: <span style='color:#808495;'>Standard Explorer</span>", unsafe_allow_html=True)
    elif tier == "pro":
        st.sidebar.markdown("### Tier: <span style='color:#A020F0;'>👑 TORQIX Pro</span>", unsafe_allow_html=True)
    elif tier == "infinity":
        st.sidebar.markdown("### Tier: <span style='color:#FFD700;'>🔥 TORQIX Infinity</span>", unsafe_allow_html=True)

    st.sidebar.metric(label="Daily Credits Remaining", value=f"{credits:,} / {max_credits:,}")
    st.sidebar.metric(label="Total Submissions Sent", value=f"{msg_count:,}")
    st.sidebar.info("📉 Note: Processing an individual AI response balances exactly 10 credits.")

    # --- BRAND VIEW 1: ADVANCED CHAT INTERFACE ---
    if page == "🤖 Chat Core Terminal":
        if credits < 10:
            st.error("⚠️ Daily credit limitations hit (100 responses maxed out). Upgrade execution parameters in the Subscription Portal to resume system operations.")
        else:
            if "messages" not in st.session_state:
                st.session_state.messages = []

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            if user_prompt := st.chat_input("Input command to Torqix AI..."):
                with st.chat_message("user"):
                    st.write(user_prompt)
                st.session_state.messages.append({"role": "user", "content": user_prompt})

                # Stream response from high-speed Llama cloud nodes
                completion = groq_client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[{"role": "user", "content": user_prompt}]
                )
                ai_reply = completion.choices.message.content

                with st.chat_message("assistant"):
                    st.write(ai_reply)
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})

                # Deduct transactional balances and iterate application counters
                supabase.table("user_profiles").update({
                    "credits_remaining": credits - 10,
                    "total_messages_sent": msg_count + 1
                }).eq("id", user_id).execute()
                st.rerun()

    # --- BRAND VIEW 2: PREMIUM SUBSCRIPTION MANAGEMENT ---
    elif page == "💎 Subscriptions & Billing":
        st.subheader("💎 Scale Computational System Ceilings")
        st.write("Upgrade your metrics dashboard pipelines to support massive asset production workflows.")
        
        # Admin simulator mechanism for testing purposes
        st.warning("🧪 Stripe Test Mode Sandbox: Run Mock Payment Upgrade Below")
        mock_col1, mock_col2 = st.columns(2)
        with mock_col1:
            if st.button("Simulate Successful Pro Payment"):
                supabase.table("user_profiles").update({"tier": "pro", "max_daily_credits": 1000000, "credits_remaining": 1000000}).eq("id", user_id).execute()
                st.success("Account status scaled to Pro!")
                st.button("Click to Refresh UI Dashboard")
        with mock_col2:
            if st.button("Simulate Successful Infinity Payment"):
                supabase.table("user_profiles").update({"tier": "infinity", "max_daily_credits": 3000000, "credits_remaining": 3000000}).eq("id", user_id).execute()
                st.success("Account status scaled to Infinity!")
                st.button("Click to Refresh UI Dashboard")

        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<div style='border: 1px solid #121214; padding: 20px; border-radius: 10px;'>", unsafe_allow_html=True)
            st.markdown("### Standard Explorer")
            st.markdown("<h1>Free</h1>", unsafe_allow_html=True)
            st.write("• 1,000 daily default credits")
            st.write("• Baseline processing speeds")
            st.write("• Hard capped at 100 requests/day")
            st.button("Current Active Operations", disabled=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col2:
            st.markdown("<div style='border: 2px solid #A020F0; padding: 20px; border-radius: 10px; background-color: #0c0812;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #A020F0;'>👑 TORQIX Pro</h3>", unsafe_allow_html=True)
            st.markdown("<h1>₹499 <span style='font-size:12px; color:#808495;'>/mo</span></h1>", unsafe_allow_html=True)
            st.write("• 1,000,000 credits allocated daily")
            st.write("• Priority cloud processing lane")
            st.write("• Production level response volumes")
            
            # ⬇️ PASTE YOUR STRIPE PRO LINK HERE ⬇️
            pro_stripe_url = "https://buy.stripe.com/test_5kQeVd2VR24OeCJ67W8IU00"
            st.link_button("Upgrade to Pro Tier", pro_stripe_url)
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div style='border: 2px solid #FFD700; padding: 20px; border-radius: 10px; background-color: #121000;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #FFD700;'>🔥 TORQIX Infinity</h3>", unsafe_allow_html=True)
            st.markdown("<h1>₹999 <span style='font-size:12px; color:#808495;'>/mo</span></h1>", unsafe_allow_html=True)
            st.write("• Unlimited workspace capabilities")
            st.write("• Enterprise-tier throughput limits")
            st.write("• Secret 3,000,000 daily backend credits")
            
            # ⬇️ PASTE YOUR STRIPE INFINITY LINK HERE ⬇️
            infinity_stripe_url = "https://buy.stripe.com/test_5kQ14n8gbaBkgKR53S8IU01"
            st.link_button("Unlock Infinite Workspace", infinity_stripe_url)
            st.markdown("</div>", unsafe_allow_html=True)
