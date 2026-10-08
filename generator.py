import random
import string
from datetime import datetime

# Sample pools for preset generators
FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Riley", "Casey", "Jesse", 
               "Jamie", "Cameron", "Dakota", "Reese", "Quinn", "Avery", "Rowan", "Skyler", "Logan", "Peyton"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", 
              "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore"]
DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "company.org", "test.net"]

POSITIVE_FEEDBACK = [
    "Great service, very satisfied!",
    "Everything worked smoothly and without issues.",
    "Excellent customer support and friendly staff.",
    "Highly recommended. Will definitely come back.",
    "Very intuitive and easy to use.",
    "Exceeded my expectations in every aspect."
]

NEUTRAL_FEEDBACK = [
    "It was okay, met basic expectations.",
    "Average experience, nothing special.",
    "Acceptable quality for the price.",
    "Standard procedure, no complaints."
]

NEGATIVE_FEEDBACK = [
    "Could be improved in several areas.",
    "Experienced slight delay during the process.",
    "User interface could be more modern.",
    "Needs more detailed documentation."
]

ALL_FEEDBACK = POSITIVE_FEEDBACK + NEUTRAL_FEEDBACK + NEGATIVE_FEEDBACK

def generate_mock_value(generator_type: str) -> str:
    """Generates synthetic test data for text fields."""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    
    if generator_type == "name":
        return f"{first} {last}"
    elif generator_type == "first_name":
        return first
    elif generator_type == "last_name":
        return last
    elif generator_type == "email":
        num = random.randint(10, 999)
        domain = random.choice(DOMAINS)
        return f"{first.lower()}.{last.lower()}{num}@{domain}"
    elif generator_type == "phone":
        return f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    elif generator_type == "number":
        return str(random.randint(1, 100))
    elif generator_type == "rating_10":
        return str(random.randint(1, 10))
    elif generator_type == "positive_feedback":
        return random.choice(POSITIVE_FEEDBACK)
    elif generator_type == "feedback":
        return random.choice(ALL_FEEDBACK)
    elif generator_type == "date":
        year = random.randint(2023, 2026)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year:04d}-{month:02d}-{day:02d}"
    else:
        return f"Test Answer {random.randint(100, 999)}"

def pick_question_value(q_config: dict):
    """
    Given a question configuration, selects or generates an answer based on weights and mode.
    Returns: string value, list of string values (for checkboxes), or None if left blank.
    """
    q_type = q_config.get("type", "text")
    options = q_config.get("options", [])

    if q_type in ["radio", "dropdown", "scale"]:
        if not options:
            return ""
        weights_dict = q_config.get("weights", {})
        # Extract weights in order of options
        weights = [float(weights_dict.get(opt, 10)) for opt in options]
        
        # Check if all weights are zero
        if sum(weights) == 0:
            if q_config.get("is_required", False):
                return random.choice(options)
            return None
        
        chosen = random.choices(options, weights=weights, k=1)[0]
        return chosen

    elif q_type == "checkbox":
        if not options:
            return []
        weights_dict = q_config.get("weights", {})
        selected = []
        for opt in options:
            w = float(weights_dict.get(opt, 50))
            if random.uniform(0, 100) <= w:
                selected.append(opt)
        
        # If required and nothing was selected, pick at least one weighted option
        if not selected and q_config.get("is_required", False):
            weights = [max(float(weights_dict.get(opt, 10)), 0.01) for opt in options]
            selected = [random.choices(options, weights=weights, k=1)[0]]
        return selected

    else:
        # Text, paragraph, or other
        mode = q_config.get("text_mode", "fixed")
        if mode == "blank":
            return "" if q_config.get("is_required", False) else None
        elif mode == "fixed":
            return q_config.get("fixed_value", "")
        elif mode == "custom_list":
            raw_list = q_config.get("custom_list", [])
            if isinstance(raw_list, str):
                items = [line.strip() for line in raw_list.splitlines() if line.strip()]
            else:
                items = [str(x).strip() for x in raw_list if str(x).strip()]
            if items:
                return random.choice(items)
            return ""
        elif mode == "preset_generator":
            gen_type = q_config.get("preset_generator", "name")
            return generate_mock_value(gen_type)
        else:
            return q_config.get("fixed_value", "")

def build_submission_payload(questions_config: list, page_history: str = "0"):
    """
    Constructs the exact POST data dictionary for a single submission.
    """
    payload = {}
    for q in questions_config:
        entry_id = q.get("entry_id")
        if not entry_id:
            continue
        val = pick_question_value(q)
        if val is not None:
            # val can be a string or list of strings
            payload[entry_id] = val

    if page_history:
        payload["pageHistory"] = page_history

    return payload
