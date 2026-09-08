import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import hashlib
import time
from datetime import datetime, date, timedelta
import extra_streamlit_components as stx

# --- CONFIGURATION ---
st.set_page_config(page_title="Duty Tracker", page_icon="📋", layout="wide")

# PASTE YOUR NEW DEPLOYMENT URL HERE
WEBAPP_URL = "YOUR_NEW_WEBAPP_URL_HERE"

# --- COOKIE MANAGER (For Persistent Login) ---
@st.cache_resource(experimental_allow_widgets=True)
def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

# --- AUTH & SESSION STATE ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = ""
if "first_name" not in st.session_state:
    st.session_state.first_name = ""
if "show_welcome_animation" not in st.session_state:
    st.session_state.show_welcome_animation = False

# Auto-login check (reads cookies on app load)
if not st.session_state.logged_in:
    saved_email = cookie_manager.get("duty_email")
    saved_name = cookie_manager.get("duty_name")
    if saved_email and saved_name:
        st.session_state.logged_in = True
        st.session_state.email = saved_email
        st.session_state.first_name = saved_name
        st.session_state.show_welcome_animation = False # Skip animation on silent re-login

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def logout():
    # Clear session state
    st.session_state.logged_in = False
    st.session_state.email = ""
    st.session_state.first_name = ""
    st.session_state.show_welcome_animation = False
    # Clear browser cookies
    cookie_manager.delete("duty_email")
    cookie_manager.delete("duty_name")
    time.sleep(0.5) # Give the browser a moment to delete the cookie
    st.rerun()

# --- API HANDLERS ---
def authenticate(action, email, password, first_name=""):
    payload = {
        "action": action,
        "email": email.strip().lower(),
        "password": hash_password(password),
        "first_name": first_name.strip()
    }
    try:
        res = requests.post(WEBAPP_URL, json=payload).json()
        return res
    except Exception:
        return {"status": "network_error"}

def load_data():
    payload = {"action": "fetch", "email": st.session_state.email}
    try:
        data = requests.post(WEBAPP_URL, json=payload).json()
        if len(data) <= 1:
            return pd.DataFrame(columns=["Sheet_Row", "Email", "Date", "Shift", "Post", "Duty_Type", "Timestamp"])
            
        df = pd.DataFrame(data[1:], columns=data[0])
        df['Date'] = pd.to_datetime(df['Date'])
        if df['Date'].dt.tz is not None:
            df['Date'] = df['Date'].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
        df['Date'] = pd.to_datetime(df['Date'].dt.date)
        return df
    except Exception:
        return pd.DataFrame(columns=["Sheet_Row", "Email", "Date", "Shift", "Post", "Duty_Type", "Timestamp"])

