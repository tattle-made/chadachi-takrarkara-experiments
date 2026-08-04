from dotenv import load_dotenv
load_dotenv()

from guardrails import Guard
from guardrails.hub import LLMCritic

guard = Guard().use(
    LLMCritic(
        metrics={
            "informative": {"description": "Is the response informative?", "threshold": 2},
        },
        max_score=3,
        llm_callable="gpt-4o-mini",
        on_fail="exception",
    )
)

test_text = "The sky is blue because of Rayleigh scattering of sunlight."

try:
    result = guard.validate(test_text)
    print("Passed:", result.validated_output)
except Exception as e:
    print("Failed:", e)