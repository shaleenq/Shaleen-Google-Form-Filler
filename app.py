"""
Google Forms Automation & Response Management Tool
Built with Streamlit, Requests, and SQLite3
Created By SHALEEN
"""

import streamlit as st
import requests
import json
import time
import random
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import database
from form_parser import fetch_and_parse_form, normalize_urls, extract_fb_public_load_data, DEFAULT_USER_AGENT
from generator import build_submission_payload, generate_mock_value

# ==========================================
# CONFIGURATION & SECRETS
# ==========================================
MASTER_ADMIN_PASSWORD = "SHALEEN_ADMIN_2026"  # Admin Passcode එක

st.set_page_config(
    page_title="Google Forms Automation & Response Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 50%, #1E1B4B 100%);
        padding: 1.8rem 2rem;
        border-radius: 14px;
        color: #FFFFFF;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        margin-bottom: 1.8rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .main-header h1 {
        margin: 0; font-size: 2.1rem; font-weight: 700;
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .badge {
        display: inline-block; padding: 0.25rem 0.65rem; border-radius: 6px;
        font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-right: 0.5rem;
    }
    .badge-primary { background: rgba(59, 130, 246, 0.2); color: #60A5FA; border: 1px solid rgba(96, 165, 250, 0.3); }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.3); }
    .badge-warning { background: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.3); }
    .badge-danger  { background: rgba(239, 68, 68, 0.2);  color: #F87171; border: 1px solid rgba(248, 113, 113, 0.3); }

    .card-box {
        background: #1E293B; border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px; padding: 1.4rem; margin-bottom: 1.2rem;
    }
    .question-title { font-size: 1.05rem; font-weight: 600; color: #F1F5F9; }
    .percentage-tag {
        font-size: 0.85rem; font-weight: 600; color: #38BDF8;
        background: rgba(56, 189, 248, 0.12); padding: 2px 8px; border-radius: 4px; float: right;
    }
    .metric-card {
        background: #0F172A; border-radius: 10px; padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.06); text-align: center;
    }
    .metric-val { font-size: 1.8rem; font-weight: 700; color: #F8FAFC; }
    .metric-label { font-size: 0.8rem; color: #94A3B8; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# Initialize SQLite database
database.init_db()

# Initialize Session State
if "form_data" not in st.session_state: st.session_state.form_data = None
if "questions_config" not in st.session_state: st.session_state.questions_config = []
if "submission_logs" not in st.session_state: st.session_state.submission_logs = []
if "raw_form_url" not in st.session_state: st.session_state.raw_form_url = ""
if "user_agent" not in st.session_state: st.session_state.user_agent = DEFAULT_USER_AGENT

# Sample Demo Form Data
SAMPLE_DEMO_QUESTIONS = [
    {
        "entry_id": "entry.105432901", "raw_entry_id": "105432901", "title": "Overall Customer Satisfaction",
        "description": "Rate your overall satisfaction.", "type": "radio", "type_id": 2, "is_required": True,
        "options": ["Extremely Satisfied", "Satisfied", "Neutral", "Dissatisfied"],
        "weights": {"Extremely Satisfied": 50.0, "Satisfied": 35.0, "Neutral": 10.0, "Dissatisfied": 5.0},
        "text_mode": "fixed", "fixed_value": "", "custom_list": "", "preset_generator": "name"
    },
    {
        "entry_id": "entry.401928374", "raw_entry_id": "401928374", "title": "Respondent Full Name",
        "description": "Participant name.", "type": "text", "type_id": 0, "is_required": True,
        "options": [], "weights": {}, "text_mode": "preset_generator", "fixed_value": "", "custom_list": "", "preset_generator": "name"
    }
]

def load_demo_form():
    st.session_state.form_data = {
        "title": "Product Feedback Demo",
        "view_url": "https://docs.google.com/forms/d/e/1FAIpQLSc_DEMO/viewform",
        "submit_url": "https://docs.google.com/forms/d/e/1FAIpQLSc_DEMO/formResponse",
        "page_count": 1, "page_history": "0", "questions": SAMPLE_DEMO_QUESTIONS
    }
    st.session_state.questions_config = [dict(q) for q in SAMPLE_DEMO_QUESTIONS]
    st.session_state.raw_form_url = "https://docs.google.com/forms/d/e/1FAIpQLSc_DEMO/viewform"

def sync_preset_into_state(preset_data):
    q_configs = preset_data["questions_config"]
    st.session_state.questions_config = q_configs
    st.session_state.form_data = {
        "title": preset_data.get("preset_name", "Loaded Form"),
        "view_url": preset_data["form_url"].replace("/formResponse", "/viewform"),
        "submit_url": preset_data["form_url"],
        "page_count": len(preset_data["page_history"].split(",")) if preset_data.get("page_history") else 1,
        "page_history": preset_data.get("page_history", "0"),
        "questions": q_configs
    }
    st.session_state.raw_form_url = preset_data["form_url"]

# ==========================================
# SIDEBAR: AUTHENTICATION & PRESETS
# ==========================================
with st.sidebar:
    st.markdown("### 🔑 System Access")
    user_access_input = st.text_input("Enter Access Key / Admin Pass", type="password", help="Enter Access Key or Master Password")
    
    is_admin = (user_access_input.strip() == MASTER_ADMIN_PASSWORD)
    is_approved_user = database.verify_access_key(user_access_input) if not is_admin else True
    
    if is_admin:
        st.success("👑 Logged in as Master Admin")
    elif is_approved_user and user_access_input.strip():
        st.success("✅ Access Granted!")
    elif user_access_input.strip():
        st.error("❌ Invalid Access Key!")

    st.markdown("---")
    st.markdown("### 💾 Saved Presets")
    presets_list = database.get_all_presets()
    preset_names = [p["preset_name"] for p in presets_list]
    
    if preset_names:
        selected_preset_name = st.selectbox("Select Preset", ["-- Choose --"] + preset_names)
        col_l, col_d = st.columns(2)
        with col_l:
            if st.button("📥 Load", use_container_width=True):
                if selected_preset_name != "-- Choose --":
                    p_data = database.get_preset(selected_preset_name)
                    if p_data:
                        sync_preset_into_state(p_data)
                        st.success(f"Loaded '{selected_preset_name}'!")
                        st.rerun()
        with col_d:
            if st.button("🗑️ Delete", use_container_width=True):
                if selected_preset_name != "-- Choose --":
                    database.delete_preset(selected_preset_name)
                    st.warning("Deleted!")
                    st.rerun()
    else:
        st.caption("No presets saved.")

# ==========================================
# MAIN HEADER
# ==========================================
st.markdown("""
<div class="main-header">
<div style="display: flex; justify-content: space-between; align-items: center;">
    <div>
        <h1>⚡ Google Forms Automation & Response Manager</h1>
        <p>Smart Entry ID Parser • Weighted Probability Distribution • Access Protection</p>
    </div>
    <div style="text-align: right;">
        <div style="font-size: 1.3rem; font-weight: 800; background: linear-gradient(90deg, #F472B6, #60A5FA, #34D399); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Created By SHALEEN</div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

# Check User Authorization Status
if not is_admin and not is_approved_user:
    st.warning("🔒 සෙවුම් පද්ධතිය භාවිතයට ඔබට අවසර නොමැත. කරුණාකර Access Key එක ඇතුළත් කරන්න හෝ Waiting List එකට ඇතුළත් වන්න.")
    
    with st.form("waiting_form"):
        st.subheader("📝 Request Access (Waiting List)")
        req_name = st.text_input("ඔබේ නම (Name)")
        req_contact = st.text_input("WhatsApp අංකය / Email")
        submit_req = st.form_submit_button("Request Access")
        
        if submit_req:
            if req_name.strip() and req_contact.strip():
                database.add_to_waiting_list(req_name.strip(), req_contact.strip())
                st.success("✅ ඔබව Waiting List එකට සාර්ථකව එකතු කරන ලදී! Admin විසින් අනුමත කළ පසු ඔබට Key එක හිමිවේ.")
            else:
                st.error("කරුණාකර නම සහ Contact විස්තර ලබා දෙන්න.")
    st.stop()

# Dynamic Navigation Tabs (Script Exporter Tab removed)
tab_list = [
    "1. 🔗 Form URL & Parsing", 
    "2. 🎛️ Question Probabilities & Mock Data", 
    "3. 🚀 Multi-Submission Engine"
]

if is_admin:
    tab_list.append("4. 🔒 Admin Panel (Waiting List)")

tabs = st.tabs(tab_list)

tab_parser = tabs[0]
tab_config = tabs[1]
tab_runner = tabs[2]
tab_admin = tabs[3] if is_admin else None

# ==============================================================================
# TAB 1: FORM URL & PARSING
# ==============================================================================
with tab_parser:
    st.subheader("Step 1: Enter Google Form URL")
    col_url, col_btn = st.columns([4, 1])
    with col_url:
        input_url = st.text_input("Google Form URL", value=st.session_state.raw_form_url, placeholder="https://docs.google.com/forms/d/e/.../viewform", label_visibility="collapsed")
    with col_btn:
        fetch_clicked = st.button("🔍 Fetch & Parse", use_container_width=True, type="primary")

    if fetch_clicked and input_url.strip():
        with st.spinner("Parsing Form Data..."):
            try:
                parsed_result = fetch_and_parse_form(input_url, custom_user_agent=st.session_state.user_agent)
                st.session_state.form_data = parsed_result
                st.session_state.questions_config = parsed_result["questions"]
                st.session_state.raw_form_url = input_url
                st.success(f"Parsed Form: **{parsed_result['title']}**")
            except Exception as e:
                st.error(f"Error parsing form: {e}")

    if st.session_state.form_data:
        fd = st.session_state.form_data
        st.markdown(f"### 📋 Form Metadata: `{fd['title']}`")
        st.info(f"**POST Endpoint:** `{fd['submit_url']}` | **pageHistory:** `{fd['page_history']}`")

# ==============================================================================
# TAB 2: QUESTION PROBABILITIES & MOCK DATA
# ==============================================================================
with tab_config:
    st.subheader("Step 2: Configure Answer Probabilities & Mock Values")
    if not st.session_state.questions_config:
        st.warning("⚠️ No form loaded yet.")
    else:
        for idx, q in enumerate(st.session_state.questions_config):
            eid = q["entry_id"]
            st.markdown(f"**{idx+1}. {q['title']}** (`{eid}`)")
            if q["options"]:
                for opt in q["options"]:
                    key = f"w_{eid}_{opt}"
                    default_val = float(q["weights"].get(opt, round(100.0 / len(q["options"]), 1)))
                    q["weights"][opt] = st.slider(f"Weight: {opt}", 0.0, 100.0, default_val, key=key)
            else:
                q["text_mode"] = st.selectbox(f"Mode for {eid}", ["preset_generator", "fixed", "blank"], key=f"mode_{eid}")
                if q["text_mode"] == "preset_generator":
                    q["preset_generator"] = st.selectbox("Generator", ["name", "email", "feedback"], key=f"gen_{eid}")
                elif q["text_mode"] == "fixed":
                    q["fixed_value"] = st.text_input("Fixed Value", value=q.get("fixed_value", "Sample"), key=f"fixed_{eid}")

# ==============================================================================
# TAB 3: MULTI-SUBMISSION EXECUTION ENGINE
# ==============================================================================
with tab_runner:
    st.subheader("Step 3: Multi-Submission Engine")
    if not st.session_state.questions_config:
        st.warning("⚠️ No form loaded.")
    else:
        fd = st.session_state.form_data
        total_responses = st.number_input("Total Responses to Send", 1, 1000, 5)
        delay_seconds = st.slider("Delay (sec)", 0.05, 5.0, 0.5)

        if st.button("🔥 Start Multi-Submission", type="primary"):
            success_count = 0
            for i in range(1, total_responses + 1):
                payload = build_submission_payload(st.session_state.questions_config, page_history=fd["page_history"])
                try:
                    res = requests.post(fd["submit_url"], data=payload, headers={"User-Agent": st.session_state.user_agent}, timeout=15)
                    if res.status_code in [200, 302]: success_count += 1
                except Exception:
                    pass
                time.sleep(delay_seconds)
            st.success(f"Completed! Successes: {success_count}/{total_responses}")

# ==============================================================================
# TAB 4: ADMIN PANEL (WAITING LIST CONTROL)
# ==============================================================================
if is_admin and tab_admin:
    with tab_admin:
        st.subheader("👑 Admin Control Panel - Waiting List & Approvals")
        st.caption("Manage requests and issue Access Keys.")
        
        df_wait = database.get_waiting_list()
        
        if df_wait.empty:
            st.info("Waiting list එකේ දැනට කිසිවෙක් නැත.")
        else:
            for idx, row in df_wait.iterrows():
                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 2.5, 1.5, 2])
                    with c1:
                        st.markdown(f"**{row['name']}**")
                    with c2:
                        st.caption(f"Contact: {row['contact']}")
                    with c3:
                        if row['status'] == 'PENDING':
                            st.warning("⏳ Pending")
                        else:
                            st.success("✅ Approved")
                    with c4:
                        if row['status'] == 'PENDING':
                            if st.button(f"Approve #{row['id']}", key=f"app_{row['id']}", type="primary"):
                                new_key = f"SHALEEN_{random.randint(10000, 99999)}"
                                database.approve_user(row['id'], new_key)
                                st.success(f"Approved! Key: `{new_key}`")
                                st.rerun()
                        else:
                            st.code(row['access_key'], language="text")
                st.markdown("---")