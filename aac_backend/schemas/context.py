from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class CommandContext:
    actor_id: str | None
    project_id: str | None
    roles: tuple[str, ...] = field(default_factory=tuple)
    request_id: str = field(default_factory=lambda: f"REQ_{uuid4().hex}")
    correlation_id: str = field(default_factory=lambda: f"CORR_{uuid4().hex}")
    causation_id: str | None = None
    idempotency_key: str | None = None

    @property
    def role_at_time(self) -> str:
        return ",".join(sorted(self.roles)) if self.roles else "system"