def save_data(date_val, shift, post, duty_type):
    if duty_type == "Leave":
        shift, post = "N/A", "N/A"
        
    payload = {
        "action": "add",
        "email": st.session_state.email,
        "Date": str(date_val),
        "Shift": shift,
        "Post": post,
        "Duty_Type": duty_type,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    requests.post(WEBAPP_URL, json=payload)

def delete_data_by_row(sheet_row):
    payload = {"action": "delete", "email": st.session_state.email, "row": int(sheet_row)}
    try:
        return requests.post(WEBAPP_URL, json=payload).json()
    except Exception:
        return {"status": "error"}

# --- UI: LOGIN / SIGNUP SCREEN ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; margin-top: 50px;'>Welcome to Duty Tracker App 📋</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Manage your everyday shifts securely</p>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
        
        with tab_login:
            log_email = st.text_input("Email", key="log_email")
            log_pass = st.text_input("Password", type="password", key="log_pass")
            if st.button("Login", use_container_width=True, type="primary"):
                if log_email and log_pass:
                    with st.spinner("Authenticating..."):
                        res = authenticate("login", log_email, log_pass)
                        if res.get("status") == "success":
                            # Update session state
                            st.session_state.logged_in = True
                            st.session_state.email = log_email.strip().lower()
                            st.session_state.first_name = res.get("first_name", "User")
                            st.session_state.show_welcome_animation = True
                            
                            # Set persistent cookies (expires in 30 days)
                            cookie_manager.set("duty_email", st.session_state.email, max_age=30*24*60*60)
                            cookie_manager.set("duty_name", st.session_state.first_name, max_age=30*24*60*60)
                            
                            time.sleep(0.5) # Wait briefly for cookie to register
                            st.rerun()
                        else:
                            st.error("Invalid email or password.")
                else:
                    st.warning("Please fill in both fields.")
                    
        with tab_signup:
            sign_first = st.text_input("First Name")
            sign_email = st.text_input("Email", key="sign_email")
            sign_pass = st.text_input("Password", type="password", key="sign_pass")
            if st.button("Create Account", use_container_width=True):
                if sign_first and sign_email and sign_pass:
                    with st.spinner("Creating account..."):
                        res = authenticate("signup", sign_email, sign_pass, sign_first)
                        if res.get("status") == "success":
                            st.success("Account created successfully! You can now log in.")
                            st.balloons()
                        elif res.get("status") == "exists":
                            st.warning("An account with this email already exists.")
                        else:
                            st.error("Failed to create account.")
                else:
                    st.warning("Please fill in all fields.")

# --- UI: MAIN APPLICATION ---
else:
    # Trigger login animation exactly once after manual login
    if st.session_state.show_welcome_animation:
        st.toast(f"Welcome back, {st.session_state.first_name}!", icon="🎉")
        st.balloons()
        st.session_state.show_welcome_animation = False

    # Top Welcome Header
    st.markdown(f"## Hi, {st.session_state.first_name}! 👋")
    st.caption(f"Logged in as: {st.session_state.email}")
    st.write("") 

    tab1, tab2 = st.tabs(["📝 New Entry", "📊 Interactive Dashboard"])

    with tab1:
        st.subheader("Log Your Duty")
        with st.form("duty_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                duty_date = st.date_input("Date", value=date.today())
                shift = st.selectbox("Shift", options=["A", "B", "C"])
            with col2:
                post = st.selectbox("Post", options=["G7", "MG", "SY", "GMB", "Admin", "Other"])
                duty_type = st.radio("Duty Type", options=["Daily", "OT (Overtime)", "Leave"], horizontal=True)
                
            submit = st.form_submit_button("Save Entry", use_container_width=True)
            if submit:
                with st.spinner("Saving..."):
                    save_data(duty_date, shift, post, duty_type)
                st.success("✅ Entry saved successfully!")

    with tab2:
        df = load_data()
        col_title, col_btn = st.columns([0.85, 0.15])
        col_title.subheader("Monthly Overview")
        if col_btn.button("🔄 Refresh", use_container_width=True):
            st.rerun()
        
        if df.empty:
            st.info("No records found. Submit entries to see your dashboard.")
        else:
            c_month, c_year = datetime.now().month, datetime.now().year
            df_month = df[(df['Date'].dt.month == c_month) & (df['Date'].dt.year == c_year)]
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Regular Duties", len(df_month[df_month['Duty_Type'] == "Daily"]))
            m2.metric("OTs", len(df_month[df_month['Duty_Type'] == "OT (Overtime)"]))
            m3.metric("Leaves", len(df_month[df_month['Duty_Type'] == "Leave"]))
            m4.metric("Total Shifts", len(df_month[df_month['Duty_Type'] != "Leave"]))
            
            st.divider()
            
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("#### 🎯 Duty by Post")
                df_worked = df_month[df_month['Duty_Type'] != "Leave"]
                if not df_worked.empty:
                    fig_post = px.pie(df_worked, names='Post', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                    fig_post.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_post, use_container_width=True)
                
            with col_chart2:
                st.markdown("#### 📈 Activity Trend")
                if not df_month.empty:
                    daily_counts = df_month.groupby(['Date', 'Duty_Type']).size().reset_index(name='Count')
                    fig_trend = px.bar(daily_counts, x='Date', y='Count', color='Duty_Type', barmode='group')
                    fig_trend.update_layout(xaxis_title="", yaxis_title="Shifts", margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_trend, use_container_width=True)
                
            st.markdown("### 🗄️ Recent Records")
            df_display = df.copy()
            df_display['Date_Str'] = df_display['Date'].dt.strftime('%Y-%m-%d')
            st.dataframe(
                df_display.drop(columns=['Sheet_Row', 'Email', 'Timestamp', 'Date']).rename(columns={'Date_Str': 'Date'}).sort_values(by="Date", ascending=False).head(10), 
                use_container_width=True, hide_index=True
            )
            
            st.markdown("#### 🗑️ Remove Entry")
            del_ops = {f"{r['Date_Str']} | {r['Duty_Type']} | {r['Post']}": r['Sheet_Row'] for _, r in df_display.sort_values(by="Date", ascending=False).head(30).iterrows()}
            if del_ops:
                cd1, cd2 = st.columns([0.8, 0.2])
                sel_lbl = cd1.selectbox("Select:", list(del_ops.keys()), label_visibility="collapsed")
                if cd2.button("Delete", type="primary", use_container_width=True):
                    if delete_data_by_row(del_ops[sel_lbl]).get("status") == "deleted":
                        st.success("✅ Deleted!")
                        st.rerun()

    # Footer Logout Button
    st.write("")
    st.write("")
    st.divider()
    col_space, col_logout = st.columns([0.85, 0.15])
    with col_logout:
        if st.button("Log Out 👋", use_container_width=True):
            logout()