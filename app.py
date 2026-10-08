"""
Google Forms Automation & Response Management Tool
Built with Streamlit, Requests, and SQLite3
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
# PAGE CONFIGURATION & THEME STYLING
# ==========================================
st.set_page_config(
    page_title="Google Forms Automation & Response Manager",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics and clean typography
st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

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
        margin: 0;
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .main-header p {
        margin: 0.5rem 0 0 0;
        color: #94A3B8;
        font-size: 0.98rem;
    }

    .badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-right: 0.5rem;
    }

    .badge-primary { background: rgba(59, 130, 246, 0.2); color: #60A5FA; border: 1px solid rgba(96, 165, 250, 0.3); }
    .badge-success { background: rgba(16, 185, 129, 0.2); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.3); }
    .badge-warning { background: rgba(245, 158, 11, 0.2); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.3); }
    .badge-danger  { background: rgba(239, 68, 68, 0.2);  color: #F87171; border: 1px solid rgba(248, 113, 113, 0.3); }

    .card-box {
        background: #1E293B;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.4rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .question-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #F1F5F9;
        margin-bottom: 0.3rem;
    }

    .question-meta {
        font-size: 0.8rem;
        color: #94A3B8;
        margin-bottom: 0.8rem;
        font-family: monospace;
    }

    .percentage-tag {
        font-size: 0.85rem;
        font-weight: 600;
        color: #38BDF8;
        background: rgba(56, 189, 248, 0.12);
        padding: 2px 8px;
        border-radius: 4px;
        float: right;
    }

    .metric-card {
        background: #0F172A;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.06);
        text-align: center;
    }

    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #F8FAFC;
    }

    .metric-label {
        font-size: 0.8rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)

# Initialize SQLite database
database.init_db()

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "form_data" not in st.session_state:
    st.session_state.form_data = None

if "questions_config" not in st.session_state:
    st.session_state.questions_config = []

if "submission_logs" not in st.session_state:
    st.session_state.submission_logs = []

if "raw_form_url" not in st.session_state:
    st.session_state.raw_form_url = ""

if "user_agent" not in st.session_state:
    st.session_state.user_agent = DEFAULT_USER_AGENT

# Demo Sample Form Helper
SAMPLE_DEMO_QUESTIONS = [
    {
        "entry_id": "entry.105432901",
        "raw_entry_id": "105432901",
        "title": "Overall Customer Satisfaction",
        "description": "Rate your overall satisfaction with our product suite.",
        "type": "radio",
        "type_id": 2,
        "is_required": True,
        "options": ["Extremely Satisfied", "Satisfied", "Neutral", "Dissatisfied"],
        "weights": {"Extremely Satisfied": 50.0, "Satisfied": 35.0, "Neutral": 10.0, "Dissatisfied": 5.0},
        "text_mode": "fixed",
        "fixed_value": "",
        "custom_list": "",
        "preset_generator": "name"
    },
    {
        "entry_id": "entry.208741235",
        "raw_entry_id": "208741235",
        "title": "Which features do you use on a weekly basis?",
        "description": "Select all that apply.",
        "type": "checkbox",
        "type_id": 4,
        "is_required": True,
        "options": ["Interactive Dashboard", "Automated Reports", "Data Export / CSV", "API Webhooks"],
        "weights": {"Interactive Dashboard": 80.0, "Automated Reports": 60.0, "Data Export / CSV": 45.0, "API Webhooks": 30.0},
        "text_mode": "fixed",
        "fixed_value": "",
        "custom_list": "",
        "preset_generator": "name"
    },
    {
        "entry_id": "entry.309852147",
        "raw_entry_id": "309852147",
        "title": "Primary Department / Team",
        "description": "Select your operational department.",
        "type": "dropdown",
        "type_id": 3,
        "is_required": True,
        "options": ["Engineering", "Product & Design", "Marketing & Growth", "Customer Support"],
        "weights": {"Engineering": 40.0, "Product & Design": 30.0, "Marketing & Growth": 20.0, "Customer Support": 10.0},
        "text_mode": "fixed",
        "fixed_value": "",
        "custom_list": "",
        "preset_generator": "name"
    },
    {
        "entry_id": "entry.401928374",
        "raw_entry_id": "401928374",
        "title": "Respondent Full Name",
        "description": "Participant name for follow-up.",
        "type": "text",
        "type_id": 0,
        "is_required": True,
        "options": [],
        "weights": {},
        "text_mode": "preset_generator",
        "fixed_value": "",
        "custom_list": "",
        "preset_generator": "name"
    },
    {
        "entry_id": "entry.502839485",
        "raw_entry_id": "502839485",
        "title": "Business Email Address",
        "description": "Contact email.",
        "type": "text",
        "type_id": 0,
        "is_required": True,
        "options": [],
        "weights": {},
        "text_mode": "preset_generator",
        "fixed_value": "",
        "custom_list": "",
        "preset_generator": "email"
    },
    {
        "entry_id": "entry.603948576",
        "raw_entry_id": "603948576",
        "title": "Additional Suggestions or Feedback",
        "description": "Any ideas on how we can improve?",
        "type": "paragraph",
        "type_id": 1,
        "is_required": False,
        "options": [],
        "weights": {},
        "text_mode": "custom_list",
        "fixed_value": "",
        "custom_list": "Loved the snappy UI!\nCould use dark mode toggle.\nLooking forward to the next release.\nVery clean and fast response times.\nOverall great experience.",
        "preset_generator": "feedback"
    }
]

def load_demo_form():
    st.session_state.form_data = {
        "title": "Product Feedback & Survey Demo",
        "view_url": "https://docs.google.com/forms/d/e/1FAIpQLSc_DEMO_SURVEY/viewform",
        "submit_url": "https://docs.google.com/forms/d/e/1FAIpQLSc_DEMO_SURVEY/formResponse",
        "page_count": 1,
        "page_history": "0",
        "questions": SAMPLE_DEMO_QUESTIONS
    }
    st.session_state.questions_config = [dict(q) for q in SAMPLE_DEMO_QUESTIONS]
    st.session_state.raw_form_url = "https://docs.google.com/forms/d/e/1FAIpQLSc_DEMO_SURVEY/viewform"

def sync_preset_into_state(preset_data):
    """Loads preset data into session state and populates widget keys."""
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
    
    # Sync widgets
    for q in q_configs:
        eid = q["entry_id"]
        for opt, val in q.get("weights", {}).items():
            st.session_state[f"w_{eid}_{opt}"] = float(val)
        if "text_mode" in q:
            st.session_state[f"mode_{eid}"] = q["text_mode"]
        if "fixed_value" in q:
            st.session_state[f"fixed_{eid}"] = q["fixed_value"]
        if "custom_list" in q:
            cl = q["custom_list"]
            st.session_state[f"custom_{eid}"] = cl if isinstance(cl, str) else "\n".join(cl)
        if "preset_generator" in q:
            st.session_state[f"gen_{eid}"] = q["preset_generator"]

# ==========================================
# SIDEBAR: PRESET STORAGE & SETTINGS
# ==========================================
with st.sidebar:
    st.markdown("### 💾 Preset Profiles")
    st.caption("Manage saved configurations in SQLite (`form_presets.db`).")
    
    presets_list = database.get_all_presets()
    preset_names = [p["preset_name"] for p in presets_list]
    
    if preset_names:
        selected_preset_name = st.selectbox("📂 Select Saved Preset", ["-- Choose Preset --"] + preset_names)
        
        col_load, col_del = st.columns([1, 1])
        with col_load:
            if st.button("📥 Load Preset", use_container_width=True):
                if selected_preset_name != "-- Choose Preset --":
                    p_data = database.get_preset(selected_preset_name)
                    if p_data:
                        sync_preset_into_state(p_data)
                        st.success(f"Loaded '{selected_preset_name}'!")
                        st.rerun()
        with col_del:
            if st.button("🗑️ Delete", use_container_width=True, type="secondary"):
                if selected_preset_name != "-- Choose Preset --":
                    database.delete_preset(selected_preset_name)
                    st.warning(f"Deleted '{selected_preset_name}'.")
                    st.rerun()
    else:
        st.info("No saved presets yet. Configure a form and save it below!")

    st.markdown("---")
    st.markdown("### ⚙️ Engine Settings")
    st.session_state.user_agent = st.text_area(
        "User-Agent Header", 
        value=st.session_state.user_agent,
        height=80,
        help="Custom User-Agent sent with each HTTP POST request."
    )
    
    st.markdown("---")
    st.markdown("### 💡 Quick Actions")
    if st.button("🧪 Load Sample Demo Form", use_container_width=True):
        load_demo_form()
        st.success("Loaded Demo Form with sample questions & weights!")
        st.rerun()

    if st.button("🧹 Clear Logs", use_container_width=True):
        st.session_state.submission_logs = []
        st.info("Logs cleared.")
        st.rerun()

# ==========================================
# MAIN HEADER
# ==========================================
st.markdown("""
<div class="main-header">
<div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>⚡ Google Forms Automation & Response Manager</h1>
                <p>Smart Entry ID Parser • Weighted Probability Distribution • SQLite Presets • Multi-Submission Engine</p>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 1.3rem; font-weight: 800; letter-spacing: 0.05em; background: linear-gradient(90deg, #F472B6, #60A5FA, #34D399, #FBBF24, #F472B6); background-size: 300% 100%; -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: shimmer 3s linear infinite;">Created By SHALEEN</div>
                <style>@keyframes shimmer { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }</style>
            </div>
        </div>
</div>
""", unsafe_allow_html=True)

# Main Application Tabs
tab_parser, tab_config, tab_runner, tab_code = st.tabs([
    "1. 🔗 Form URL & Parsing", 
    "2. 🎛️ Question Probabilities & Mock Data", 
    "3. 🚀 Multi-Submission Engine",
    "4. 📜 Standalone Python Script"
])

# ==============================================================================
# TAB 1: FORM URL & PARSING
# ==============================================================================
with tab_parser:
    st.subheader("Step 1: Enter Google Form URL")
    st.write("Paste your public Google Form link. The tool will parse `FB_PUBLIC_LOAD_DATA_` to extract all questions, entry IDs, and choices.")

    col_url, col_btn = st.columns([4, 1])
    with col_url:
        input_url = st.text_input(
            "Google Form URL",
            value=st.session_state.raw_form_url,
            placeholder="https://docs.google.com/forms/d/e/.../viewform or forms.gle/...",
            label_visibility="collapsed"
        )
    with col_btn:
        fetch_clicked = st.button("🔍 Fetch & Parse", use_container_width=True, type="primary")

    if fetch_clicked:
        if not input_url.strip():
            st.error("Please provide a valid Google Form URL.")
        else:
            with st.spinner("Connecting to Google Forms and parsing data..."):
                try:
                    parsed_result = fetch_and_parse_form(input_url, custom_user_agent=st.session_state.user_agent)
                    st.session_state.form_data = parsed_result
                    st.session_state.questions_config = parsed_result["questions"]
                    st.session_state.raw_form_url = input_url
                    st.success(f"Successfully parsed form: **{parsed_result['title']}** ({len(parsed_result['questions'])} questions detected)")
                except Exception as e:
                    st.error(f"Error parsing Google Form: {e}")

    # Fallback option: Paste HTML or FB_PUBLIC_LOAD_DATA_ directly
    with st.expander("🛠️ Advanced: Paste Raw Form HTML / FB_PUBLIC_LOAD_DATA_ (Offline Mode)"):
        raw_html_input = st.text_area("Paste HTML source code or script content", height=150)
        col_fb_submit, col_fb_hist = st.columns(2)
        with col_fb_submit:
            manual_submit_url = st.text_input("Manual /formResponse URL", placeholder="https://docs.google.com/forms/d/e/.../formResponse")
        with col_fb_hist:
            manual_page_hist = st.text_input("Manual pageHistory", value="0")
        if st.button("Parse from Raw HTML"):
            if not raw_html_input:
                st.error("HTML input is empty.")
            else:
                try:
                    from test_parser import parse_google_form
                    parsed_from_html = parse_google_form(raw_html_input)
                    sub_url = manual_submit_url.strip() or "https://docs.google.com/forms/d/e/MANUAL_FORM/formResponse"
                    st.session_state.form_data = {
                        "title": parsed_from_html["title"],
                        "view_url": sub_url.replace("/formResponse", "/viewform"),
                        "submit_url": sub_url,
                        "page_count": parsed_from_html["page_count"],
                        "page_history": manual_page_hist or parsed_from_html["page_history"],
                        "questions": parsed_from_html["questions"]
                    }
                    st.session_state.questions_config = parsed_from_html["questions"]
                    st.success(f"Parsed {len(parsed_from_html['questions'])} questions from raw input!")
                except Exception as ex:
                    st.error(f"Failed to parse raw HTML: {ex}")

    # Display Parsed Summary if form is loaded
    if st.session_state.form_data:
        fd = st.session_state.form_data
        st.markdown("---")
        st.markdown(f"### 📋 Form Metadata: `{fd['title']}`")
        
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        with m_c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{len(fd['questions'])}</div>
                <div class="metric-label">Total Questions</div>
            </div>
            """, unsafe_allow_html=True)
        with m_c2:
            mcq_count = sum(1 for q in fd['questions'] if q['options'])
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{mcq_count}</div>
                <div class="metric-label">Choice Fields</div>
            </div>
            """, unsafe_allow_html=True)
        with m_c3:
            text_count = sum(1 for q in fd['questions'] if not q['options'])
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{text_count}</div>
                <div class="metric-label">Text Fields</div>
            </div>
            """, unsafe_allow_html=True)
        with m_c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val">{fd['page_count']}</div>
                <div class="metric-label">Form Pages</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.info(f"**POST Endpoint:** `{fd['submit_url']}` | **pageHistory:** `{fd['page_history']}`")

        # Questions Preview Table
        preview_data = []
        for i, q in enumerate(fd['questions'], 1):
            preview_data.append({
                "#": i,
                "Entry ID": q['entry_id'],
                "Question Title": q['title'],
                "Type": q['type'].upper(),
                "Required": "✅ Yes" if q['is_required'] else "❌ No",
                "Options Count": len(q['options']) if q['options'] else 0
            })
        st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
        st.info("👉 Move to **Tab 2 (Question Probabilities & Mock Data)** to customize weights and text answers.")

