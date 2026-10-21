"""Administrator-published display profiles and restrictive device data policies.

No device-facing write API. A policy can only narrow the token's original scope.
"""
import json
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field
from pixora.models import now

Provider = Literal['codex','chatgpt','system','github','rss','tasks','weather']
Identifier = Annotated[str, Field(min_length=1, max_length=80)]
Names = Annotated[list[Identifier], Field(max_length=64)]

class Profile(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    show_clock: bool = True
    show_weather: bool = True
    density: Literal['comfortable','compact'] = 'comfortable'
    focus_window: Literal['primary','weekly'] = 'primary'
    theme: Literal['orbit','paper','amoled','aurora'] = 'orbit'
    accent: Literal['mint','blue','amber','violet'] = 'mint'
    text_size: Literal['standard','large'] = 'standard'
    appearance: Literal['theme','light','dark','auto'] = 'theme'

class Rule(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    connectors: Names | None = None
    entities: Names | None = None
    metrics: Names | None = None
    windows: Names | None = None
    entries: Literal['full','titles','none'] = 'full'

class Policy(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    # None preserves legacy scope; {} permits no providers.
    rules: dict[Provider, Rule] | None = None
    public_only: bool = False

def initialize_profiles(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS device_profiles(
        device_id TEXT PRIMARY KEY, profile TEXT NOT NULL, policy TEXT NOT NULL,
        revision INTEGER NOT NULL, updated_at TEXT NOT NULL)''')

def read_profile(conn, device_id):
    row=conn.execute('SELECT profile,policy,revision,updated_at FROM device_profiles WHERE device_id=?',(device_id,)).fetchone()
    if row is None:return Profile(),Policy(),0,None
    return Profile.model_validate_json(row[0]),Policy.model_validate_json(row[1]),row[2],row[3]

def configure(conn,device_id,profile=None,policy=None):
    if not conn.in_transaction:conn.execute('BEGIN IMMEDIATE')
    row=conn.execute('SELECT providers FROM devices WHERE id=? AND revoked=0',(device_id,)).fetchone()
    if row is None:raise ValueError('unknown or revoked device')
    old_profile,old_policy,revision,_=read_profile(conn,device_id)
    new_profile=Profile.model_validate(profile) if profile is not None else old_profile
    new_policy=Policy.model_validate(policy) if policy is not None else old_policy
    if new_policy.rules is not None and not set(new_policy.rules)<=set(json.loads(row[0])):
        raise ValueError('policy cannot add providers outside the original token scope')
    updated=now().isoformat()
    conn.execute('INSERT OR REPLACE INTO device_profiles VALUES (?,?,?,?,?)',
        (device_id,new_profile.model_dump_json(),new_policy.model_dump_json(),revision+1,updated))
    return {'revision':revision+1,'updated_at':updated,'profile':new_profile.model_dump(),'policy':new_policy.model_dump()}

def allowed_providers(providers,policy):
    return [p for p in providers if policy.rules is None or p in policy.rules]

def rule_for(provider,policy):
    return Rule() if policy.rules is None else policy.rules.get(provider)

def permitted_stream(provider,connector,entity,policy):
    rule=rule_for(provider,policy)
    return rule is not None and (rule.connectors is None or connector in rule.connectors) and (rule.entities is None or entity in rule.entities)

def filter_observation(item,policy):
    provider=item['provider'];rule=rule_for(provider,policy)
    if not permitted_stream(provider,item['connector_id'],item['entity_id'],policy):return None
    if policy.public_only and item.get('sensitivity','private')!='public':return None
    item=dict(item)
    item['metrics']=[m for m in item['metrics'] if (rule.metrics is None or m['key'] in rule.metrics) and (provider not in ('codex','chatgpt') or rule.windows is None or m['key'] in rule.windows)]
    if rule.entries=='none':item['entries']=[]
    elif rule.entries=='titles':item['entries']=[{'title':e['title']} for e in item.get('entries',[])]
    return item

def filter_snapshot(item,policy):
    provider=item['provider'];rule=rule_for(provider,policy)
    # V1 quota snapshots have no public classification and map to one v2 stream.
    if policy.public_only or not permitted_stream(provider,'quota-v1','default',policy):return None
    item=dict(item)
    item['windows']=[w for w in item['windows'] if (rule.windows is None or w['name'] in rule.windows) and (rule.metrics is None or w['name'] in rule.metrics)]
    if policy.rules is not None:item['reason']=None
    return item
