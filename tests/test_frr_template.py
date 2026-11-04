import jinja2
import yaml

import netmodel

TEMPLATE = netmodel.ROOT / "ansible" / "templates" / "frr.conf.j2"
INVENTORY = netmodel.ROOT / "ansible" / "inventory.yml"


def _render(name):
    inv = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    host = inv["all"]["children"]["routers"]["hosts"][name]
    env = jinja2.Environment(
        undefined=jinja2.StrictUndefined, trim_blocks=True, keep_trailing_newline=True
    )
    return env.from_string(TEMPLATE.read_text(encoding="utf-8")).render(
        inventory_hostname=name, **host
    )


def test_br01_config():
    text = _render("br01")
    assert "hostname br01" in text
    assert "ospf router-id 10.255.0.2" in text
    assert " network 10.0.1.0/24 area 0" in text
    assert " network 10.10.1.0/24 area 0" in text


def test_core1_has_all_backbones():
    text = _render("core1")
    for n in (1, 2, 3, 4):
        assert f" network 10.0.{n}.0/24 area 0" in text