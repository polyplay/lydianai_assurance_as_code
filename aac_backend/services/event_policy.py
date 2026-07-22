BLOCKING_RELEVANT_PREFIXES = (
    "artefact.",
    "relationship.",
    "validation.",
    "suspect.",
    "tailoring.",
    "profile.",
    "schema.",
    "standards.",
    "evidence.",
    "test_result.",
    "import.completed",
    "project.assurance_configuration_",
)

NON_BLOCKING_EVENT_TYPES = {
    "validation.issue_suppressed",
    "suspect.cleared",
}


def is_blocking_relevant_event_type(event_type: str) -> bool:
    if event_type in NON_BLOCKING_EVENT_TYPES:
        return False
    return event_type.startswith(BLOCKING_RELEVANT_PREFIXES)
