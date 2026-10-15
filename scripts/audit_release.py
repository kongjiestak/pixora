"""Basic publication scan; prints locations only, never secret values."""
import re
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATTERNS=[rb"(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}",rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}",rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",rb"(?:/Users/|/home/)[A-Za-z0-9._-]+/"]
def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT)
def main():
    patterns=[re.compile(p) for p in PATTERNS];values=[];failures=[]
    if (ROOT/'.env').exists():
        for line in (ROOT/'.env').read_text().splitlines():
            if '=' in line:
                key,value=line.split('=',1)
                if key.endswith('_TOKEN') and len(value.strip())>=32:values.append(value.strip().encode())
    def check(oid,path):
        data=git('cat-file','blob',oid)
        if Path(path).name in {'.env','auth.json'} or path.endswith(('.sqlite','.log','.key','.pem')) or any(p.search(data) for p in patterns) or any(v in data for v in values):failures.append(path or oid[:12])
    count=0
    for entry in git('ls-files','--stage','-z').decode().split('\0'):
        if entry:
            header,path=entry.split('\t',1);check(header.split()[1],path);count+=1
    history=0
    for entry in git('rev-list','--objects','--all').decode().splitlines():
        oid,_,path=entry.partition(' ')
        if git('cat-file','-t',oid).strip()==b'blob':check(oid,path);history+=1
    if failures:raise SystemExit('Publication scan failed (values suppressed): '+', '.join(failures))
    emails=set(git('log','--all','--format=%ae%n%ce').decode().splitlines())
    personal=[e for e in emails if e and not (e.endswith('@users.noreply.github.com') or e=='noreply@github.com')]
    if personal:print('REVIEW: historical commit metadata includes non-noreply email(s); obtain owner approval or stop publication. Values suppressed.')
    print(f'PASS: {count} staged files, {history} historical blobs; no tested content secret patterns. Metadata review is separate.')
if __name__=='__main__':main()
