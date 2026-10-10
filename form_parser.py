import re
import json
import requests
from urllib.parse import urlparse, urlunparse

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def extract_page_question_mapping(raw_data):
    """
    Extracts which questions belong to which page from raw_data[1][2].
    Returns a list of lists, where each inner list contains entry_ids for that page.
    """
    page_question_map = []
    try:
        if len(raw_data) > 1 and raw_data[1] and len(raw_data[1]) > 2 and raw_data[1][2]:
            pages = raw_data[1][2]
            for page in pages:
                if page and len(page) > 0:
                    question_ids = []
                    for q_item in page:
                        if q_item and len(q_item) > 0 and q_item[0] is not None:
                            question_ids.append(str(q_item[0]))
                    page_question_map.append(question_ids)
                else:
                    page_question_map.append([])
    except Exception:
        pass
    return page_question_map


def normalize_urls(raw_url: str):
    """
    Normalizes a Google Form URL into a view_url (for fetching HTML)
    and a submit_url (for posting responses).
    Handles forms.gle short links by resolving redirects.
    """
    url = raw_url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Follow redirect if it's forms.gle
    if "forms.gle" in url:
        try:
            resp = requests.head(url, allow_redirects=True, timeout=10, headers={"User-Agent": DEFAULT_USER_AGENT})
            url = resp.url
        except Exception:
            try:
                resp = requests.get(url, allow_redirects=True, timeout=10, headers={"User-Agent": DEFAULT_USER_AGENT})
                url = resp.url
            except Exception:
                pass

    # Clean query parameters and anchors
    parsed = urlparse(url)
    clean_path = parsed.path

    # Replace /viewform, /edit, /preview, /formResponse etc.
    # Form endpoints follow: /forms/d/e/{form_id}/viewform or /forms/d/{form_id}/viewform
    base_path = re.sub(r'/(viewform|formResponse|edit|preview|closedform).*$', '', clean_path)

    view_url = urlunparse((parsed.scheme or "https", parsed.netloc, f"{base_path}/viewform", "", "", ""))
    submit_url = urlunparse((parsed.scheme or "https", parsed.netloc, f"{base_path}/formResponse", "", "", ""))

    return view_url, submit_url

def extract_fb_public_load_data(html_text: str):
    """Extracts FB_PUBLIC_LOAD_DATA_ array from raw HTML."""
    # Method 1: Regex with ;</script>
    match = re.search(r'FB_PUBLIC_LOAD_DATA_\s*=\s*(.+?);\s*(?:</script>|\n)', html_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # Method 2: Matching brackets after variable assignment
    idx = html_text.find("FB_PUBLIC_LOAD_DATA_")
    if idx != -1:
        eq_idx = html_text.find("=", idx)
        if eq_idx != -1:
            start_bracket = html_text.find("[", eq_idx)
            if start_bracket != -1:
                # Bracket counting
                count = 0
                in_string = False
                escape = False
                end_idx = -1
                for i in range(start_bracket, len(html_text)):
                    c = html_text[i]
                    if escape:
                        escape = False
                        continue
                    if c == '\\':
                        escape = True
                        continue
                    if c == '"':
                        in_string = not in_string
                        continue
                    if not in_string:
                        if c == '[':
                            count += 1
                        elif c == ']':
                            count -= 1
                            if count == 0:
                                end_idx = i + 1
                                break
                if end_idx != -1:
                    raw_json_str = html_text[start_bracket:end_idx]
                    try:
                        return json.loads(raw_json_str)
                    except Exception:
                        pass

    # Check for login requirement
    if "accounts.google.com/ServiceLogin" in html_text or "Sign in to continue" in html_text:
        raise ValueError("This Google Form requires Google Account sign-in (authentication required). Automated submissions cannot bypass Google Login.")
    
    if "This form is no longer accepting responses" in html_text:
        raise ValueError("This Google Form is closed and is no longer accepting responses.")

    raise ValueError("Could not parse FB_PUBLIC_LOAD_DATA_ from the Google Form HTML. Verify that the URL is public and accessible.")

def fetch_and_parse_form(url: str, custom_user_agent: str = DEFAULT_USER_AGENT):
    """
    Fetches the Google Form HTML and extracts all question metadata and form parameters.
    """
    view_url, submit_url = normalize_urls(url)
    
    headers = {
        "User-Agent": custom_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        response = requests.get(view_url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error while fetching Google Form: {e}")

    raw_data = extract_fb_public_load_data(response.text)
    
    # Form Title
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
    page_question_map = []
    try:
        if len(raw_data) > 1 and raw_data[1] and len(raw_data[1]) > 2 and raw_data[1][2]:
            page_count = len(raw_data[1][2]) or 1
            page_question_map = extract_page_question_mapping(raw_data)
            
            # Fallback: if page_question_map is empty or all pages have no questions,
            # treat as single-page form
            if not page_question_map or all(len(page) == 0 for page in page_question_map):
                page_count = 1
                page_question_map = []
    except Exception:
        page_count = 1
        page_question_map = []
    page_history = ",".join(str(i) for i in range(page_count))

    # Questions parsing
    questions = []
    items = raw_data[1][1] if (len(raw_data) > 1 and raw_data[1] and len(raw_data[1]) > 1) else []
    for item in items:
        if not item or len(item) < 5 or not item[4]:
            continue
        
        q_title = item[1] if len(item) > 1 and item[1] else "Untitled Question"
        q_desc = item[2] if len(item) > 2 and item[2] else ""
        q_type_id = item[3] if len(item) > 3 and item[3] is not None else 0

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
            
            # Sub-title for grid or multi-part questions
            sub_title = q_title
            if len(sub) > 3 and sub[3] and isinstance(sub[3], str) and sub[3] != q_title:
                sub_title = f"{q_title} - {sub[3]}"

            # Determine type label
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

            # Default weights if options exist
            weights = {}
            if options:
                default_w = round(100.0 / len(options), 1)
                for opt in options:
                    weights[opt] = default_w

            questions.append({
                "entry_id": f"entry.{entry_id}",
                "raw_entry_id": entry_id,
                "title": sub_title,
                "description": q_desc,
                "type": type_label,
                "type_id": q_type_id,
                "is_required": is_required,
                "options": options,
                "weights": weights,
                "text_mode": "custom_list" if type_label in ["text", "paragraph"] else "fixed",
                "fixed_value": "Sample Response",
                "custom_list": "Response Option 1\nResponse Option 2\nResponse Option 3",
                "preset_generator": "name"
            })

    return {
        "title": form_title,
        "view_url": view_url,
        "submit_url": submit_url,
        "page_count": page_count,
        "page_history": page_history,
        "page_question_map": page_question_map,
        "questions": questions
    }
