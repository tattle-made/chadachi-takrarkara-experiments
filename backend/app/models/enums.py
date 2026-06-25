from enum import Enum


class MessageKind(str, Enum):
    user_query = "user_query"
    llm_response = "llm_response"


class FunctionalityType(str, Enum):
    ask_llm = "ask_llm"
    policy_violation = "policy_violation"
    write_email = "write_email"


class MessageStatus(str, Enum):
    completed = "completed"
    error = "error"
    streaming = "streaming"


class AnnotationTag(str, Enum):
    hallucination = "hallucination"
    personal_information = "personal-information"
    too_verbose = "too-verbose"
    high_priority = "high-priority"
    low_priority = "low-priority"
