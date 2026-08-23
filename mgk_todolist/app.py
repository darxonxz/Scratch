import streamlit as st
import pdfplumber
import re
import uuid
import pandas as pd
import time

# --- 1. APP CONFIG & MODERN CSS THEME ---
st.set_page_config(page_title="TaskFlow Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    /* Global modern UI styling */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #4facfe, #00f2fe); }
    
    /* Modern card containers */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] {
        background-color: #161B22;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #30363D;
    }
    
    /* Priority Pill Badges */
    .badge-p1 { background-color: #FF4D4D; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p2 { background-color: #FFA500; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p3 { background-color: #38EF7D; color: black; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .cat-badge { background-color: #21262D; color: #8B949E; border: 1px solid #30363D; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. SESSION STATE MANAGEMENT ---
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# --- 3. HELPER FUNCTIONS ---
def parse_text_to_tasks(text):
    lines = text.split('\n')
    current_cat = "General"
    new_tasks = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
            
        # Check if line is a bullet/task
        is_bullet = re.match(r'^[-*•]\s', line)
        is_keyword = line.lower().startswith(('to do', 'task', 'action'))
        
        if is_bullet or is_keyword:
            clean_text = re.sub(r'^[-*•]\s*(task:|to do:)?\s*', '', line, flags=re.IGNORECASE)
            # Default priority assignment based on urgent keywords
            priority = "P1 (High)" if any(w in clean_text.lower() for w in ['urgent', 'asap', 'today', 'important']) else "P3 (Low)"
            
            new_tasks.append({
                "id": str(uuid.uuid4()),
                "text": clean_text.strip(),
                "category": current_cat,
                "priority": priority,
                "completed": False,
                "subtasks": []
            })
        else:
            # Assume short line without bullet is a category
            if 2 < len(line) < 35:
                current_cat = line.strip().strip(':')
                
    st.session_state.tasks.extend(new_tasks)

def add_single_task(title, category, priority, subtasks_str):
    if title:
        subtasks_list = [{"text": s.strip(), "completed": False} for s in subtasks_str.split(',') if s.strip()]
        st.session_state.tasks.append({
            "id": str(uuid.uuid4()),
            "text": title,
            "category": category if category else "General",
            "priority": priority,
            "completed": False,
            "subtasks": subtasks_list
        })
        st.toast("Task added! 🚀")

# --- 4. SIDEBAR: FOCUS TIMER & EXPORT ---
with st.sidebar:
    st.header("⚡ Focus Zone")
    st.caption("TickTick-style Pomodoro Timer")
    
    timer_mins = st.number_input("Focus minutes", min_value=1, max_value=60, value=25)
    if st.button("▶️ Start Focus Session"):
        st.info("Focus session active! Stay on task...")
        bar = st.progress(0)
        total_sec = timer_mins * 60
        for i in range(total_sec):
            time.sleep(1)
            bar.progress((i + 1) / total_sec)
        st.success("Session complete! Take a break. 🎉")
        st.balloons()
        
    st.divider()
    st.header("💾 Backup & Export")
    if st.session_state.tasks:
        df = pd.DataFrame(st.session_state.tasks)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Tasks (CSV)", data=csv, file_name="my_tasks.csv", mime="text/csv")

# --- 5. DASHBOARD & METRICS ---
st.title("⚡ TaskFlow Pro")

if st.session_state.tasks:
    total_tasks = len(st.session_state.tasks)
    completed_tasks = sum(1 for t in st.session_state.tasks if t['completed'])
    progress = completed_tasks / total_tasks
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Total Tasks", total_tasks)
    col_m2.metric("Completed", completed_tasks)
    col_m3.metric("Completion Rate", f"{int(progress * 100)}%")
    
    st.progress(progress)
    if progress == 1.0:
        st.snow()

st.divider()

# --- 6. TASK INPUT HUB ---
input_tab1, input_tab2, input_tab3 = st.tabs(["➕ Quick Add", "📄 PDF Extractor", "📋 Paste Notes"])

with input_tab1:
    col_a, col_b, col_c = st.columns([3, 2, 2])
    with col_a:
        quick_title = st.text_input("Task title", placeholder="e.g., Complete project report", label_visibility="collapsed")
    with col_b:
        quick_cat = st.text_input("Category", placeholder="Work / Personal", label_visibility="collapsed")
    with col_c:
        quick_prio = st.selectbox("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], index=1, label_visibility="collapsed")
    
    quick_sub = st.text_input("Subtasks (comma-separated)", placeholder="Subtask 1, Subtask 2")
    if st.button("Add Task 🚀"):
        add_single_task(quick_title, quick_cat, quick_prio, quick_sub)
        st.rerun()

with input_tab2:
    pdf_file = st.file_uploader("Upload PDF", type="pdf")
    if st.button("Extract PDF Tasks"):
        if pdf_file:
            text = ""
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
            parse_text_to_tasks(text)
            st.success("PDF parsed!")
            st.rerun()

with input_tab3:
    raw_text = st.text_area("Paste text or notes:")
    if st.button("Extract Pasted Tasks"):
        if raw_text:
            parse_text_to_tasks(raw_text)
            st.success("Notes parsed!")
            st.rerun()

# --- 7. SLICERS, FILTERS & SEARCH ---
if st.session_state.tasks:
    st.divider()
    f_col1, f_col2, f_col3, f_col4 = st.columns([3, 2, 2, 1])
    
    with f_col1:
        search_query = st.text_input("🔍 Search tasks", placeholder="Type keyword...").lower()
    with f_col2:
        all_cats = list(set(t['category'] for t in st.session_state.tasks))
        selected_cats = st.multiselect("Category", all_cats, default=all_cats)
    with f_col3:
        selected_prios = st.multiselect("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], default=["P1 (High)", "P2 (Medium)", "P3 (Low)"])
    with f_col4:
        st.write("")
        st.write("")
        if st.button("🗑️ Clear All"):
            st.session_state.tasks = []
            st.rerun()

    # Apply Filters
    filtered = [
        t for t in st.session_state.tasks 
        if (search_query in t['text'].lower() or search_query in t['category'].lower())
        and t['category'] in selected_cats
        and t['priority'] in selected_prios
    ]

    active_tasks = [t for t in filtered if not t['completed']]
    done_tasks = [t for t in filtered if t['completed']]

    # --- 8. TASK LIST RENDERING ---
    st.subheader(f"🎯 To-Do ({len(active_tasks)})")
    for t in active_tasks:
        p_class = "badge-p1" if "P1" in t['priority'] else ("badge-p2" if "P2" in t['priority'] else "badge-p3")
        
        col_chk, col_content = st.columns([0.05, 0.95])
        with col_chk:
            if st.checkbox("", value=False, key=f"chk_{t['id']}"):
                t['completed'] = True
                st.toast("Task completed! 🎉")
                st.rerun()
        with col_content:
            st.markdown(
                f"**{t['text']}** <span class='{p_class}'>{t['priority']}</span> <span class='cat-badge'>📁 {t['category']}</span>", 
                unsafe_allow_html=True
            )
            # Render Subtasks if available
            if t['subtasks']:
                with st.expander(f"Subtasks ({sum(1 for s in t['subtasks'] if s['completed'])}/{len(t['subtasks'])})"):
                    for idx, sub in enumerate(t['subtasks']):
                        sub_chk = st.checkbox(sub['text'], value=sub['completed'], key=f"sub_{t['id']}_{idx}")
                        sub['completed'] = sub_chk

    # Done section (auto-pushed to bottom)
    if done_tasks:
        st.markdown("---")
        st.subheader(f"✅ Completed ({len(done_tasks)})")
        for t in done_tasks:
            col_chk, col_content = st.columns([0.05, 0.95])
            with col_chk:
                if not st.checkbox("", value=True, key=f"chk_{t['id']}"):
                    t['completed'] = False
                    st.rerun()
            with col_content:
                st.markdown(
                    f"~~{t['text']}~~ <span class='cat-badge'>📁 {t['category']}</span>", 
                    unsafe_allow_html=True
                )
