import re
import json

def parse_google_form(html_text: str):
    """
    Extracts form title, pageHistory, and questions with options from Google Form HTML.
    """
    # Attempt to locate FB_PUBLIC_LOAD_DATA_
    match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(.+?);\s*(?:</script>|\n)', html_text, re.DOTALL)
    if not match:
        match = re.search(r'var\s+FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.+?\]);', html_text, re.DOTALL)
    if not match:
        # Try finding raw array starting after FB_PUBLIC_LOAD_DATA_
        idx = html_text.find("FB_PUBLIC_LOAD_DATA_")
        if idx != -1:
            eq_idx = html_text.find("=", idx)
            semi_idx = html_text.find(";</script>", eq_idx)
            if eq_idx != -1 and semi_idx != -1:
                raw_str = html_text[eq_idx+1:semi_idx].strip()
                try:
                    raw_data = json.loads(raw_str)
                    return _process_raw_data(raw_data)
                except Exception:
                    pass
        raise ValueError("Could not find FB_PUBLIC_LOAD_DATA_ in the provided Google Form HTML.")

    raw_str = match.group(1).strip()
    try:
        raw_data = json.loads(raw_str)
    except Exception as e:
        # Clean up any trailing semicolon or whitespace
        cleaned = re.sub(r';\s*$', '', raw_str)
        raw_data = json.loads(cleaned)

    return _process_raw_data(raw_data)

def _process_raw_data(raw_data):
    # Form metadata
    # raw_data[1][8] is often form title, raw_data[1][0] or raw_data[3]
    form_title = "Google Form"
    try:
        if len(raw_data) > 1 and raw_data[1]:
            if len(raw_data[1]) > 8 and raw_data[1][8]:
                form_title = str(raw_data[1][8])
            elif len(raw_data[1]) > 0 and raw_data[1][0]:
                form_title = str(raw_data[1][0])
        elif len(raw_data) > 3 and raw_data[3]:
            form_title = str(raw_data[3])
    except Exception:
        pass

    # Page count & pageHistory
    page_count = 1
    try:
        if len(raw_data) > 1 and raw_data[1] and len(raw_data[1]) > 2 and raw_data[1][2]:
            page_count = len(raw_data[1][2]) or 1
    except Exception:
        page_count = 1
    page_history = ",".join(str(i) for i in range(page_count))

    # Questions parsing
    questions = []
    try:
        items = raw_data[1][1] if (len(raw_data) > 1 and raw_data[1] and len(raw_data[1]) > 1) else []
        for item in items:
            if not item or len(item) < 5 or not item[4]:
                continue
            
            q_title = item[1] if len(item) > 1 and item[1] else "Untitled Question"
            q_desc = item[2] if len(item) > 2 and item[2] else ""
            q_type_id = item[3] if len(item) > 3 and item[3] is not None else 0

            # item[4] can have one or more sub-entries
            for sub in item[4]:
                if not sub or len(sub) == 0:
                    continue
                entry_id = str(sub[0])
                options = []
                if len(sub) > 1 and sub[1]:
                    for opt in sub[1]:
                        if opt and len(opt) > 0 and opt[0] is not None:
                            options.append(str(opt[0]))
                
                is_required = bool(sub[2]) if len(sub) > 2 else False
                
                # Determine type label
                # 0: Short text, 1: Paragraph, 2: Multiple choice (Radio), 3: Dropdown, 4: Checkboxes, 5: Linear scale
                type_label = "text"
                if options:
                    if q_type_id == 4:
                        type_label = "checkbox"
                    elif q_type_id == 3:
                        type_label = "dropdown"
                    elif q_type_id == 5:
                        type_label = "scale"
                    else:
                        type_label = "radio"
                else:
                    if q_type_id == 1:
                        type_label = "paragraph"
                    else:
                        type_label = "text"

                questions.append({
                    "entry_id": f"entry.{entry_id}",
                    "raw_entry_id": entry_id,
                    "title": q_title,
                    "description": q_desc,
                    "type": type_label,
                    "type_id": q_type_id,
                    "is_required": is_required,
                    "options": options
                })
    except Exception as e:
        print(f"Error parsing questions: {e}")

    return {
        "title": form_title,
        "page_count": page_count,
        "page_history": page_history,
        "questions": questions
    }

if __name__ == "__main__":
    print("Testing parser logic syntax check OK")
