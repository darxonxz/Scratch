import streamlit as st
import pdfplumber
import re
import uuid
import pandas as pd
import time
import io

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="TaskFlow Pro", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stProgress > div > div > div > div { background-image: linear-gradient(to right, #4facfe, #00f2fe); }
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] {
        background-color: #161B22; border-radius: 10px; padding: 12px; border: 1px solid #30363D;
    }
    .badge-p1 { background-color: #FF4D4D; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p2 { background-color: #FFA500; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .badge-p3 { background-color: #38EF7D; color: black; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; }
    .cat-badge { background-color: #21262D; color: #8B949E; border: 1px solid #30363D; padding: 2px 8px; border-radius: 6px; font-size: 0.75rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. SESSION STATE & SANITIZATION ---
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# Helper to safely clear data editor memory when external tasks are added
def clear_editor_state():
    if "spreadsheet_editor" in st.session_state:
        del st.session_state["spreadsheet_editor"]

# Ensure schema integrity
for task in st.session_state.tasks:
    task.setdefault('id', str(uuid.uuid4()))
    task.setdefault('text', 'Untitled Task')
    task.setdefault('category', 'General')
    task.setdefault('priority', 'P3 (Low)')
    task.setdefault('completed', False)
    task.setdefault('subtasks', [])

# --- 3. PARSER UTILITIES ---
def parse_text_to_tasks(text):
    if not text or not text.strip():
        return
    lines = text.split('\n')
    current_cat = "Imported"
    new_tasks = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        is_bullet = re.match(r'^(?:[-*•]|\d+[\.\)])\s', line)
        is_keyword = re.match(r'^(?:task|to do|todo|action|item)[\s:]', line, re.IGNORECASE)
        
        if is_bullet or is_keyword:
            clean_text = re.sub(r'^(?:[-*•]|\d+[\.\)])\s*', '', line)
            clean_text = re.sub(r'^(?:task|to do|todo|action|item)[\s:]*', '', clean_text, flags=re.IGNORECASE).strip()
            
            if not clean_text:
                continue
                
            low_text = clean_text.lower()
            if any(w in low_text for w in ['urgent', 'asap', 'today', 'critical', 'high', 'p1']):
                prio = "P1 (High)"
            elif any(w in low_text for w in ['medium', 'important', 'soon', 'p2']):
                prio = "P2 (Medium)"
            else:
                prio = "P3 (Low)"
                
            new_tasks.append({
                "id": str(uuid.uuid4()),
                "text": clean_text,
                "category": current_cat,
                "priority": prio,
                "completed": False,
                "subtasks": []
            })
        elif 2 < len(line) < 40 and not line.endswith('.'):
            current_cat = line.strip().strip(':')
                
    if new_tasks:
        st.session_state.tasks.extend(new_tasks)
        clear_editor_state()

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
    st.header("💾 Backup & Export")
    if st.session_state.tasks:
        # Create a clean export DataFrame without complex nested dicts
        export_records = []
        for t in st.session_state.tasks:
            export_records.append({
                "Task Title": t.get("text", ""),
                "Category": t.get("category", "General"),
                "Priority": t.get("priority", "P3 (Low)"),
                "Status": "Done" if t.get("completed") else "Pending"
            })
        df_export = pd.DataFrame(export_records)
        csv_bytes = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Tasks (CSV)",
            data=csv_bytes,
            file_name="my_tasks.csv",
            mime="text/csv",
            key="export_csv_btn"
        )

# --- 5. HEADER & METRICS ---
st.title("⚡ TaskFlow Pro")

if st.session_state.tasks:
    total_count = len(st.session_state.tasks)
    done_count = sum(1 for t in st.session_state.tasks if t.get('completed', False))
    progress_val = done_count / total_count if total_count > 0 else 0.0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Tasks", total_count)
    m2.metric("Completed Tasks", done_count)
    m3.metric("Completion Rate", f"{int(progress_val * 100)}%")
    
    st.progress(progress_val)
    if progress_val == 1.0:
        st.snow()

st.divider()

# --- 6. INPUT HUB (WRAPPED IN FORMS FOR RELIABILITY) ---
with st.expander("➕ Import / Add Tasks", expanded=not bool(st.session_state.tasks)):
    input_tab1, input_tab2, input_tab3 = st.tabs(["Quick Add", "📄 Upload PDF", "📋 Paste Notes"])
    
    # --- QUICK ADD FORM ---
    with input_tab1:
        with st.form("quick_add_form", clear_on_submit=True):
            col_qa1, col_qa2, col_qa3 = st.columns([3, 2, 2])
            with col_qa1:
                q_title = st.text_input("Task Title", placeholder="Enter task name...")
            with col_qa2:
                q_cat = st.text_input("Category", placeholder="Project / Area")
            with col_qa3:
                q_prio = st.selectbox("Priority", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], index=2)
            
            q_subs = st.text_input("Subtasks (comma-separated)", placeholder="Subtask 1, Subtask 2")
            submit_qa = st.form_submit_button("Add Task 🚀")
            
            if submit_qa:
                if q_title.strip():
                    sub_list = [{"text": s.strip(), "completed": False} for s in q_subs.split(',') if s.strip()]
                    st.session_state.tasks.append({
                        "id": str(uuid.uuid4()),
                        "text": q_title.strip(),
                        "category": q_cat.strip() if q_cat.strip() else "General",
                        "priority": q_prio,
                        "completed": False,
                        "subtasks": sub_list
                    })
                    clear_editor_state()
                    st.toast("Task added successfully! 🎯")
                    st.rerun()
                else:
                    st.warning("Please enter a task title.")

    # --- PDF UPLOADER ---
    with input_tab2:
        uploaded_pdf = st.file_uploader("Drop your PDF here 📥", type="pdf", key="pdf_uploader_input")
        if st.button("Extract PDF Tasks 🚀", key="btn_extract_pdf") and uploaded_pdf:
            try:
                pdf_bytes = uploaded_pdf.getvalue() # Safe byte retrieval
                pdf_text = ""
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    for page in pdf.pages:
                        extracted = page.extract_text()
                        if extracted:
                            pdf_text += extracted + "\n"
                
                if pdf_text.strip():
                    parse_text_to_tasks(pdf_text)
                    st.toast("PDF Tasks Extracted! 🎉")
                    st.rerun()
                else:
                    st.warning("No readable text found in PDF.")
            except Exception as e:
                st.error(f"Error reading PDF: {e}")

    # --- PASTE NOTES FORM ---
    with input_tab3:
        with st.form("paste_notes_form"):
            pasted_text = st.text_area("Paste text or bullet points here:", height=150)
            submit_paste = st.form_submit_button("Extract Pasted Tasks 🚀")
            
            if submit_paste:
                if pasted_text.strip():
                    parse_text_to_tasks(pasted_text)
                    st.toast("Notes Extracted! 🎉")
                    st.rerun()
                else:
                    st.warning("Please paste some text first.")

# --- 7. WORKSPACE MODES ---
if st.session_state.tasks:
    checklist_mode, organizer_mode = st.tabs(["🎯 Focus Checklist Mode", "🛠️ Bulk Organizer Mode"])

    # --- CHECKLIST MODE ---
    with checklist_mode:
        f_col1, f_col2, f_col3, f_col4 = st.columns([3, 2, 2, 1])
        with f_col1:
            search_str = st.text_input("🔍 Search", placeholder="Filter by keyword...", key="search_input").lower()
        with f_col2:
            cats_available = list(set(t.get('category', 'General') for t in st.session_state.tasks))
            sel_cats = st.multiselect("Category Slicer", cats_available, default=cats_available, key="cat_slicer")
        with f_col3:
            sel_prios = st.multiselect("Priority Slicer", ["P1 (High)", "P2 (Medium)", "P3 (Low)"], default=["P1 (High)", "P2 (Medium)", "P3 (Low)"], key="prio_slicer")
        with f_col4:
            st.write("")
            st.write("")
            if st.button("🗑️ Clear All", key="btn_clear_all"):
                st.session_state.tasks = []
                clear_editor_state()
                st.rerun()

        filtered_tasks = [
            t for t in st.session_state.tasks
            if (search_str in t.get('text', '').lower() or search_str in t.get('category', '').lower())
            and t.get('category', 'General') in sel_cats
            and t.get('priority', 'P3 (Low)') in sel_prios
        ]
        
        active_items = [t for t in filtered_tasks if not t.get('completed', False)]
        done_items = [t for t in filtered_tasks if t.get('completed', False)]

        st.subheader(f"🎯 To-Do ({len(active_items)})")
        for t in active_items:
            prio = t.get('priority', 'P3 (Low)')
            p_class = "badge-p1" if "P1" in prio else ("badge-p2" if "P2" in prio else "badge-p3")
            
            c_chk, c_text, c_edit = st.columns([0.05, 0.85, 0.1])
            with c_chk:
                if st.checkbox("", value=False, key=f"chk_{t['id']}"):
                    t['completed'] = True
                    clear_editor_state()
                    st.toast("Task completed! 🔨")
                    st.rerun()
            with c_text:
                st.markdown(
                    f"**{t.get('text', '')}** <span class='{p_class}'>{prio}</span> <span class='cat-badge'>📁 {t.get('category', 'General')}</span>",
                    unsafe_allow_html=True
                )
                if t.get('subtasks'):
                    sub_done = sum(1 for s in t['subtasks'] if s.get('completed', False))
                    with st.expander(f"Subtasks ({sub_done}/{len(t['subtasks'])})"):
                        for idx, sub in enumerate(t['subtasks']):
                            sub_chk = st.checkbox(sub['text'], value=sub.get('completed', False), key=f"sub_{t['id']}_{idx}")
                            sub['completed'] = sub_chk

            with c_edit:
                with st.popover("✏️"):
                    st.caption("Quick Edit")
                    edit_txt = st.text_input("Task Title", t.get('text', ''), key=f"et_{t['id']}")
                    edit_cat = st.text_input("Category", t.get('category', ''), key=f"ec_{t['id']}")
                    prio_options = ["P1 (High)", "P2 (Medium)", "P3 (Low)"]
                    current_prio_idx = prio_options.index(prio) if prio in prio_options else 2
                    edit_prio = st.selectbox("Priority", prio_options, index=current_prio_idx, key=f"ep_{t['id']}")
                    
                    if st.button("Save", key=f"eb_{t['id']}"):
                        t['text'] = edit_txt
                        t['category'] = edit_cat
                        t['priority'] = edit_prio
                        clear_editor_state()
                        st.rerun()

        if done_items:
            st.markdown("---")
            st.subheader(f"✅ Completed ({len(done_items)})")
            for t in done_items:
                c_chk, c_text = st.columns([0.05, 0.95])
                with c_chk:
                    if not st.checkbox("", value=True, key=f"chk_done_{t['id']}"):
                        t['completed'] = False
                        clear_editor_state()
                        st.rerun()
                with c_text:
                    st.markdown(
                        f"~~{t.get('text', '')}~~ <span class='cat-badge'>📁 {t.get('category', 'General')}</span>",
                        unsafe_allow_html=True
                    )

    # --- SPREADSHEET BULK ORGANIZER MODE ---
    with organizer_mode:
        st.info("💡 **Bulk Edit Mode:** Double-click any cell to edit titles, categories, or priorities across all rows at once.")
        
        df_editor = pd.DataFrame(st.session_state.tasks)
        
        edited_grid = st.data_editor(
            df_editor,
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
        
        if st.button("💾 Apply Bulk Changes", type="primary", key="btn_apply_bulk"):
            updated_task_list = []
            for _, row in edited_grid.iterrows():
                if pd.isna(row.get('text')) or str(row.get('text')).strip() == "":
                    continue
                    
                row_id = row.get('id') if pd.notna(row.get('id')) and row.get('id') else str(uuid.uuid4())
                subs = row.get('subtasks') if isinstance(row.get('subtasks'), list) else []

                updated_task_list.append({
                    "id": str(row_id),
                    "text": str(row['text']).strip(),
                    "category": str(row['category']).strip() if pd.notna(row['category']) else "General",
                    "priority": str(row['priority']) if pd.notna(row['priority']) else "P3 (Low)",
                    "completed": bool(row.get('completed', False)),
                    "subtasks": subs
                })
            
            st.session_state.tasks = updated_task_list
            st.success("Changes saved successfully! 🎉")
            time.sleep(0.3)
            st.rerun()
