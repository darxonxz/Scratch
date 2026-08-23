import streamlit as st
import pdfplumber
import re
import uuid
import pandas as pd
import time
import io

# --- 1. CONFIG & MODERN DARK UI THEME ---
st.set_page_config(page_title="TaskFlow Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #4facfe, #00f2fe); }
    
    /* Modern card container styling */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] {
        background-color: #161B22; border-radius: 10px; padding: 12px; border: 1px solid #30363D;
    }
    
    /* Priority & Category Badges */
    .badge-p1 { background-color: #FF4D4D; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p2 { background-color: #FFA500; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p3 { background-color: #38EF7D; color: black; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .cat-badge { background-color: #21262D; color: #8B949E; border: 1px solid #30363D; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; }
    .sub-badge { background-color: #1F2937; color: #9CA3AF; padding: 1px 6px; border-radius: 4px; font-size: 0.70rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. SESSION STATE MANAGEMENT & REPAIR ---
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# Ensure older tasks have all necessary keys to avoid KeyError
for task in st.session_state.tasks:
    task.setdefault('priority', 'P3 (Low)')
    task.setdefault('category', 'General')
    task.setdefault('subtasks', [])
    task.setdefault('completed', False)

# --- 3. SMART TEXT & PDF PARSER ---
def parse_text_to_tasks(text):
    lines = text.split('\n')
    current_cat = "General"
    new_tasks = []

    for line in lines:
        raw_line = line
        stripped_line = line.strip()
        if not stripped_line: 
            continue

        # Check for indented lines (subtasks)
        is_indented = len(raw_line) - len(raw_line.lstrip()) >= 2
        is_bullet = re.match(r'^[-*•]\s', stripped_line)
        is_keyword = stripped_line.lower().startswith(('to do', 'task', 'action'))

        if (is_bullet or is_keyword) and is_indented and new_tasks:
            # Add as subtask to the last created task
            clean_sub = re.sub(r'^[-*•]\s*(task:|to do:)?\s*', '', stripped_line, flags=re.IGNORECASE).strip()
            new_tasks[-1]['subtasks'].append({"text": clean_sub, "completed": False})

        elif is_bullet or is_keyword:
            # Main task
            clean_text = re.sub(r'^[-*•]\s*(task:|to do:)?\s*', '', stripped_line, flags=re.IGNORECASE).strip()
            priority = "P1 (High)" if any(w in clean_text.lower() for w in ['urgent', 'asap', 'today', 'important']) else "P3 (Low)"
            
            new_tasks.append({
                "id": str(uuid.uuid4()),
                "text": clean_text,
                "category": current_cat,
                "priority": priority,
                "completed": False,
                "subtasks": []
            })
        elif 2 < len(stripped_line) < 40:
            # Short line without bullet treated as Category Header
            current_cat = stripped_line.strip(':')

    st.session_state.tasks.extend(new_tasks)

# --- 4. SIDEBAR: FOCUS TIMER & BACKUP/RESTORE ---
with st.sidebar:
    st.header("⚡ Focus Zone")
    st.caption("TickTick-style Pomodoro Timer")
    timer_mins = st.number_input("Focus duration (mins)", min_value=1, max_value=60, value=25)
    if st.button("▶️ Start Timer"):
        bar = st.progress(0)
        total_sec = timer_mins * 60
        for i in range(total_sec):
            time.sleep(1)
            bar.progress((i + 1) / total_sec)
        st.success("Focus block finished! Take a break. 🎉")
        st.balloons()
        
    st.divider()
    st.header("💾 Backup & Restore")
    if st.session_state.tasks:
        df_export = pd.DataFrame(st.session_state.tasks)
        csv_data = df_export.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export CSV", data=csv_data, file_name="my_tasks.csv", mime="text/csv")
    
    uploaded_csv = st.file_uploader("📤 Restore from CSV", type=["csv"])
    if uploaded_csv and st.button("Load Backup"):
        df_in = pd.read_csv(uploaded_csv)
        st.session_state.tasks = df_in.to_dict(orient="records")
        st.rerun()

# --- 5. TOP METRICS DASHBOARD ---
st.title("⚡ TaskFlow Pro")

if st.session_state.tasks:
    total_cnt = len(st.session_state.tasks)
    done_cnt = sum(1 for t in st.session_state.tasks if t.get('completed', False))
    progress = done_cnt / total_cnt if total_cnt > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tasks", total_cnt)
    col2.metric("Completed", done_cnt)
    col3.metric("Completion Rate", f"{int(progress * 100)}%")
    
    st.progress(progress)
    if progress == 1.0:
        st.snow()

st.divider()

# --- 6. TASK EXTRACTION & INPUT HUB ---
with st.expander("➕ Extract Tasks (PDF, Text, or Quick Add)", expanded=not bool(st.session_state.tasks)):
    tab_quick, tab_pdf, tab_paste = st.tabs(["⚡ Quick Add", "📄 Upload PDF", "📋 Paste Notes"])
    
    with tab_quick:
        qc1, qc2, qc3 = st.columns([3, 2, 2])
        with qc1: q_title = st.text_input("Task Title", placeholder="e.g., Submit budget report", label_visibility="collapsed")
        with qc2: q_cat = st.text_input("Category", placeholder="Work / Personal", label_visibility="collapsed")
        with qc3: q_prio = st.selectbox("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], index=1, label_visibility="collapsed")
        q_subs = st.text_input("Subtasks (comma-separated)", placeholder="Subtask 1, Subtask 2")
        if st.button("Add Task 🚀") and q_title:
            sub_list = [{"text": s.strip(), "completed": False} for s in q_subs.split(',') if s.strip()]
            st.session_state.tasks.append({
                "id": str(uuid.uuid4()), "text": q_title, "category": q_cat or "General", 
                "priority": q_prio, "completed": False, "subtasks": sub_list
            })
            st.rerun()

    with tab_pdf:
        pdf_file = st.file_uploader("Choose a PDF file", type="pdf")
        if st.button("Extract PDF Tasks") and pdf_file:
            pdf_text = "".join([page.extract_text() or "" for page in pdfplumber.open(pdf_file).pages])
            parse_text_to_tasks(pdf_text)
            st.toast("Tasks extracted from PDF! 📄")
            st.rerun()

    with tab_paste:
        raw_pasted = st.text_area("Paste notes or bullet lists:")
        if st.button("Extract Pasted Tasks") and raw_pasted:
            parse_text_to_tasks(raw_pasted)
            st.toast("Notes converted to tasks! 📋")
            st.rerun()

# --- 7. MAIN VIEWS (CHECKLIST VS BULK SPREADSHEET ORGANIZER) ---
if st.session_state.tasks:
    view_checklist, view_bulk = st.tabs(["🎯 Focus Checklist", "🛠️ Bulk Organizer"])

    # ==========================================
    # VIEW 1: ADHD Focus Checklist
    # ==========================================
    with view_checklist:
        fc1, fc2, fc3, fc4 = st.columns([3, 2, 2, 1])
        with fc1: search_q = st.text_input("🔍 Search keyword").lower()
        with fc2: 
            cats = list(set(t.get('category', 'General') for t in st.session_state.tasks))
            sel_cats = st.multiselect("Category Filter", cats, default=cats)
        with fc3: 
            sel_prios = st.multiselect("Priority Filter", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], default=["P1 (High)", "P2 (Medium)", "P3 (Low)"])
        with fc4:
            st.write(""); st.write("")
            if st.button("🗑️ Clear All"): 
                st.session_state.tasks = []
                st.rerun()

        # Apply Filters safely
        filtered_list = [
            t for t in st.session_state.tasks 
            if (search_q in t.get('text', '').lower() or search_q in t.get('category', '').lower())
            and t.get('category', 'General') in sel_cats
            and t.get('priority', 'P3 (Low)') in sel_prios
        ]
        
        active_items = [t for t in filtered_list if not t.get('completed', False)]
        done_items = [t for t in filtered_list if t.get('completed', False)]

        st.subheader(f"🎯 To-Do ({len(active_items)})")
        for t in active_items:
            prio = t.get('priority', 'P3 (Low)')
            p_class = "badge-p1" if "P1" in prio else ("badge-p2" if "P2" in prio else "badge-p3")
            
            c_chk, c_txt, c_pop = st.columns([0.05, 0.85, 0.1])
            with c_chk:
                if st.checkbox("", value=False, key=f"chk_{t['id']}"):
                    t['completed'] = True
                    st.toast("Task completed! 🎉")
                    st.rerun()
            with c_txt:
                st.markdown(
                    f"**{t.get('text', '')}** <span class='{p_class}'>{prio}</span> <span class='cat-badge'>📁 {t.get('category', 'General')}</span>", 
                    unsafe_allow_html=True
                )
                # Subtasks expander
                if t.get('subtasks'):
                    done_sub_cnt = sum(1 for s in t['subtasks'] if s.get('completed'))
                    with st.expander(f"Subtasks ({done_sub_cnt}/{len(t['subtasks'])})"):
                        for idx, sub in enumerate(t['subtasks']):
                            s_chk = st.checkbox(
                                f"~~{sub['text']}~~" if sub.get('completed') else sub['text'], 
                                value=sub.get('completed', False), 
                                key=f"s_{t['id']}_{idx}"
                            )
                            sub['completed'] = s_chk

            with c_pop:
                # Inline Editing Popover
                with st.popover("✏️"):
                    st.caption("Quick Edit Task")
                    e_text = st.text_input("Title", t.get('text', ''), key=f"et_{t['id']}")
                    e_cat = st.text_input("Category", t.get('category', 'General'), key=f"ec_{t['id']}")
                    e_prio = st.selectbox("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], 
                                          index=["P1 (High)", "P2 (Medium)", "P3 (Low)"].index(prio) if prio in ["P1 (High)", "P2 (Medium)", "P3 (Low)"] else 2, 
                                          key=f"ep_{t['id']}")
                    if st.button("Save", key=f"eb_{t['id']}"):
                        t['text'], t['category'], t['priority'] = e_text, e_cat, e_prio
                        st.rerun()

        # Completed items auto-pushed to bottom
        if done_items:
            st.markdown("---")
            st.subheader(f"✅ Completed ({len(done_items)})")
            for t in done_items:
                c_chk, c_txt = st.columns([0.05, 0.95])
                with c_chk:
                    if not st.checkbox("", value=True, key=f"chk_d_{t['id']}"):
                        t['completed'] = False
                        st.rerun()
                with c_txt:
                    st.markdown(f"~~{t.get('text', '')}~~ <span class='cat-badge'>📁 {t.get('category', 'General')}</span>", unsafe_allow_html=True)

    # ==========================================
    # VIEW 2: Bulk Organizer (Excel/Spreadsheet Mode)
    # ==========================================
    with view_bulk:
        st.info("💡 **Pro-Tip:** Double click cells to edit text, select priorities, or update categories across rows in bulk!")
        
        df = pd.DataFrame(st.session_state.tasks)
        
        # Interactive Excel Grid
        edited_df = st.data_editor(
            df,
            column_config={
                "id": None,
                "subtasks": None,
                "completed": st.column_config.CheckboxColumn("Done?", width="small"),
                "text": st.column_config.TextColumn("Task Title", width="large", required=True),
                "category": st.column_config.TextColumn("Category", width="medium"),
                "priority": st.column_config.SelectboxColumn("Priority", options=["P1 (High)", "P2 (Medium)", "P3 (Low)"], width="medium")
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="spreadsheet_editor"
        )
        
        if st.button("💾 Apply Grid Changes", type="primary"):
            updated_tasks = []
            for _, row in edited_df.iterrows():
                if pd.isna(row.get('text')) or str(row.get('text')).strip() == "":
                    continue
                
                t_id = str(row.get('id')) if pd.notna(row.get('id')) and str(row.get('id')).strip() != "" else str(uuid.uuid4())
                subs = row.get('subtasks') if isinstance(row.get('subtasks'), list) else []

                updated_tasks.append({
                    "id": t_id,
                    "text": str(row['text']).strip(),
                    "category": str(row['category']).strip() if pd.notna(row['category']) else "General",
                    "priority": str(row['priority']) if pd.notna(row['priority']) else "P3 (Low)",
                    "completed": bool(row.get('completed', False)),
                    "subtasks": subs
                })
            
            st.session_state.tasks = updated_tasks
            st.toast("Grid saved successfully! 🎉")
            time.sleep(0.3)
            st.rerun()
