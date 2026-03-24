import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from main import LaptopDoctorAgent
from sensors import LaptopSensors

# Page Configuration
st.set_page_config(page_title="AI Laptop Doctor", layout="wide")

st.title("🩺 AI-Powered Actionable Troubleshooting System")
st.markdown("---")

# Sidebar for Controls
st.sidebar.header("System Controls")
if st.sidebar.button("🚀 Run Full System Scan"):
    with st.spinner("Scanning Hardware..."):
        scanner = LaptopSensors()
        scanner.run_full_scan()
    st.sidebar.success("Scan Complete!")

# Load Data
def load_data():
    with open("last_scan.json", "r") as f:
        return json.load(f)

try:
    data = load_data()
    
    # --- ROW 1: Visual Gauges ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("CPU Usage")
        st.write(f"**{data['system']['cpu_model']}**")
        st.progress(data['system']['cpu_usage_pct'] / 100)
        st.metric("Usage", f"{data['system']['cpu_usage_pct']}%")

    with col2:
        st.subheader("RAM Status")
        st.write(f"Available: {data['system']['ram_available_gb']} GB")
        st.progress(data['system']['ram_usage_pct'] / 100)
        st.metric("Used", f"{data['system']['ram_usage_pct']}%")

    with col3:
        st.subheader("Battery Health")
        st.metric("Health %", data['battery_health']['wear_level_pct'], delta="Excellent" if float(data['battery_health']['wear_level_pct']) < 5 else "Check Manual")

    # --- ROW 2: AI Diagnosis Chat ---
    st.markdown("---")
    st.header("💬 Talk to Dr. Llama")
    
    user_query = st.text_input("Describe your issue (e.g., 'Why is my RAM high?' or 'Is my SSD failing?')")
    
    if user_query:
        with st.spinner("Analyzing manuals and telemetry..."):
            agent = LaptopDoctorAgent()
            response = agent.run_doctor(user_query)
            st.chat_message("assistant").write(response)

    # --- ROW 3: Faulty Drivers & Logs ---
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.header("⚠️ Driver Alerts")
        st.write(data['faulty_drivers'])
    with c2:
        st.header("📜 Recent System Logs")
        st.table(data['recent_logs'])

except Exception as e:
    st.warning("Please run a system scan from the sidebar to start.")