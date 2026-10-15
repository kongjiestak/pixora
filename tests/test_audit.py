"""Regression checks for author/committer metadata, without real identities."""
import subprocess
import sys
from pathlib import Path
import pytest

@pytest.mark.parametrize("email,expected",[("sample@example.invalid",1),("12345+test@users.noreply.github.com",0)])
def test_publication_scan_checks_commit_metadata(tmp_path,email,expected):
    root=tmp_path/'repo';root.mkdir()
    subprocess.run(['git','init','-q',str(root)],check=True)
    (root/'scripts').mkdir()
    source=Path(__file__).resolve().parents[1]/'scripts/audit_release.py'
    (root/'scripts/audit_release.py').write_bytes(source.read_bytes())
    (root/'README.md').write_text('test fixture')
    subprocess.run(['git','add','.'],cwd=root,check=True)
    subprocess.run(['git','-c','user.name=Test','-c','user.email='+email,'commit','-qm','fixture'],cwd=root,check=True)
    r=subprocess.run([sys.executable,'scripts/audit_release.py'],cwd=root,capture_output=True,text=True)
    assert r.returncode==expected
    assert email not in r.stdout+r.stderr
