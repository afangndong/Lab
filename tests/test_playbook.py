import subprocess

import netmodel


def test_playbook_syntax():
    r = subprocess.run(
        ["ansible-playbook", "-i", "ansible/inventory.yml", "ansible/site.yml", "--syntax-check"],
        cwd=netmodel.ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr