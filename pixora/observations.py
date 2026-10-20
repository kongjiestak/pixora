"""Versioned metric observations; scopes remain explicit provider capabilities."""
from datetime import datetime, timedelta, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from urllib.parse import urlsplit
from pixora.models import now

class Metric(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    key: str = Field(min_length=1, max_length=80)
    value: float | None = None
    unit: str = Field(default='', max_length=24)

class Entry(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1,max_length=240)
    detail: str = Field(default='',max_length=240)
    url: str | None = Field(default=None,max_length=2048)
    @field_validator('url')
    @classmethod
    def safe_url(cls,value):
        if value is None:return value
        parsed=urlsplit(value)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or any(ord(c)<33 for c in value):
            raise ValueError('entry link requires credential-free HTTPS')
        return value

class Observation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[2] = 2
    provider: Literal['codex','chatgpt','system','github','rss','tasks']
    connector_id: str = Field(min_length=1, max_length=64, pattern=r'^[a-z0-9][a-z0-9._-]*$')
    entity_id: str = Field(default='default', min_length=1, max_length=64, pattern=r'^[a-z0-9][a-z0-9._-]*$')
    category: Literal['ai','system','developer','personal','automation']
    source: str = Field(min_length=1, max_length=80)
    mode: Literal['real','demo']
    status: Literal['ok','unavailable','error']
    collected_at: datetime
    expires_at: datetime
    sensitivity: Literal['private','public'] = 'private'
    metrics: list[Metric] = Field(default_factory=list, max_length=32)

    entries: list[Entry] = Field(default_factory=list,max_length=10)

    @model_validator(mode='after')
    def consistent(self):
        if self.collected_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError('timestamps require timezone')
        self.collected_at=self.collected_at.astimezone(timezone.utc)
        self.expires_at=self.expires_at.astimezone(timezone.utc)
        if self.collected_at > now()+timedelta(seconds=60):
            raise ValueError('collection in future')
        if not self.collected_at < self.expires_at <= self.collected_at+timedelta(days=30):
            raise ValueError('expiry must follow collection, at most 30 days')
        if (self.mode=='demo') != (self.source=='demo'):
            raise ValueError('demo mode/source must agree')
        if any(m.value is not None and m.unit in ('percent','percent-used') and not 0<=m.value<=100 for m in self.metrics):
            raise ValueError('percentage outside 0..100')
        if self.status=='ok' and not any(m.value is not None for m in self.metrics):
            raise ValueError('ok requires a known metric')
        if self.status!='ok' and (self.metrics or self.entries):
            raise ValueError('failed observations cannot claim metrics')
        if len({m.key for m in self.metrics})!=len(self.metrics):
            raise ValueError('duplicate metric key')
        if self.provider=='chatgpt' and self.mode=='real' and self.status=='ok':
            raise ValueError('real ChatGPT quota unavailable')
        return self

def from_snapshot(snapshot):
    return Observation(provider=snapshot.provider,connector_id='quota-v1',category='ai',
        source=snapshot.source,mode=snapshot.mode,status=snapshot.status,
        collected_at=snapshot.observed_at,expires_at=snapshot.observed_at+timedelta(seconds=600),
        metrics=[Metric(key=w.name,value=w.used_percent,unit='percent-used') for w in snapshot.windows])
