import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, date
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Duty Tracker", page_icon="📋", layout="wide")

# PASTE YOUR APPS SCRIPT WEB APP URL HERE
WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxGqPAoO0nu0-pppHjyJTBO8ltNC3XEjwXRsVsNBOP4uY8vXsQArSiICPbjLzeJ438/exec"

# --- DATA HANDLING (Via Apps Script API) ---
def load_data():
    try:
        response = requests.get(WEBAPP_URL)
        data = response.json()
        
        if len(data) <= 1: # Only headers or empty sheet
            return pd.DataFrame(columns=["Date", "Shift", "Post", "Duty_Type", "Timestamp"])
            
        headers = data[0]
        rows = data[1:]
        return pd.DataFrame(rows, columns=headers)
    except Exception as e:
        st.error("Failed to connect to Google Sheets.")
        return pd.DataFrame(columns=["Date", "Shift", "Post", "Duty_Type", "Timestamp"])

def save_data(date_val, shift, post, duty_type):
    if duty_type == "Leave":
        shift = "N/A"
        post = "N/A"
        
    payload = {
        "Date": str(date_val),
        "Shift": shift,
        "Post": post,
        "Duty_Type": duty_type,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Send data to Google Apps Script POST endpoint
    requests.post(WEBAPP_URL, json=payload)

# --- UI NAVIGATION ---
st.sidebar.title("📋 Duty Tracker")
menu = st.sidebar.radio("Navigation", ["📝 New Entry", "📊 Dashboard"])

df = load_data()

# --- TAB 1: ENTRY FORM ---
if menu == "📝 New Entry":
    st.title("Log Your Duty")
    st.markdown("Fill out the details below. Data saves directly to Google Sheets via Webhook.")
    
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
            with st.spinner("Saving to Google Sheets..."):
                save_data(duty_date, shift, post, duty_type)
            if duty_type == "Leave":
                st.success(f"✅ Successfully logged Leave for {duty_date}.")
            else:
                st.success(f"✅ Successfully logged {duty_type} duty for {duty_date} at post {post} (Shift {shift}).")

# --- TAB 2: DASHBOARD ---
elif menu == "📊 Dashboard":
    st.title("Interactive Duty Dashboard")
    st.button("🔄 Refresh Data")
    
    if df.empty:
        st.info("No records found in the Google Sheet. Submit some entries to see the dashboard.")
    else:
        df['Date'] = pd.to_datetime(df['Date'])
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        df_month = df[(df['Date'].dt.month == current_month) & (df['Date'].dt.year == current_year)]
        
        total_daily = len(df_month[df_month['Duty_Type'] == "Daily"])
        total_ot = len(df_month[df_month['Duty_Type'] == "OT (Overtime)"])
        total_leave = len(df_month[df_month['Duty_Type'] == "Leave"])
        
        # --- METRICS ---
        st.markdown("### 📅 Current Month Overview")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Regular Duties", total_daily)
        m2.metric("Total OTs", total_ot)
        m3.metric("Logged Leaves", total_leave)
        
        st.divider()
        
        # --- CHARTS ---
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("#### Duty by Post (Excluding Leaves)")
            df_worked = df[df['Duty_Type'] != "Leave"]
            if not df_worked.empty:
                post_counts = df_worked['Post'].value_counts().reset_index()
                post_counts.columns = ['Post', 'Count']
                fig_post = px.pie(post_counts, values='Count', names='Post', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                st.plotly_chart(fig_post, use_container_width=True)
            else:
                st.info("No active duty posts logged yet.")
            
        with col_chart2:
            st.markdown("#### Activity over Time")
            daily_counts = df.groupby(['Date', 'Duty_Type']).size().reset_index(name='Count')
            fig_trend = px.bar(daily_counts, x='Date', y='Count', color='Duty_Type', barmode='group')
            st.plotly_chart(fig_trend, use_container_width=True)
            
        # --- RAW DATA ---
        st.markdown("### 🗄️ Recent Records (Live from Google Sheets)")
        st.dataframe(df.sort_values(by="Date", ascending=False).head(10), use_container_width=True, hide_index=True)