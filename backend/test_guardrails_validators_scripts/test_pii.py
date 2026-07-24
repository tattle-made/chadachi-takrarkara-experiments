from kaapi_guardrails.core.validators.pii_remover import PIIRemover
from guardrails import Guard

guard = Guard().use(PIIRemover())
# result = guard.validate("My name is Rohan and my PAN is ABCDE1234F")
result = guard.validate("hey there")
print(result.validated_output)
print(result)

# USAGE WITHOUT GUARD
# validator = PIIRemover(entity_types=["IN_PAN", "EMAIL_ADDRESS", "PHONE_NUMBER"])
# res = validator.validate("My name is Rohan and my PAN is ABCDE1234F", {})
# print(res)