# ==============================================================================
# TAB 2: QUESTION PROBABILITIES & MOCK DATA
# ==============================================================================
with tab_config:
    st.subheader("Step 2: Configure Answer Probabilities & Mock Values")
    
    if not st.session_state.questions_config:
        st.warning("⚠️ No form loaded yet. Please enter a URL in Tab 1 or click 'Load Sample Demo Form' in the sidebar.")
    else:
        st.write("Assign custom weights to multiple-choice options or configure realistic mock data generators for text inputs.")
        
        # Batch toolbar
        tb_col1, tb_col2, tb_col3, tb_col4 = st.columns([1.5, 1.5, 2, 2])
        with tb_col1:
            if st.button("⚖️ Equalize All Choice Weights", use_container_width=True):
                for q in st.session_state.questions_config:
                    if q["options"]:
                        eq_w = round(100.0 / len(q["options"]), 1)
                        for opt in q["options"]:
                            q["weights"][opt] = eq_w
                            st.session_state[f"w_{q['entry_id']}_{opt}"] = eq_w
                st.success("All choice options set to equal weights!")
                st.rerun()

        with tb_col2:
            if st.button("🎲 Randomize All Weights", use_container_width=True):
                for q in st.session_state.questions_config:
                    if q["options"]:
                        rands = [random.randint(5, 95) for _ in q["options"]]
                        tot = sum(rands)
                        for opt, r in zip(q["options"], rands):
                            normalized = round((r / tot) * 100.0, 1)
                            q["weights"][opt] = normalized
                            st.session_state[f"w_{q['entry_id']}_{opt}"] = normalized
                st.success("Choice weights randomly distributed!")
                st.rerun()

        with tb_col3:
            # Preset saving dialog
            with st.popover("💾 Save Preset to SQLite", use_container_width=True):
                new_preset_name = st.text_input("Preset Name", value=st.session_state.form_data.get("title", "My Form Preset"))
                if st.button("Save Profile", type="primary", use_container_width=True):
                    if not new_preset_name.strip():
                        st.error("Please enter a preset name.")
                    else:
                        fd = st.session_state.form_data
                        database.save_preset(
                            preset_name=new_preset_name,
                            form_url=fd["submit_url"],
                            page_history=fd["page_history"],
                            questions_config=st.session_state.questions_config
                        )
                        st.success(f"Saved preset '{new_preset_name}' to SQLite database!")
                        time.sleep(0.5)
                        st.rerun()

        st.markdown("---")

        # Dynamic Question Cards
        for idx, q in enumerate(st.session_state.questions_config):
            eid = q["entry_id"]
            type_label = q["type"].upper()
            req_badge = "🔴 Required" if q["is_required"] else "⚪ Optional"

            with st.container():
                st.markdown(f"""
                <div class="card-box">
                    <div style="display: flex; justify-content: space-between; align-items: baseline;">
                        <div class="question-title">{idx+1}. {q['title']}</div>
                        <div>
                            <span class="badge badge-primary">{eid}</span>
                            <span class="badge badge-warning">{type_label}</span>
                            <span class="badge badge-{'danger' if q['is_required'] else 'success'}">{req_badge}</span>
                        </div>
                    </div>
                    <div class="question-meta">{q['description'] if q['description'] else 'No additional instructions'}</div>
                </div>
                """, unsafe_allow_html=True)

                # Rendering Options for Multiple Choice / Dropdown / Checkboxes / Scale
                if q["options"]:
                    st.write("**Option Weights & Probability Distribution:**")
                    opts = q["options"]
                    
                    # Calculate total weight for normalization display
                    curr_weights = {}
                    for opt in opts:
                        key = f"w_{eid}_{opt}"
                        default_val = float(q["weights"].get(opt, round(100.0 / len(opts), 1)))
                        curr_weights[opt] = st.session_state.get(key, default_val)
                    
                    total_w = sum(curr_weights.values()) or 1.0

                    # Render sliders for each option
                    for opt in opts:
                        c_opt_name, c_opt_slider, c_opt_prob = st.columns([3, 5, 2])
                        key = f"w_{eid}_{opt}"
                        default_val = float(q["weights"].get(opt, round(100.0 / len(opts), 1)))
                        
                        with c_opt_name:
                            st.markdown(f"**{opt}**")
                        with c_opt_slider:
                            slider_val = st.slider(
                                label=f"Weight for {opt}",
                                min_value=0.0,
                                max_value=100.0,
                                value=default_val,
                                step=1.0,
                                key=key,
                                label_visibility="collapsed"
                            )
                            q["weights"][opt] = slider_val
                        with c_opt_prob:
                            prob_pct = (slider_val / total_w) * 100.0 if total_w > 0 else 0.0
                            st.markdown(f"<span class='percentage-tag'>{prob_pct:.1f}% prob</span>", unsafe_allow_html=True)

                else:
                    # Rendering Text / Short Answer / Paragraph fields
                    st.write("**Synthetic Data Generation Mode:**")
                    c_mode, c_input = st.columns([2, 5])
                    
                    mode_key = f"mode_{eid}"
                    fixed_key = f"fixed_{eid}"
                    custom_key = f"custom_{eid}"
                    gen_key = f"gen_{eid}"

                    with c_mode:
                        current_mode = q.get("text_mode", "preset_generator")
                        mode_options = ["preset_generator", "custom_list", "fixed", "blank"]
                        mode_labels = {
                            "preset_generator": "🤖 Mock Generator",
                            "custom_list": "📝 Custom Random List",
                            "fixed": "📌 Fixed String",
                            "blank": "⚪ Leave Blank"
                        }
                        selected_mode = st.selectbox(
                            f"Mode for {eid}",
                            options=mode_options,
                            format_func=lambda x: mode_labels[x],
                            index=mode_options.index(current_mode) if current_mode in mode_options else 0,
                            key=mode_key,
                            label_visibility="collapsed"
                        )
                        q["text_mode"] = selected_mode

                    with c_input:
                        if selected_mode == "preset_generator":
                            gen_choices = [
                                ("name", "Random Full Name (e.g. Alex Morgan)"),
                                ("first_name", "Random First Name"),
                                ("last_name", "Random Last Name"),
                                ("email", "Random Realistic Email (e.g. name@gmail.com)"),
                                ("phone", "Random Phone Number"),
                                ("number", "Random Number (1-100)"),
                                ("rating_10", "Random Score (1-10)"),
                                ("positive_feedback", "Positive Review Comment"),
                                ("feedback", "Mixed Customer Feedback Sentiment"),
                                ("date", "Random Date (YYYY-MM-DD)")
                            ]
                            current_gen = q.get("preset_generator", "name")
                            gen_idx = [x[0] for x in gen_choices].index(current_gen) if current_gen in [x[0] for x in gen_choices] else 0
                            
                            chosen_gen = st.selectbox(
                                "Generator Preset",
                                options=[x[0] for x in gen_choices],
                                format_func=lambda x: dict(gen_choices)[x],
                                index=gen_idx,
                                key=gen_key,
                                label_visibility="collapsed"
                            )
                            q["preset_generator"] = chosen_gen
                            
                            # Preview sample
                            preview_val = generate_mock_value(chosen_gen)
                            st.caption(f"Sample generated output: `{preview_val}`")

                        elif selected_mode == "custom_list":
                            existing_list = q.get("custom_list", "")
                            if isinstance(existing_list, list):
                                existing_list = "\n".join(existing_list)
                            list_val = st.text_area(
                                "Enter 1 value per line (random selection at submission)",
                                value=existing_list or "Value 1\nValue 2\nValue 3",
                                key=custom_key,
                                height=85
                            )
                            q["custom_list"] = list_val

                        elif selected_mode == "fixed":
                            fixed_val = st.text_input(
                                "Constant value to submit",
                                value=q.get("fixed_value", "Fixed Answer"),
                                key=fixed_key
                            )
                            q["fixed_value"] = fixed_val

                        elif selected_mode == "blank":
                            st.info("Field will be submitted empty (or omitted if optional).")

                st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# TAB 3: MULTI-SUBMISSION EXECUTION ENGINE
