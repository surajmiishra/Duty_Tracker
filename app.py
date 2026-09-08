import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, date

# --- CONFIGURATION ---
st.set_page_config(page_title="Duty Tracker", page_icon="📋", layout="wide")

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyTCymBHrWM8DLUtjcT2YoR3lt4-1COjAq9OFwEatmj6Z58gq8m1vVQhY778CR8NzBo/exec"

# --- DATA HANDLING ---
def load_data():
    try:
        response = requests.get(WEBAPP_URL)
        data = response.json()
        
        if len(data) <= 1: 
            return pd.DataFrame(columns=["Date", "Shift", "Post", "Duty_Type", "Timestamp"])
            
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        
        # --- FIX FOR THE TIMEZONE SHIFT ISSUE ---
        df['Date'] = pd.to_datetime(df['Date'])
        if df['Date'].dt.tz is not None:
            df['Date'] = df['Date'].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
        
        df['Date'] = df['Date'].dt.date 
        df['Date'] = pd.to_datetime(df['Date']) 
        
        return df
    except Exception as e:
        st.error("Failed to connect to Google Sheets.")
        return pd.DataFrame(columns=["Date", "Shift", "Post", "Duty_Type", "Timestamp"])

def save_data(date_val, shift, post, duty_type):
    if duty_type == "Leave":
        shift = "N/A"
        post = "N/A"
        
    payload = {
        "action": "add",
        "Date": str(date_val),
        "Shift": shift,
        "Post": post,
        "Duty_Type": duty_type,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    requests.post(WEBAPP_URL, json=payload)

def delete_data(date_str, shift, post, duty_type):
    payload = {
        "action": "delete",
        "Date": str(date_str),
        "Shift": str(shift),
        "Post": str(post),
        "Duty_Type": str(duty_type)
    }
    requests.post(WEBAPP_URL, json=payload)

# --- MAIN SCREEN UI ---
st.title("📋 Duty Tracker")
st.markdown("Track your everyday shifts and monitor your monthly duty statistics.")

tab1, tab2 = st.tabs(["📝 New Entry", "📊 Interactive Dashboard"])

# --- TAB 1: ENTRY FORM ---
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
            with st.spinner("Saving to Google Sheets..."):
                save_data(duty_date, shift, post, duty_type)
            if duty_type == "Leave":
                st.success(f"✅ Successfully logged Leave for {duty_date}.")
            else:
                st.success(f"✅ Successfully logged {duty_type} duty for {duty_date} at post {post} (Shift {shift}).")

# --- TAB 2: DASHBOARD ---
with tab2:
    df = load_data()
    
    col_title, col_btn = st.columns([0.85, 0.15])
    with col_title:
        st.subheader("Monthly Overview")
    with col_btn:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()
    
    if df.empty:
        st.info("No records found in the Google Sheet. Submit some entries to see the dashboard.")
    else:
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        df_month = df[(df['Date'].dt.month == current_month) & (df['Date'].dt.year == current_year)]
        
        total_daily = len(df_month[df_month['Duty_Type'] == "Daily"])
        total_ot = len(df_month[df_month['Duty_Type'] == "OT (Overtime)"])
        total_leave = len(df_month[df_month['Duty_Type'] == "Leave"])
        
        # --- METRICS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Regular Duties", total_daily)
        m2.metric("Total OTs", total_ot)
        m3.metric("Logged Leaves", total_leave)
        m4.metric("Total Shifts Worked", total_daily + total_ot)
        
        st.divider()
        
        # --- CHARTS ---
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("#### 🎯 Duty by Post")
            df_worked = df_month[df_month['Duty_Type'] != "Leave"]
            if not df_worked.empty:
                post_counts = df_worked['Post'].value_counts().reset_index()
                post_counts.columns = ['Post', 'Count']
                fig_post = px.pie(post_counts, values='Count', names='Post', hole=0.4, 
                                  color_discrete_sequence=px.colors.sequential.Teal)
                fig_post.update_traces(textposition='inside', textinfo='percent+label')
                fig_post.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_post, use_container_width=True)
            else:
                st.info("No active duty posts logged this month.")
            
        with col_chart2:
            st.markdown("#### 📈 Activity over Time")
            if not df_month.empty:
                daily_counts = df_month.groupby(['Date', 'Duty_Type']).size().reset_index(name='Count')
                fig_trend = px.bar(daily_counts, x='Date', y='Count', color='Duty_Type', 
                                   barmode='group', color_discrete_map={"Daily": "#1f77b4", "OT (Overtime)": "#ff7f0e", "Leave": "#d62728"})
                fig_trend.update_layout(xaxis_title="", yaxis_title="Number of Shifts", margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No activity logged this month.")
            
        # --- RAW DATA & DELETE FUNCTION ---
        st.markdown("### 🗄️ Recent Records (Live)")
        
        df_display = df.copy()
        df_display['Date_Str'] = df_display['Date'].dt.strftime('%Y-%m-%d')
        
        # Display table without Timestamp
        st.dataframe(
            df_display.drop(columns=['Timestamp', 'Date'])
                      .rename(columns={'Date_Str': 'Date'})
                      .sort_values(by="Date", ascending=False)
                      .head(10), 
            use_container_width=True, 
            hide_index=True
        )
        
        st.markdown("#### 🗑️ Remove an Entry")
        st.caption("Select an incorrect or duplicate entry from the dropdown below to delete it.")
        
        delete_options = {}
        for _, row in df_display.sort_values(by="Date", ascending=False).head(30).iterrows():
            record_label = f"{row['Date_Str']} | {row['Duty_Type']} | Shift: {row['Shift']} | Post: {row['Post']}"
            delete_options[record_label] = row
            
        if delete_options:
            col_del1, col_del2 = st.columns([0.8, 0.2])
            with col_del1:
                selected_label = st.selectbox("Select entry to delete:", options=list(delete_options.keys()), label_visibility="collapsed")
            with col_del2:
                if st.button("Delete Entry", type="primary", use_container_width=True):
                    selected_row = delete_options[selected_label]
                    with st.spinner("Deleting entry..."):
                        delete_data(
                            date_str=selected_row['Date_Str'],
                            shift=selected_row['Shift'],
                            post=selected_row['Post'],
                            duty_type=selected_row['Duty_Type']
                        )
                    st.success("✅ Entry deleted successfully!")
                    st.rerun()