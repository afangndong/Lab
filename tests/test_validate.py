import  validate

import pytest
import yaml


@pytest.fixture
def data():
    """Frische Kopie der Standortdaten für jeden Test."""
    with open("data/sites.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)

    
def test_real_data_is_valid(data):
    assert validate.validate(data) == []


def test_duplicate_host_ip(data):
    data["sites"][3]["hosts"].append({"name": "srv02", "ip": "10.10.4.10", "role": "server"})
    errors = validate.validate(data)
    assert any("doppelt" in e and "10.10.4.10" in e for e in errors)


def test_overlapping_subnets(data):
    data["sites"][1]["lan"] = "10.10.1.128/25"
    errors = validate.validate(data)
    assert any("ueberlappt" in e for e in errors)


def test_host_outside_lan(data):
    data["sites"][0]["hosts"][0]["ip"] = "10.10.9.10"
    errors = validate.validate(data)
    assert any("liegt nicht in" in e for e in errors)


def test_reserved_router_address(data):
    data["sites"][0]["hosts"][0]["ip"] = "10.10.1.254"
    errors = validate.validate(data)
    assert any("reserviert" in e for e in errors)


def test_unknown_sla_class(data):
    data["sites"][0]["sla"] = "platin"
    errors = validate.validate(data)
    assert any("SLA-Klasse" in e for e in errors)


def test_duplicate_router_id(data):
    data["sites"][1]["router_id"] = data["sites"][0]["router_id"]
    errors = validate.validate(data)
    assert any("router_id" in e and "doppelt" in e for e in errors)


def test_duplicate_site_id_and_name(data):
    data["sites"][1]["id"] = 1
    data["sites"][2]["name"] = "br01"
    errors = validate.validate(data)
    assert any("id 1 doppelt" in e for e in errors)
    assert any("Name br01 doppelt" in e for e in errors)


def test_bad_role_and_ip_format(data):
    data["sites"][0]["hosts"][0]["role"] = "drucker"
    data["sites"][3]["hosts"][0]["ip"] = "10.10.4.999"
    errors = validate.validate(data)
    assert any("Rolle" in e for e in errors)
    assert any("ungueltige IP" in e for e in errors)


def test_invalid_subnet_string(data):
    data["sites"][0]["backbone"] = "10.0.1.5/24"  # Hostbits gesetzt
    errors = validate.validate(data)
    assert any("ungueltiges Subnetz" in e for e in errors)


def test_empty_file():
    assert validate.validate(None) != []