# ==============================================================================
with tab_runner:
    st.subheader("Step 3: Multi-Submission Execution Engine")
    
    if not st.session_state.questions_config:
        st.warning("⚠️ No form configured yet. Please load a form in Tab 1 or Tab 2.")
    else:
        fd = st.session_state.form_data
        st.write(f"Targeting POST endpoint: `{fd['submit_url']}`")
        
        # Controls Row
        c_sub1, c_sub2, c_sub3, c_sub4 = st.columns([2, 2, 2, 2])
        with c_sub1:
            total_responses = st.number_input(
                "Total Responses to Send",
                min_value=1,
                max_value=1000,
                value=10,
                step=5,
                help="Total number of automated responses to send."
            )
        with c_sub2:
            delay_seconds = st.slider(
                "Delay Between Requests (sec)",
                min_value=0.05,
                max_value=5.0,
                value=0.5,
                step=0.05,
                help="time.sleep() between consecutive requests to avoid throttling."
            )
        with c_sub3:
            st.markdown("<br>", unsafe_allow_html=True)
            preview_clicked = st.button("🔍 Preview Single Payload", use_container_width=True)
        with c_sub4:
            st.markdown("<br>", unsafe_allow_html=True)
            test_1_clicked = st.button("🧪 Test 1 Live Submission", use_container_width=True)

        if preview_clicked:
            sample_payload = build_submission_payload(st.session_state.questions_config, page_history=fd["page_history"])
            st.markdown("#### Sample Generated Payload (Dry Run):")
            st.json(sample_payload)

        if test_1_clicked:
            with st.spinner("Submitting test payload..."):
                sample_payload = build_submission_payload(st.session_state.questions_config, page_history=fd["page_history"])
                headers = {"User-Agent": st.session_state.user_agent}
                t0 = time.time()
                try:
                    resp = requests.post(fd["submit_url"], data=sample_payload, headers=headers, timeout=12)
                    latency = round((time.time() - t0) * 1000, 1)
                    is_ok = resp.status_code in [200, 302]
                    
                    st.session_state.submission_logs.insert(0, {
                        "Run #": len(st.session_state.submission_logs) + 1,
                        "Timestamp": datetime.now().strftime("%H:%M:%S"),
                        "Status": "SUCCESS ✅" if is_ok else f"ERROR {resp.status_code} ❌",
                        "Latency (ms)": latency,
                        "Payload Preview": str(sample_payload)[:100] + "..."
                    })
                    
                    if is_ok:
                        st.success(f"Test Submission Successful! (Status: {resp.status_code}, Latency: {latency} ms)")
                    else:
                        st.error(f"Server returned HTTP {resp.status_code}. Response: {resp.text[:300]}")
                except Exception as ex:
                    st.error(f"Failed to submit: {ex}")

        st.markdown("---")
        st.markdown("### 🚀 Automated Execution Runner")

        col_start, col_status = st.columns([1, 3])
        with col_start:
            start_execution = st.button(
                f"🔥 Start Multi-Submission ({total_responses} requests)",
                type="primary",
                use_container_width=True
            )

        # Execution Progress Placeholders
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        stat_c1, stat_c2, stat_c3, stat_c4 = st.columns(4)
        m_sent = stat_c1.empty()
        m_succ = stat_c2.empty()
        m_err = stat_c3.empty()
        m_time = stat_c4.empty()

        if start_execution:
            success_count = 0
            error_count = 0
            headers = {"User-Agent": st.session_state.user_agent}
            start_time = time.time()
            
            for i in range(1, total_responses + 1):
                payload = build_submission_payload(st.session_state.questions_config, page_history=fd["page_history"])
                req_t0 = time.time()
                status_label = "PENDING"
                latency = 0
                
                try:
                    res = requests.post(fd["submit_url"], data=payload, headers=headers, timeout=15)
                    latency = round((time.time() - req_t0) * 1000, 1)
                    if res.status_code in [200, 302]:
                        success_count += 1
                        status_label = "SUCCESS ✅"
                    else:
                        error_count += 1
                        status_label = f"HTTP {res.status_code} ❌"
                except Exception as err:
                    error_count += 1
                    status_label = f"TIMEOUT / {str(err)[:15]} ❌"

                # Update Logs
                st.session_state.submission_logs.insert(0, {
                    "Run #": len(st.session_state.submission_logs) + 1,
                    "Timestamp": datetime.now().strftime("%H:%M:%S"),
                    "Status": status_label,
                    "Latency (ms)": latency,
                    "Payload Preview": str(payload)[:120] + "..."
                })

                # Update UI elements
                progress_val = i / total_responses
                progress_bar.progress(progress_val)
                elapsed = round(time.time() - start_time, 1)
                
                status_text.markdown(f"**Executing:** Submission `{i}` of `{total_responses}` ({int(progress_val*100)}%) | Active Endpoint: `{fd['submit_url']}`")
                
                m_sent.metric("Total Sent", f"{i} / {total_responses}")
                m_succ.metric("Successful", f"{success_count}")
                m_err.metric("Errors", f"{error_count}")
                m_time.metric("Elapsed Time", f"{elapsed}s")

                if i < total_responses and delay_seconds > 0:
                    time.sleep(delay_seconds)

            st.balloons()
            st.success(f"Execution Completed! Sent {total_responses} responses. Successes: {success_count}, Errors: {error_count}.")

        # Live Submission Logs Table
        st.markdown("### 📜 Real-time Execution Logs")
        if st.session_state.submission_logs:
            df_logs = pd.DataFrame(st.session_state.submission_logs)
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
            
            # Export to CSV
            csv_data = df_logs.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Submission Logs (CSV)",
                data=csv_data,
                file_name=f"google_form_submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.caption("No submissions executed yet. Click 'Start Multi-Submission' or 'Test 1 Live Submission' to run.")

