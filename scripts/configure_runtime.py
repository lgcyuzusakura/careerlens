"""Generate ignored local runtime credentials; optionally import the selected Codex provider without printing secrets."""
import argparse
import json
import os
import secrets
import tomllib
from pathlib import Path

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--codex",action="store_true")
args=parser.parse_args()
target=root/".env"
values={}
if target.exists():
    for line in target.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            name,value=line.split("=",1);values[name]=value.strip("'\"")
values.setdefault("JWT_SECRET",secrets.token_urlsafe(48))
values.setdefault("ADMIN_USERNAME","admin")
values.setdefault("ADMIN_PASSWORD",secrets.token_urlsafe(18))
values.setdefault("DATABASE_PASSWORD",secrets.token_urlsafe(24))
values.setdefault("RELEASE_TAG","v0.2-dev")
if args.codex:
    home=Path(os.environ.get("CODEX_HOME",Path.home()/".codex"))
    config=tomllib.loads((home/"config.toml").read_text(encoding="utf-8"))
    provider=config.get("model_providers",{}).get(config.get("model_provider"),{})
    auth=json.loads((home/"auth.json").read_text(encoding="utf-8")) if (home/"auth.json").exists() else {}
    key=os.getenv(provider.get("env_key","OPENAI_API_KEY"),"") or provider.get("experimental_bearer_token","") or auth.get("OPENAI_API_KEY","")
    base=provider.get("base_url","")
    if not key or not base or not config.get("model"):
        raise SystemExit("Selected Codex provider lacks a usable base URL, model or API key; no secret was printed")
    values.update(OPENAI_API_KEY=key,OPENAI_BASE_URL=base,OPENAI_MODEL=config["model"],OPENAI_API_STYLE=provider.get("wire_api","responses"))
for name,value in values.items():
    if any(char in value for char in "\r\n'"):
        raise SystemExit("Unsupported runtime value encoding; no secret was printed")
target.write_text("\n".join(f"{name}='{value}'" for name,value in values.items())+"\n",encoding="utf-8")
print("Configured ignored .env runtime credentials" + (" and selected Codex provider" if args.codex else "") + "; secret values were not printed")
