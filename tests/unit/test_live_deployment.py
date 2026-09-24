from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]


def test_live_compose_has_private_api_and_persistent_media():
    config = yaml.safe_load((ROOT / "docker-compose.live.yml").read_text(encoding="utf-8"))

    api = config["services"]["api"]
    assert api["ports"] == ["127.0.0.1:8000:8000"]
    assert api["restart"] == "unless-stopped"
    assert {
        "autotube_data:/app/data",
        "autotube_uploads:/app/uploads",
        "autotube_generations:/app/generations",
    }.issubset(set(api["volumes"]))

    tunnel = config["services"]["tunnel"]
    assert tunnel["env_file"] == [".env.live"]
    assert tunnel["command"] == "tunnel --no-autoupdate run"


def test_dockerfile_runs_one_api_worker():
    dockerfile = (ROOT / "Dockerfile.api").read_text(encoding="utf-8")
    assert dockerfile.startswith("FROM python:3.12-slim")
    assert '"--workers", "1"' in dockerfile
