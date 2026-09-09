import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import hashlib
import time
import uuid
from datetime import datetime, date
import extra_streamlit_components as stx

# --- CONFIGURATION ---
st.set_page_config(page_title="Duty Tracker", page_icon="📋", layout="wide")

# PASTE YOUR DEPLOYMENT URL HERE
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbzh46p4uBw3QDBk4_ObntV2FcPJxdb6PnmtFxjQ1EgbRB3svnHDV_kgAQ2wBbLE9Due/exec"

# --- COOKIE MANAGER ---
cookie_manager = stx.CookieManager(key="duty_cookie_manager_v5")

# --- AUTH & SESSION STATE INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = ""
if "first_name" not in st.session_state:
    st.session_state.first_name = ""
if "show_welcome_animation" not in st.session_state:
    st.session_state.show_welcome_animation = False
if "just_logged_out" not in st.session_state:
    st.session_state.just_logged_out = False

# --- PERSISTENT LOGIN CHECK ---
if not st.session_state.logged_in and not st.session_state.just_logged_out:
    saved_email = cookie_manager.get("duty_email")
    saved_name = cookie_manager.get("duty_name")
    if saved_email and saved_name:
        st.session_state.logged_in = True
        st.session_state.email = saved_email
        st.session_state.first_name = saved_name
        st.session_state.show_welcome_animation = True

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def logout():
    st.session_state.logged_in = False
    st.session_state.email = ""
    st.session_state.first_name = ""
    st.session_state.show_welcome_animation = False
    st.session_state.just_logged_out = True
    
    cookie_manager.delete("duty_email", key=f"del_e_{uuid.uuid4().hex}")
    cookie_manager.delete("duty_name", key=f"del_n_{uuid.uuid4().hex}")
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
    st.session_state.just_logged_out = False

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
                            st.session_state.logged_in = True
                            st.session_state.email = log_email.strip().lower()
                            st.session_state.first_name = res.get("first_name", "User")
                            st.session_state.show_welcome_animation = True
                            st.session_state.just_logged_out = False
                            
                            cookie_manager.set("duty_email", st.session_state.email, max_age=30*24*60*60, key=f"set_e_{uuid.uuid4().hex}")
                            cookie_manager.set("duty_name", st.session_state.first_name, max_age=30*24*60*60, key=f"set_n_{uuid.uuid4().hex}")
                            
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
    if st.session_state.show_welcome_animation:
        st.toast(f"Welcome back, {st.session_state.first_name}! 👋", icon="🎉")
        st.balloons()
        st.session_state.show_welcome_animation = False

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
        
        # --- HEADER & DATE DROPDOWNS ---
        head_col1, head_col2, head_col3 = st.columns([0.6, 0.2, 0.2])
        with head_col1:
            st.subheader("Monthly Duty Summary 💳")
            
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        current_month_idx = datetime.now().month - 1
        current_year = datetime.now().year
        year_options = list(range(current_year, current_year + 10)) # Generates up to 10 upcoming years
        
        with head_col2:
            selected_month_str = st.selectbox("Month", options=months_list, index=current_month_idx, label_visibility="collapsed")
        with head_col3:
            selected_year = st.selectbox("Year", options=year_options, index=0, label_visibility="collapsed")
            
        st.divider()

        if df.empty:
            st.info("No records found. Submit entries to see your dashboard.")
        else:
            month_num = months_list.index(selected_month_str) + 1
            df_month = df[(df['Date'].dt.month == month_num) & (df['Date'].dt.year == selected_year)]

            # --- SUMMARY CARD ---
            with st.container(border=True):
                st.markdown(f"### **{selected_month_str} {selected_year} Summary**")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Worked Shifts", len(df_month[df_month['Duty_Type'] != "Leave"]))
                m2.metric("Regular Duties", len(df_month[df_month['Duty_Type'] == "Daily"]))
                m3.metric("Overtime (OT)", len(df_month[df_month['Duty_Type'] == "OT (Overtime)"]))
                m4.metric("Leaves", len(df_month[df_month['Duty_Type'] == "Leave"]))

            st.write("")
            
            # --- GRANULAR FILTERS SECTION ---
            st.markdown("#### 🔍 Filter Duties")
            f1, f2, f3 = st.columns(3)
            with f1:
                filter_type = st.selectbox("Duty Type Filter", options=["All", "Daily", "OT (Overtime)", "Leave"])
            with f2:
                filter_shift = st.selectbox("Shift Filter", options=["All", "A", "B", "C"])
            with f3:
                filter_post = st.selectbox("Post Filter", options=["All", "G7", "MG", "SY", "GMB", "Admin", "Other"])

            df_filtered = df_month.copy()
            if filter_type != "All":
                df_filtered = df_filtered[df_filtered['Duty_Type'] == filter_type]
            if filter_shift != "All":
                df_filtered = df_filtered[df_filtered['Shift'] == filter_shift]
            if filter_post != "All":
                df_filtered = df_filtered[df_filtered['Post'] == filter_post]

            st.divider()

            # --- CHARTS & VISUALIZATIONS ---
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("#### 🎯 Duty Breakdown by Post")
                df_worked = df_filtered[df_filtered['Duty_Type'] != "Leave"]
                if not df_worked.empty:
                    fig_post = px.pie(df_worked, names='Post', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                    fig_post.update_layout(showlegend=True, margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_post, use_container_width=True)
                else:
                    st.caption("No duty post data available for selected filters.")
                
            with col_chart2:
                st.markdown("#### 📈 Monthly Shift Trends")
                if not df_filtered.empty:
                    daily_counts = df_filtered.groupby(['Date', 'Duty_Type']).size().reset_index(name='Count')
                    fig_trend = px.bar(daily_counts, x='Date', y='Count', color='Duty_Type', barmode='group')
                    fig_trend.update_layout(xaxis_title="", yaxis_title="Shifts", margin=dict(t=10, b=10, l=10, r=10))
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.caption("No shift activity available for selected filters.")

            # --- FILTERED RECORDS TABLE ---
            st.markdown(f"### 🗄️ Records for {selected_month_str} ({len(df_filtered)} found)")
            if not df_filtered.empty:
                df_display = df_filtered.copy()
                df_display['Date_Str'] = df_display['Date'].dt.strftime('%Y-%m-%d')
                st.dataframe(
                    df_display.drop(columns=['Sheet_Row', 'Email', 'Timestamp', 'Date']).rename(columns={'Date_Str': 'Date'}).sort_values(by="Date", ascending=False), 
                    use_container_width=True, hide_index=True
                )
            else:
                st.warning("No records match your selected filters for this month.")
            
            # --- REMOVE ENTRY SECTION ---
            st.markdown("#### 🗑️ Remove Entry")
            if not df_month.empty:
                df_del_display = df_month.copy()
                df_del_display['Date_Str'] = df_del_display['Date'].dt.strftime('%Y-%m-%d')
                del_ops = {f"{r['Date_Str']} | {r['Duty_Type']} | {r['Post']}": r['Sheet_Row'] for _, r in df_del_display.sort_values(by="Date", ascending=False).iterrows()}
                
                cd1, cd2 = st.columns([0.8, 0.2])
                sel_lbl = cd1.selectbox("Select entry to delete:", list(del_ops.keys()), label_visibility="collapsed")
                if cd2.button("Delete Entry", type="primary", use_container_width=True):
                    if delete_data_by_row(del_ops[sel_lbl]).get("status") == "deleted":
                        st.success("✅ Entry deleted!")
                        st.rerun()

    # Footer Logout Button
    st.write("")
    st.divider()
    col_space, col_logout = st.columns([0.85, 0.15])
    with col_logout:
        if st.button("Log Out 👋", use_container_width=True):
            logout()