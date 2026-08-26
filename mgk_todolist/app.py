import streamlit as st
import pdfplumber
import re
import uuid
import pandas as pd
import time
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="TaskFlow Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .badge-p1 { background-color: #FF4D4D; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p2 { background-color: #FFA500; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p3 { background-color: #38EF7D; color: black; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .cat-badge { background-color: #21262D; color: #8B949E; border: 1px solid #30363D; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. MEMORY INITIALIZATION ---
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# --- 3. CALLBACK FUNCTIONS (THE FIX) ---
# Callbacks happen *before* the page reloads, ensuring data is never lost.

def add_quick_task():
    title = st.session_state.q_title
    if title.strip():
        cat = st.session_state.q_cat.strip() if st.session_state.q_cat.strip() else "General"
        subs = [{"text": s.strip(), "completed": False} for s in st.session_state.q_subs.split(',') if s.strip()]
        
        st.session_state.tasks.append({
            "id": str(uuid.uuid4()),
            "text": title.strip(),
            "category": cat,
            "priority": st.session_state.q_prio,
            "completed": False,
            "subtasks": subs
        })
        # Clear inputs automatically
        st.session_state.q_title = ""
        st.session_state.q_cat = ""
        st.session_state.q_subs = ""

def extract_from_text(text):
    if not text.strip(): return
    lines = text.split('\n')
    current_cat = "Imported"
    
    for line in lines:
        line = line.strip()
        if not line: continue
            
        is_bullet = re.match(r'^(?:[-*•]|\d+[\.\)])\s', line)
        is_keyword = re.match(r'^(?:task|to do|todo|action|item)[\s:]', line, re.IGNORECASE)
        
        if is_bullet or is_keyword:
            clean_text = re.sub(r'^(?:[-*•]|\d+[\.\)])\s*', '', line)
            clean_text = re.sub(r'^(?:task|to do|todo|action|item)[\s:]*', '', clean_text, flags=re.IGNORECASE).strip()
            
            if clean_text:
                low = clean_text.lower()
                prio = "P1 (High)" if any(w in low for w in ['urgent', 'asap', 'critical']) else ("P2 (Medium)" if any(w in low for w in ['medium', 'important']) else "P3 (Low)")
                
                st.session_state.tasks.append({
                    "id": str(uuid.uuid4()), "text": clean_text, "category": current_cat,
                    "priority": prio, "completed": False, "subtasks": []
                })
        elif 2 < len(line) < 40 and not line.endswith('.'):
            current_cat = line.strip().strip(':')

def process_pdf():
    if st.session_state.pdf_uploader is not None:
        pdf_bytes = st.session_state.pdf_uploader.getvalue()
        text = ""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted: text += extracted + "\n"
        extract_from_text(text)

def process_paste():
    if st.session_state.paste_area:
        extract_from_text(st.session_state.paste_area)
        st.session_state.paste_area = ""

# --- 4. SIDEBAR: TIMER & EXPORT ---
with st.sidebar:
    st.header("⚡ Focus Zone")
    timer_mins = st.number_input("Focus duration (mins)", min_value=1, max_value=60, value=25)
    if st.button("▶️ Start Focus Timer", type="primary"):
        st.info("Focus session active! Stay on task...")
        bar = st.progress(0)
        total_sec = timer_mins * 60
        for i in range(total_sec):
            time.sleep(1)
            bar.progress((i + 1) / total_sec)
        st.success("Session complete! 🎉")
        st.balloons()
        
    st.divider()
    st.header("💾 Export Data")
    if st.session_state.tasks:
        export_df = pd.DataFrame([{
            "Task Title": t.get("text", ""),
            "Category": t.get("category", ""),
            "Priority": t.get("priority", ""),
            "Status": "Done" if t.get("completed") else "Pending"
        } for t in st.session_state.tasks])
        
        st.download_button(
            label="📥 Download CSV",
            data=export_df.to_csv(index=False).encode('utf-8'),
            file_name="taskflow_export.csv",
            mime="text/csv"
        )
    if st.button("🗑️ Clear All Tasks"):
        st.session_state.tasks = []
        st.rerun()

# --- 5. HEADER ---
st.title("⚡Hey! 🛑 I cannot see our older messages in this window. The chat history is completely blank on my end right now. 

To fix the problem and give you the working script (without the Android/EXE app stuff 🚫📱), I need a quick favour:

1. 📋 **Paste the current code** you have.
2. 🎯 **Drop a quick list of the features** you need it to do.

Paste them below, and we will get this sorted out immediately! 🛠️🐛
