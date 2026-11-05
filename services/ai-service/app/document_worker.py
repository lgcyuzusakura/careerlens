"""One disposable parser process per upload; no files or model credentials needed."""
import json
import sys

if sys.platform != "win32":
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (4, 4))

from .documents import DocumentInput, extract_document

if __name__ == "__main__":
    try:
        result = extract_document(DocumentInput.model_validate_json(sys.stdin.buffer.read(2850001)))
        sys.stdout.write(json.dumps(result, ensure_ascii=True))
    except Exception:
        sys.exit(1)
