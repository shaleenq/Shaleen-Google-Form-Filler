import json
import re
import requests

sample_html = """
<!DOCTYPE html>
<html>
<head><title>Customer Feedback Survey</title></head>
<body>
<script type="text/javascript">
var FB_PUBLIC_LOAD_DATA_ = [null, [
    "Customer Feedback Survey",
    [
        [101, "Overall Satisfaction", "How satisfied are you?", 2, [
            [111111111, [["Very Satisfied"], ["Satisfied"], ["Neutral"], ["Dissatisfied"]], 1]
        ]],
        [102, "Which features do you use?", "Select all that apply", 4, [
            [222222222, [["Dashboard"], ["Reports"], ["Automation"], ["Export"]], 0]
        ]],
        [103, "Your Department", "Choose your department", 3, [
            [333333333, [["Engineering"], ["Marketing"], ["Sales"], ["Support"]], 1]
        ]],
        [104, "Any additional comments?", "Let us know your feedback", 1, [
            [444444444, null, 0]
        ]],
        [105, "Full Name", "", 0, [
            [555555555, null, 1]
        ]]
    ],
    [null, null]
], null, "Customer Feedback Survey"];
</script>
</body>
</html>
"""

from test_parser import parse_google_form

res = parse_google_form(sample_html)
print("Title:", res["title"])
print("Page count:", res["page_count"])
print("Page history:", res["page_history"])
print(f"Parsed {len(res['questions'])} questions:")
for q in res["questions"]:
    print(f" - {q['entry_id']} ({q['type']}): {q['title']} | Options: {q['options']} | Req: {q['is_required']}")
