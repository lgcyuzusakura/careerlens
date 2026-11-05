"""Validate tracked planning artifacts without application dependencies."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = (
    r"sk-[A-Za-z0-9_-]{16,}",
    r"gh[pousr]_[A-Za-z0-9_]{16,}",
    r"github_pat_[A-Za-z0-9_]{16,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"(?<![A-Za-z0-9-])[0-9A-F]{4}-[0-9A-F]{4}(?![A-Za-z0-9-])",
)


def require(condition: bool, description: str) -> None:
    if not condition:
        raise ValueError(description)


def tracked_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    )
    return [Path(name) for name in result.stdout.decode("utf-8").split("\0") if name]


def check_markdown(path: Path, text: str) -> int:
    marker = ""
    fence_size = 0
    language = ""
    block: list[str] = []
    json_count = 0
    for line in text.splitlines():
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            if (
                fence
                and fence.group(1)[0] == marker
                and len(fence.group(1)) >= fence_size
                and not fence.group(2).strip()
            ):
                if language == "json":
                    json.loads("\n".join(block))
                    json_count += 1
                marker = ""
                block = []
            else:
                block.append(line)
            continue
        if fence:
            marker = fence.group(1)[0]
            fence_size = len(fence.group(1))
            language = fence.group(2).strip()
            continue
        # Conversation links are historical verbatim, including local skill paths.
        if path.name == "AI_LOG.md":
            continue
        for match in re.finditer(r"\]\(([^)]+)\)", line):
            target = match.group(1).strip("<>")
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = unquote(target.split("#", 1)[0])
            resolved = (ROOT / path.parent / target).resolve()
            require(resolved.is_relative_to(ROOT), f"Link leaves repository: {path}")
            require(resolved.exists(), f"Broken relative link in {path}: {target}")
    require(not marker, f"Unclosed Markdown fence: {path}")
    return json_count


def check_postman() -> int:
    path = ROOT / "postman/CareerLens.postman_collection.json"
    collection = json.loads(path.read_text(encoding="utf-8"))
    require(
        collection["info"]["schema"].endswith("/v2.1.0/collection.json"),
        "Unexpected Postman schema version",
    )
    variables = {item["key"]: item["value"] for item in collection["variable"]}
    require(
        variables == {
            "webBaseUrl": "http://localhost:3000",
            "javaBaseUrl": "http://localhost:8080",
            "bffBaseUrl": "http://localhost:8081",
            "pythonBaseUrl": "http://localhost:8082",
        },
        "Postman port variables differ from the agreed contract",
    )
    count = 0
    for group in collection["item"]:
        for item in group["item"]:
            request = item["request"]
            require(request["method"] in {"GET", "POST"}, "Unexpected debug method")
            require(
                any(request["url"].startswith("{{" + key + "}}/") for key in variables),
                "Postman URL must use a documented localhost variable",
            )
            if "body" in request:
                body = json.loads(request["body"]["raw"])
                require(
                    body["options"]["useExternalModel"] is False,
                    "Default Postman requests must not use an external model",
                )
            require(bool(item.get("event")), "Missing Postman response assertion")
            count += 1
    require(count == 10, "Expected ten documented Postman requests")
    return count


def check_ignored_materials(paths: list[Path]) -> None:
    for path in paths:
        require(path.parts[0].lower() not in {"test", "private", "local-data"}, f"Private material tracked: {path}")
        require(path.suffix.lower() not in {".zip", ".pdf", ".pem", ".key", ".p12", ".pfx"}, f"Private file type tracked: {path}")
        require(
            not (path.name == ".env" or path.name.startswith(".env."))
            or path.name == ".env.example",
            f"Environment secret file tracked: {path}",
        )
    for name in ("test/README.md", "test/materials.zip", ".env", "apps/web/.env.local", "private/resume.txt"):
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--quiet", "--", name], cwd=ROOT
        )
        require(result.returncode == 0, f"Expected private path to be ignored: {name}")
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--quiet", "--", ".env.example"], cwd=ROOT
    )
    require(result.returncode == 1, ".env.example must remain committable")


def main() -> None:
    paths = tracked_paths()
    require(bool(paths), "No tracked files; stage documentation before checking")
    check_ignored_materials(paths)
    markdown_count = 0
    json_count = 0
    for path in paths:
        if path.suffix.lower() not in {".md", ".json", ".yml", ".yaml"}:
            continue
        text = (ROOT / path).read_text(encoding="utf-8")
        require("\ufffd" not in text, f"Invalid replacement character: {path}")
        for pattern in SECRET_PATTERNS:
            require(re.search(pattern, text) is None, f"Potential sensitive value in {path}; value hidden")
        if path.suffix.lower() == ".md":
            json_count += check_markdown(path, text)
            markdown_count += 1
        elif path.suffix.lower() == ".json":
            json.loads(text)
    request_count = check_postman()
    print(f"PASS: {markdown_count} Markdown files, {json_count} JSON examples, {request_count} Postman requests")
    print("PASS: tracked-file privacy boundaries and heuristic secret scan")
    print("Planning checks only; no application, Docker, LLM or endpoint execution")


if __name__ == "__main__":
    main()
