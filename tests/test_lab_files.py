import netmodel


def test_frr_daemons_enables_ospf():
    text = (netmodel.ROOT / "docker" / "frr" / "daemons").read_text(encoding="utf-8")
    assert "zebra=yes" in text
    assert "ospfd=yes" in text