# ==============================================================================
# TAB 4: STANDALONE PYTHON SCRIPT EXPORTER
# ==============================================================================
with tab_code:
    st.subheader("Step 4: Standalone Python Script Exporter")
    st.write("Need to run this outside of Streamlit? You can copy or download a standalone Python script configured with your exact weights and mock settings.")

    if not st.session_state.questions_config:
        st.info("Configure a form first to generate the standalone script.")
    else:
        fd = st.session_state.form_data
        script_code = f'''# =====================================================================
# Google Forms Automated Submitter
# Auto-generated by Google Forms Automation & Response Manager
# Form Title: {fd.get("title", "Google Form")}
# =====================================================================

import random
import time
import requests

FORM_URL = "{fd.get("submit_url", "")}"
PAGE_HISTORY = "{fd.get("page_history", "0")}"

HEADERS = {{
    "User-Agent": "{st.session_state.user_agent}"
}}

# Question Configurations with Weighted Probabilities & Mock Generators
QUESTIONS_CONFIG = {json.dumps(st.session_state.questions_config, indent=4)}

def generate_payload():
    payload = {{}}
    for q in QUESTIONS_CONFIG:
        entry_id = q.get("entry_id")
        q_type = q.get("type", "text")
        options = q.get("options", [])
        
        if q_type in ["radio", "dropdown", "scale"] and options:
            weights_dict = q.get("weights", {{}})
            weights = [float(weights_dict.get(opt, 10)) for opt in options]
            if sum(weights) > 0:
                payload[entry_id] = random.choices(options, weights=weights, k=1)[0]
            elif q.get("is_required", False):
                payload[entry_id] = random.choice(options)
                
        elif q_type == "checkbox" and options:
            weights_dict = q.get("weights", {{}})
            chosen = [opt for opt in options if random.uniform(0, 100) <= float(weights_dict.get(opt, 50))]
            if not chosen and q.get("is_required", False):
                chosen = [random.choice(options)]
            payload[entry_id] = chosen
            
        else:
            mode = q.get("text_mode", "fixed")
            if mode == "fixed":
                payload[entry_id] = q.get("fixed_value", "")
            elif mode == "custom_list":
                raw = q.get("custom_list", "")
                lines = [x.strip() for x in (raw.splitlines() if isinstance(raw, str) else raw) if x.strip()]
                payload[entry_id] = random.choice(lines) if lines else "Sample"
            elif mode == "preset_generator":
                payload[entry_id] = f"Test Respondent {{random.randint(100, 999)}}"

    if PAGE_HISTORY:
        payload["pageHistory"] = PAGE_HISTORY
    return payload

def run_submissions(total_count=10, delay_sec=0.5):
    print(f"Starting {{total_count}} submissions to {{FORM_URL}}...")
    successes = 0
    errors = 0
    
    for i in range(1, total_count + 1):
        payload = generate_payload()
        try:
            res = requests.post(FORM_URL, data=payload, headers=HEADERS, timeout=15)
            if res.status_code in [200, 302]:
                print(f"[OK] {{i}}/{{total_count}} Status: {{res.status_code}}")
                successes += 1
            else:
                print(f"[FAIL] {{i}}/{{total_count}} Status: {{res.status_code}}")
                errors += 1
        except Exception as e:
            print(f"[ERROR] {{i}}/{{total_count}} {{e}}")
            errors += 1
            
        if i < total_count and delay_sec > 0:
            time.sleep(delay_sec)
            
    print(f"Finished! Successes: {{successes}}, Errors: {{errors}}")

if __name__ == "__main__":
    run_submissions(total_count=10, delay_sec=0.5)
'''
        st.code(script_code, language="python")
        st.download_button(
            label="📥 Download Standalone Python Script",
            data=script_code,
            file_name="google_form_submitter.py",
            mime="text/x-python"
        )