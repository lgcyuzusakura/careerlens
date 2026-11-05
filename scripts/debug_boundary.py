"""Print only statuses and codes for synthetic Unicode boundary diagnostics."""
import json
import urllib.error
import urllib.request

body = {"resumeText": "😀" * 15000 + " Java", "jdText": "必须掌握 Java、Spring Boot；Docker 经验优先。", "options": {"useExternalModel": False}}
for port, path in [(8082, "/internal/v1/extractions"), (8080, "/api/v1/matches"), (8081, "/api/v1/analyses"), (3000, "/api/v1/analyses")]:
    payload = dict(body)
    if port == 8082:
        payload.update(contractVersion="analysis-v1", skillDictionaryVersion="skills-v1")
    request = urllib.request.Request(f"http://localhost:{port}{path}", data=json.dumps(payload, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(request, timeout=25)
    except urllib.error.HTTPError as error:
        response = error
    result = json.loads(response.read())
    print(port, response.status, result.get("code"), len(json.dumps(result, ensure_ascii=False).encode()))
