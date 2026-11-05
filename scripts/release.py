"""Keep a healthy four-image snapshot, or deploy/roll back that exact local snapshot."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = {"web": "web", "bff": "bff", "domain-api": "java", "ai-service": "ai"}


def run(*args, capture=False):
    return subprocess.run(args, cwd=ROOT, check=True, text=True, capture_output=capture).stdout


def dictionary_hash():
    return hashlib.sha256((ROOT / "config/skills.v1.json").read_bytes()).hexdigest()


def snapshot(name):
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,79}", name):
        raise ValueError("Use a lowercase release name, at most 80 characters")
    destination = ROOT / "output/releases" / f"{name}.json"
    if destination.exists():
        raise ValueError("Snapshot already exists; choose a new name")
    images = {}
    for service, short in SERVICES.items():
        container = run("docker", "compose", "ps", "-q", service, capture=True).strip()
        if not container:
            raise ValueError(f"Service is not running: {service}")
        info = json.loads(run("docker", "inspect", container, capture=True))[0]
        if info["State"].get("Health", {}).get("Status") != "healthy":
            raise ValueError(f"Service is not healthy: {service}")
        image_id = info["Image"]
        tag = f"careerlens-{short}:keep-{name}"
        run("docker", "tag", image_id, tag)
        images[service] = {"tag": tag, "imageId": image_id}
    run(sys.executable, "scripts/smoke.py")
    record = {"schemaVersion": 1, "name": name, "gitSha": run("git", "rev-parse", "HEAD", capture=True).strip(),
              "workingTreeDirty": bool(run("git", "status", "--porcelain", capture=True).strip()),
              "contractVersion": "analysis-v1", "dictionarySha256": dictionary_hash(), "images": images}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Saved healthy snapshot: {destination}")


def deploy(path):
    record = json.loads(path.read_text(encoding="utf-8"))
    if record["schemaVersion"] != 1 or record["contractVersion"] != "analysis-v1" or record["dictionarySha256"] != dictionary_hash() or set(record["images"]) != set(SERVICES):
        raise ValueError("Snapshot contract/dictionary does not match this checkout")
    override = {"services": {}}
    for service, item in record["images"].items():
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", item["imageId"]):
            raise ValueError("Invalid image identity")
        run("docker", "image", "inspect", item["imageId"], capture=True)
        override["services"][service] = {"image": item["imageId"], "pull_policy": "never"}
    target = ROOT / "output/releases/compose-release.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(override), encoding="utf-8")
    run("docker", "compose", "-f", "compose.yaml", "-f", str(target), "up", "-d", "--no-build", "--force-recreate", "--wait", "--wait-timeout", "120")
    run(sys.executable, "scripts/smoke.py")
    print(f"Deployed and verified all four images from {record['name']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--snapshot", metavar="NAME")
    action.add_argument("--deploy", type=Path, metavar="MANIFEST")
    args = parser.parse_args()
    if args.snapshot:
        snapshot(args.snapshot)
    else:
        deploy(args.deploy)
