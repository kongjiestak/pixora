"""Linux host metrics without hostnames, process lists, credentials or remote calls."""
import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path
from pixora.observations import Observation,Metric
from pixora.models import now
from pixora.settings import setting

def cpu_sample(text):
    values=[int(n) for n in text.splitlines()[0].split()[1:9]]
    return sum(values),values[3]+values[4]

def memory_percent(text):
    values={line.split(':')[0]:int(line.split()[1]) for line in text.splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
    return 100*(1-values['MemAvailable']/values['MemTotal'])

class SystemCollector:
    async def collect(self):
        timestamp=now()
        base=dict(provider='system',connector_id='linux-host',entity_id=setting('SYSTEM_ENTITY','local-host'),category='system',source='linux-proc-statvfs',mode='real',collected_at=timestamp,expires_at=timestamp+timedelta(seconds=600))
        try:
            if not sys.platform.startswith('linux'):raise OSError('Linux required')
            proc=Path('/proc')
            a=cpu_sample((proc/'stat').read_text());await asyncio.sleep(.25)
            b=cpu_sample((proc/'stat').read_text());total=b[0]-a[0]
            cpu=100*(1-(b[1]-a[1])/total) if total>0 else None
            disk=os.statvfs('/')
            metrics=[Metric(key='cpu.used',value=None if cpu is None else max(0,min(100,cpu)),unit='percent'),
                Metric(key='memory.used',value=memory_percent((proc/'meminfo').read_text()),unit='percent'),
                Metric(key='disk.used',value=100*(1-disk.f_bfree/disk.f_blocks) if disk.f_blocks else None,unit='percent')]
            return [Observation(**base,status='ok',metrics=metrics)]
        except (OSError,ValueError,KeyError,IndexError,ZeroDivisionError):
            return [Observation(**base,status='unavailable')]
