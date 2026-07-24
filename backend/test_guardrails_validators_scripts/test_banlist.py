from guardrails import Guard
from guardrails.hub import BanList

guard = Guard().use(BanList(banned_words=["confidential", "secret"], on_fail="exception"))

test_text = "This project has a confidential roadmap."

try:
    result = guard.validate(test_text)
    print("Passed:", result.validated_output)
except Exception as e:
    print("Failed as expected:", e)