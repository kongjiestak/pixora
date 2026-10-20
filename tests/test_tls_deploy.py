"""Exercise the certificate gate without changing the system trust store or live proxy."""
import importlib.util
from pathlib import Path
import subprocess
import pytest

spec = importlib.util.spec_from_file_location('deploy_tls', Path(__file__).parents[1]/'scripts/deploy_tls.py')
tls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tls)

@pytest.fixture
def certificate(tmp_path, monkeypatch):
    cert, key = tmp_path/'cert.pem', tmp_path/'key.pem'
    config = tmp_path/'openssl.cnf'
    config.write_text('[req]\ndistinguished_name=dn\nx509_extensions=extensions\nprompt=no\n[dn]\nCN=display.example\n[extensions]\nsubjectAltName=DNS:display.example\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyEncipherment,keyCertSign\nextendedKeyUsage=serverAuth\n')
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','30','-config',str(config)],check=True,capture_output=True)
    monkeypatch.setenv('SSL_CERT_FILE', str(cert))
    return cert, key

def test_rejects_wrong_hostname_or_key(certificate, tmp_path):
    cert, key = certificate
    assert len(tls.validate_pair(cert,key,'display.example')[0]) == 64
    with pytest.raises(RuntimeError): tls.validate_pair(cert,key,'wrong.example')
    wrong = tmp_path/'wrong.key'
    subprocess.run(['openssl','genrsa','-out',str(wrong),'2048'],check=True,capture_output=True)
    with pytest.raises(RuntimeError): tls.validate_pair(cert,wrong,'display.example')

def test_invalid_certificate_does_not_touch_active_configuration(tmp_path):
    (tmp_path/'tls/incoming').mkdir(parents=True)
    (tmp_path/'https-config').mkdir()
    active = tmp_path/'https-config/Caddyfile'
    active.write_text('original configuration')
    (tmp_path/'tls/incoming/fullchain.pem').write_text('not a certificate')
    (tmp_path/'tls/incoming/key.pem').write_text('not a key')
    with pytest.raises(RuntimeError): tls.deploy(tmp_path,'display.example',2053,'unused')
    assert active.read_text() == 'original configuration'

def test_reload_failure_rolls_back_configuration(certificate, tmp_path, monkeypatch):
    cert, key = certificate
    incoming = tmp_path/'tls/incoming'
    incoming.mkdir(parents=True)
    (incoming/'fullchain.pem').write_bytes(cert.read_bytes())
    (incoming/'key.pem').write_bytes(key.read_bytes())
    (tmp_path/'https-config').mkdir()
    active = tmp_path/'https-config/Caddyfile'
    active.write_text('previous valid configuration')
    (tmp_path/'tls-managed.enabled').touch()
    original = tls.command
    reloads = []
    def run(args, data=None):
        if args[0] != 'docker': return original(args, data)
        if 'reload' in args:
            reloads.append(args)
            if len(reloads) == 1: raise RuntimeError('simulated reload failure')
        return b''
    monkeypatch.setattr(tls,'command',run)
    with pytest.raises(RuntimeError): tls.deploy(tmp_path,'display.example',2053,'test-proxy')
    assert len(reloads) == 2
    assert active.read_text() == 'previous valid configuration'
