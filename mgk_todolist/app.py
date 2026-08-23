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
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #4facfe, #00f2fe); }
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] {
        background-color: #161B22; border-radius: 10px; padding: 10px; border: 1px solid #30363D;
    }
    .badge-p1 { background-color: #FF4D4D; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p2 { background-color: #FFA500; color: white; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p3 { background-color: #38EF7D; color: black; padding: 3px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .cat-badge { background-color: #21262D; color: #8B949E; border: 1px solid #30363D; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. SESSION STATE MANAGEMENT & AUTO-REPAIR ---
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# Ensure older tasks have all the right keys so the app never crashes
for task in st.session_state.tasks:
    task.setdefault('priority', 'P3 (Low)')
    task.setdefault('category', 'General')
    task.setdefault('subtasks', [])
    task.setdefault('completed', False)

# --- 3. HELPER FUNCTIONS ---
def parse_text_to_tasks(text):
    lines = text.split('\n')
    current_cat = "Imported"
    new_tasks = []
    
    for line in lines:
        line = line.strip()
        if not line: continue
            
        is_bullet = re.match(r'^[-*•]\s', line)
        is_keyword = line.lower().startswith(('to do', 'task', 'action'))
        
        if is_bullet or is_keyword:
            clean_text = re.sub(r'^[-*•]\s*(task:|to do:)?\s*', '', line, flags=re.IGNORECASE).strip()
            priority = "P1 (High)" if any(w in clean_text.lower() for w in ['urgent', 'asap', 'today', 'important']) else "P3 (Low)"
            
            new_tasks.append({
                "id": str(uuid.uuid4()),
                "text": clean_text,
                "category": current_cat,
                "priority": priority,
                "completed": False,
                "subtasks": []
            })
        elif 2 < len(line) < 35: # Likely a category header
            current_cat = line.strip().strip(':')
                
    st.session_state.tasks.extend(new_tasks)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚡ Focus Zone")
    timer_mins = st.number_input("Pomodoro minutes", min_value=1, max_value=60, value=25)
    if st.button("▶️ Start Focus Timer"):
        bar = st.progress(0)
        total_sec = timer_mins * 60
        for i in range(total_sec):
            time.sleep(1)
            bar.progress((i + 1) / total_sec)
        st.success("Session complete! 🎉")
        st.balloons()
        
    st.divider()
    if st.session_state.tasks:
        df = pd.DataFrame(st.session_state.tasks)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Backup Tasks (CSV)", data=csv, file_name="my_tasks.csv", mime="text/csv")

# --- 5. TOP METRICS & PROGRESS ---
st.title("⚡ TaskFlow Pro")

if st.session_state.tasks:
    total = len(st.session_state.tasks)
    done = sum(1 for t in st.session_state.tasks if t.get('completed', False))
    progress = done / total if total > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total", total)
    c2.metric("Done", done)
    c3.metric("Score", f"{int(progress * 100)}%")
    st.progress(progress)
    if progress == 1.0: st.snow()

st.divider()

# --- 6. ADD NEW TASKS HUB ---
with st.expander("➕ Add New Tasks (Manual, PDF, or Paste)", expanded=not bool(st.session_state.tasks)):
    t1, t2, t3 = st.tabs(["Quick Add", "Upload PDF", "Paste Notes"])
    
    with t1:
        qa_col1, qa_col2, qa_col3 = st.columns([3, 2, 2])
        with qa_col1: q_title = st.text_input("Title", placeholder="Task name", label_visibility="collapsed")
        with qa_col2: q_cat = st.text_input("Category", placeholder="Project / Area", label_visibility="collapsed")
        with qa_col3: q_prio = st.selectbox("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], index=2, label_visibility="collapsed")
        if st.button("Add Task 🚀") and q_title:
            st.session_state.tasks.append({"id": str(uuid.uuid4()), "text": q_title, "category": q_cat or "General", "priority": q_prio, "completed": False, "subtasks": []})
            st.rerun()

    with t2:
        pdf_file = st.file_uploader("Upload PDF", type="pdf")
        if st.button("Extract PDF Tasks") and pdf_file:
            text = "".join([page.extract_text() or "" for page in pdfplumber.open(pdf_file).pages])
            parse_text_to_tasks(text)
            st.rerun()

    with t3:
        raw_text = st.text_area("Paste text or bullet points:")
        if st.button("Extract Pasted Tasks") and raw_text:
            parse_text_to_tasks(raw_text)
            st.rerun()

# --- 7. MAIN VIEWS (CHECKLIST VS BULK EDIT) ---
if st.session_state.tasks:
    view_tab, organize_tab = st.tabs(["🎯 Focus Checklist", "🛠️ Bulk Organizer"])

    # ==========================================
    # VIEW TAB: The ADHD-Friendly Dopamine Checklist
    # ==========================================
    with view_tab:
        f1, f2, f3, f4 = st.columns([3, 2, 2, 1])
        with f1: sq = st.text_input("🔍 Search").lower()
        with f2: 
            all_c = list(set(t.get('category', 'General') for t in st.session_state.tasks))
            sel_c = st.multiselect("Category", all_c, default=all_c)
        with f3: 
            sel_p = st.multiselect("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], default=["P1 (High)", "P2 (Medium)", "P3 (Low)"])
        with f4:
            st.write(""); st.write("")
            if st.button("🗑️ Clear All"): st.session_state.tasks = []; st.rerun()

        filtered = [t for t in st.session_state.tasks if (sq in t.get('text', '').lower() or sq in t.get('category', '').lower()) and t.get('category') in sel_c and t.get('priority') in sel_p]
        active = [t for t in filtered if not t.get('completed')]
        done_list = [t for t in filtered if t.get('completed')]

        st.subheader(f"🎯 Active ({len(active)})")
        for t in active:
            prio = t.get('priority', 'P3 (Low)')
            p_cls = "badge-p1" if "P1" in prio else ("badge-p2" if "P2" in prio else "badge-p3")
            
            # 3 Columns: Checkbox, Text, Edit Button
            c_chk, c_txt, c_edit = st.columns([0.05, 0.85, 0.1])
            with c_chk:
                if st.checkbox("", key=f"chk_{t['id']}"):
                    t['completed'] = True
                    st.rerun()
            with c_txt:
                st.markdown(f"**{t.get('text', '')}** <span class='{p_cls}'>{prio}</span> <span class='cat-badge'>📁 {t.get('category', 'General')}</span>", unsafe_allow_html=True)
            with c_edit:
                # INLINE EDIT POPOVER
                with st.popover("✏️"):
                    st.caption("Quick Edit")
                    n_txt = st.text_input("Task", t.get('text',''), key=f"e_txt_{t['id']}")
                    n_cat = st.text_input("Category", t.get('category',''), key=f"e_cat_{t['id']}")
                    n_prio = st.selectbox("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], 
                                          index=["P1 (High)", "P2 (Medium)", "P3 (Low)"].index(prio) if prio in ["P1 (High)", "P2 (Medium)", "P3 (Low)"] else 2, 
                                          key=f"e_prio_{t['id']}")
                    if st.button("Save", key=f"e_btn_{t['id']}"):
                        t['text'], t['category'], t['priority'] = n_txt, n_cat, n_prio
                        st.rerun()

        if done_list:
            st.markdown("---")
            st.subheader(f"✅ Done ({len(done_list)})")
            for t in done_list:
                c_chk, c_txt = st.columns([0.05, 0.95])
                with c_chk:
                    if not st.checkbox("", value=True, key=f"chk_d_{t['id']}"):
                        t['completed'] = False
                        st.rerun()
                with c_txt:
                    st.markdown(f"~~{t.get('text', '')}~~ <span class='cat-badge'>📁 {t.get('category', 'General')}</span>", unsafe_allow_html=True)

    # ==========================================
    # ORGANIZE TAB: The Spreadsheet Bulk Editor
    # ==========================================
    with organize_tab:
        st.info("💡 **Pro-tip:** Double click any cell to edit. You can drag to copy-paste categories or priorities across multiple rows just like Excel!")
        
        df = pd.DataFrame(st.session_state.tasks)
        
        # Interactive Grid Widget
        edited_df = st.data_editor(
            df,
            column_config={
                "id": None, # Hide ugly IDs
                "subtasks": None, # Hide complex subtask data
                "completed": st.column_config.CheckboxColumn("Done?", width="small"),
                "text": st.column_config.TextColumn("Task Title", width="large", required=True),
                "category": st.column_config.TextColumn("Category (Folder)", width="medium"),
                "priority": st.column_config.SelectboxColumn("Priority", options=["P1 (High)", "P2 (Medium)", "P3 (Low)"], width="medium")
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic", # ALLOWS ADDING/DELETING ROWS IN BULK
            key="bulk_editor"
        )
        
        if st.button("💾 Apply Bulk Changes", type="primary"):
            new_tasks = []
            for _, row in edited_df.iterrows():
                # Skip if task text is totally empty
                if pd.isna(row.get('text')) or str(row.get('text')).strip() == "":
                    continue
                    
                t_id = row.get('id') if pd.notna(row.get('id')) and row.get('id') else str(uuid.uuid4())
                subs = row.get('subtasks') if isinstance(row.get('subtasks'), list) else []

                new_tasks.append({
                    "id": str(t_id),
                    "text": str(row['text']).strip(),
                    "category": str(row['category']).strip() if pd.notna(row['category']) else "General",
                    "priority": str(row['priority']) if pd.notna(row['priority']) else "P3 (Low)",
                    "completed": bool(row.get('completed', False)),
                    "subtasks": subs
                })
            
            st.session_state.tasks = new_tasks
            st.success("Grid saved successfully! 🎉")
            time.sleep(0.5)
            st.rerun()
