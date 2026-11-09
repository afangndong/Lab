import subprocess

import pytest

import netmodel


@pytest.mark.parametrize("playbook", ["site.yml", "backup.yml", "rollback.yml"])
def test_playbook_syntax(playbook):
    r = subprocess.run(
        ["ansible-playbook", "-i", "ansible/inventory.yml", f"ansible/{playbook}", "--syntax-check"],
        cwd=netmodel.ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr