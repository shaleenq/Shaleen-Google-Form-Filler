from generator import build_submission_payload, generate_mock_value

sample_config = [
    {
        "entry_id": "entry.111",
        "title": "Satisfaction",
        "type": "radio",
        "is_required": True,
        "options": ["A", "B", "C"],
        "weights": {"A": 80, "B": 20, "C": 0}
    },
    {
        "entry_id": "entry.222",
        "title": "Features",
        "type": "checkbox",
        "is_required": False,
        "options": ["X", "Y", "Z"],
        "weights": {"X": 100, "Y": 0, "Z": 50}
    },
    {
        "entry_id": "entry.333",
        "title": "Name",
        "type": "text",
        "is_required": True,
        "text_mode": "preset_generator",
        "preset_generator": "name"
    },
    {
        "entry_id": "entry.444",
        "title": "Email",
        "type": "text",
        "is_required": True,
        "text_mode": "preset_generator",
        "preset_generator": "email"
    },
    {
        "entry_id": "entry.555",
        "title": "Custom City",
        "type": "text",
        "is_required": False,
        "text_mode": "custom_list",
        "custom_list": "Tokyo\nNew York\nLondon\nParis"
    }
]

for i in range(5):
    payload = build_submission_payload(sample_config, page_history="0,1")
    print(f"Sample {i+1}:", payload)
