from dataclasses import dataclass


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    title: str
    severity: str
    execution_modes: tuple[str, ...]
    blocking_contexts: tuple[str, ...]


RULE_ROWS = (
    ("AAC-RULE-RULE-001", "Referenced artefact exists", "critical", ("import", "immediate", "baseline", "release_gate"), ("import", "baseline", "release_gate")),
    ("AAC-RULE-RULE-002", "Relationship type allowed", "critical", ("import", "immediate", "baseline", "release_gate"), ("import", "baseline", "release_gate")),
    ("AAC-RULE-RULE-003", "Unique artefact ID", "critical", ("import", "immediate"), ("import",)),
    ("AAC-RULE-RULE-004", "Required metadata present", "critical", ("import", "baseline", "release_gate"), ("import", "baseline", "release_gate")),
    ("AAC-RULE-RULE-005", "Profile mandatory artefact present", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-006", "Tailoring decision complete", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-010", "ASIL safety requirement allocated", "critical", ("immediate", "baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-011", "Requirement decomposition traced", "major", ("baseline", "release_gate"), ()),
    ("AAC-RULE-RULE-012", "Requirement has verification intent", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-013", "Released requirement has verification evidence", "critical", ("release_gate",), ("release_gate",)),
    ("AAC-RULE-RULE-014", "Safety requirement traces to safety source", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-020", "Component classification defined", "critical", ("import", "baseline"), ("import", "baseline")),
    ("AAC-RULE-RULE-021", "Software architecture covers requirements", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-022", "Interface contract exists for component interaction", "critical", ("immediate", "baseline"), ("baseline",)),
    ("AAC-RULE-RULE-023", "Interface source and destination valid", "critical", ("import", "immediate"), ("import",)),
    ("AAC-RULE-RULE-024", "Interface payload semantics defined", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-025", "QM-to-ASIL interface has failure behavior", "critical", ("immediate", "baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-026", "Timing-relevant interface has timing verification", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-027", "ASIL-relevant interface has AG contract", "critical", ("immediate", "baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-030", "Assumption covered by safeguard or test", "critical", ("immediate", "baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-031", "Guarantee mapped to requirement or safeguard", "major", ("baseline",), ()),
    ("AAC-RULE-RULE-032", "Safeguard allocated to ASIL component", "critical", ("immediate", "baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-033", "Released safeguard has implementation", "critical", ("release_gate",), ("release_gate",)),
    ("AAC-RULE-RULE-034", "Released safeguard has verification", "critical", ("release_gate",), ("release_gate",)),
    ("AAC-RULE-RULE-040", "Software unit traces to design and requirement", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-041", "Implementation item references valid source", "major", ("baseline",), ()),
    ("AAC-RULE-RULE-042", "Build configuration identified", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-043", "Static analysis evidence present or tailored", "major", ("release_gate",), ()),
    ("AAC-RULE-RULE-044", "Coding guideline compliance evidence present or tailored", "major", ("release_gate",), ()),
    ("AAC-RULE-RULE-050", "Test specification traces to test basis", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-051", "Test case has expected result and pass criteria", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-052", "Test procedure references environment", "major", ("baseline",), ()),
    ("AAC-RULE-RULE-053", "Test result references valid test case/spec", "critical", ("immediate", "baseline"), ("baseline",)),
    ("AAC-RULE-RULE-054", "Failed test result linked to defect or waiver", "critical", ("release_gate",), ("release_gate",)),
    ("AAC-RULE-RULE-055", "Requirements coverage exists", "critical", ("release_gate",), ("release_gate",)),
    ("AAC-RULE-RULE-060", "Change has impact analysis", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-061", "Defect resolution traced", "major", ("release_gate",), ()),
    ("AAC-RULE-RULE-062", "Configuration items baselined", "critical", ("baseline",), ("baseline",)),
    ("AAC-RULE-RULE-063", "Confirmation measure evidence exists", "major", ("release_gate",), ()),
    ("AAC-RULE-RULE-070", "Cybersecurity relevant item has CS evidence", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-071", "Software update relevant item has SUMS evidence", "critical", ("release_gate",), ("release_gate",)),
    ("AAC-RULE-RULE-080", "Released upstream change creates suspect state", "major", ("immediate",), ()),
    ("AAC-RULE-RULE-081", "Suspect artefact not releasable", "critical", ("release_gate",), ("release_gate",)),
    ("AAC-RULE-RULE-090", "Baseline contains no critical issues", "critical", ("baseline", "release_gate"), ("baseline", "release_gate")),
    ("AAC-RULE-RULE-091", "Release gate fails on critical issues", "critical", ("release_gate",), ("release_gate",)),
)

RULE_CATALOG: dict[str, RuleDefinition] = {
    rule_id: RuleDefinition(
        rule_id=rule_id,
        title=title,
        severity=severity,
        execution_modes=execution_modes,
        blocking_contexts=blocking_contexts,
    )
    for rule_id, title, severity, execution_modes, blocking_contexts in RULE_ROWS
}
