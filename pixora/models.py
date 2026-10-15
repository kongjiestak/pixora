from datetime import datetime, timezone, timedelta
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator, AliasChoices

def now():
    return datetime.now(timezone.utc)

class Window(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=80)
    used_percent: float = Field(ge=0, le=100)
    duration_minutes: int | None = Field(default=None, gt=0)
    resets_at: datetime | None = None

    @model_validator(mode="after")
    def timezone_check(self):
        if self.resets_at and self.resets_at.tzinfo is None:
            raise ValueError("resets_at requires timezone")
        return self

class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    provider: Literal["codex", "chatgpt"]
    source: Literal["codex-app-server", "unavailable", "demo"]
    mode: Literal["real", "demo"]
    status: Literal["ok", "unavailable", "error"]
    observed_at: datetime = Field(validation_alias=AliasChoices("observed_at", "collected_at"))
    windows: list[Window] = Field(default_factory=list, max_length=32)
    reason_code: Literal["quota_unavailable", "codex_read_failed", "demo_fixed", "chatgpt_unavailable", "awaiting_collector"] | None = None
    reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def consistency(self):
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at requires timezone")
        if self.observed_at > now() + timedelta(seconds=60):
            raise ValueError("observation is in the future")
        if (self.mode == "demo") != (self.source == "demo"):
            raise ValueError("demo source and mode must agree")
        if self.status != "ok" and self.windows:
            raise ValueError("unavailable/error must not claim quota")
        if self.status == "ok" and not self.windows:
            raise ValueError("ok requires windows")
        if self.provider == "chatgpt" and self.mode == "real" and (self.status == "ok" or self.source != "unavailable"):
            raise ValueError("ChatGPT real quota not implemented")
        if self.mode == "real" and self.provider == "codex" and self.source not in ("codex-app-server", "unavailable"):
            raise ValueError("invalid Codex source")
        return self
