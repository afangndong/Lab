from pathlib import Path
import generate

def test_render_all_paths(data, tmp_path):
    files = generate.render_all(data, root=tmp_path)
    names = {p.relative_to(tmp_path).as_posix() for p in files}
    assert names == {"docker-compose.yml", "ansible/inventory.yml",
                     "terraform/lab.auto.tfvars.json"}

def test_deterministic(data, tmp_path):
    assert generate.render_all(data, root=tmp_path) == generate.render_all(data, root=tmp_path)

def test_compose_has_all_nodes(data, tmp_path):
    text = next(t for p, t in generate.render_all(data, root=tmp_path).items()
                if p.name == "docker-compose.yml")
    for name in ("br01", "pc01", "srv-lager", "srv02"):  # Namen aus deinem lab ggf. anpassen
        assert name in text

def test_header_present(data, tmp_path):
    for t in generate.render_all(data, root=tmp_path).values():
        if not t.lstrip().startswith("{"):   # JSON hat keinen Header
            assert t.startswith(generate.HEADER)

def test_stale_detection(data, tmp_path):
    files = generate.render_all(data, root=tmp_path)
    for p, t in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")
    first = next(iter(files))
    first.write_text("manipuliert", encoding="utf-8")
    stale = [p for p, t in files.items() if p.read_text(encoding="utf-8") != t]
    assert stale == [first]