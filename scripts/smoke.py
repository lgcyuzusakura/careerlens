"""Exercise the real four-service HTTP chain with synthetic data only."""
import json
import os
import urllib.error
import urllib.request
import uuid
import urllib.parse


BASE = os.getenv("WEB_BASE_URL", "http://localhost:3000")
BODY = {"resumeText": "项目经历\n使用 Java 和 Spring Boot 实现合成课程管理 API，并编写单元测试。", "jdText": "必须掌握 Java、Spring Boot；Docker 经验优先。", "options": {"useExternalModel": False}}
TOKEN = ''
ADMIN_TOKEN = ''

for line in open('.env',encoding='utf-8'):
    if '=' in line and not line.lstrip().startswith('#'):
        name,value=line.strip().split('=',1)
        if name in {'ADMIN_USERNAME','ADMIN_PASSWORD'}:
            os.environ.setdefault(name,value.strip("'\""))


def call(path, body=None, status=200, base=BASE):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + TOKEN} if TOKEN and ':8082' not in base else {})}
    request = urllib.request.Request(base + path, data=data, headers=headers)
    try:
        response = urllib.request.urlopen(request, timeout=50)
    except urllib.error.HTTPError as error:
        response = error
    assert response.status == status, (path, response.status, response.read().decode())
    trace = response.headers.get("X-Trace-Id")
    result = json.loads(response.read())
    assert set(result) == {"code", "msg", "data"}
    assert trace and len(trace) == 36
    return result, trace


def main():
    global TOKEN
    legacy=os.getenv('LEGACY_SMOKE')=='true'
    if not legacy:
        call('/api/v1/account',status=401)
        session,_=call('/api/v1/auth/register',{'username':'smoke_'+uuid.uuid4().hex[:20],'password':'synthetic-smoke-password'})
        TOKEN=session['data']['token']
        call('/api/v1/admin/users',status=403)
        order,_=call('/api/v1/recharges',{'amountCents':1000,'idempotencyKey':str(uuid.uuid4())})
        for _ in range(2): call('/api/v1/recharges/'+order['data']['id']+'/simulate-confirm',{})
        account,_=call('/api/v1/account');assert account['data']['user']['credits']==110
        boundary='careerlens-smoke-'+uuid.uuid4().hex
        form=b'--'+boundary.encode()+b'\r\nContent-Disposition: form-data; name="target"\r\n\r\nresume\r\n--'+boundary.encode()+b'\r\nContent-Disposition: form-data; name="file"; filename="synthetic.txt"\r\nContent-Type: text/plain\r\n\r\nSynthetic Java Spring Boot resume with enough text.\r\n--'+boundary.encode()+b'--\r\n'
        upload=urllib.request.Request(BASE+'/api/v1/documents/text',data=form,headers={'Authorization':'Bearer '+TOKEN,'Content-Type':'multipart/form-data; boundary='+boundary})
        parsed=urllib.request.urlopen(upload,timeout=15);document=json.loads(parsed.read());assert document['data']['format']=='txt' and 'Synthetic Java' in document['data']['text']
        admin,_=call('/api/v1/auth/login',{'username':os.getenv('ADMIN_USERNAME','admin'),'password':os.environ['ADMIN_PASSWORD']})
        ADMIN_TOKEN=admin['data']['token'];user_token=TOKEN;TOKEN=ADMIN_TOKEN
        overview,_=call('/api/v1/admin/overview');assert overview['data']['users']>=2 and overview['data']['simulatedRevenueCents']>=1000
        orders,_=call('/api/v1/admin/recharges');assert any(item['id']==order['data']['id'] for item in orders['data']['items'])
        TOKEN=user_token
    templates, _ = call("/api/v1/job-templates")
    assert len(templates["data"]["items"]) >= 2
    result, trace = call("/api/v1/analyses", BODY)
    data = result["data"]
    assert data["score"] == {"value": 86, "matchedWeight": 6, "totalWeight": 7, "reason": "WEIGHTED_SKILL_COVERAGE"}, data["score"]
    assert {item["skillId"] for item in data["matches"]} == {"java", "spring-boot"}
    assert {item["skillId"] for item in data["gaps"]} == {"docker"}
    assert data["mode"] == "rules"
    for port, path, payload in [(8081,"/api/v1/analyses",BODY),(8080,"/api/v1/matches",BODY),(8082,"/internal/v1/extractions",{**BODY,"contractVersion":"analysis-v1","skillDictionaryVersion":"skills-v1"})]:
        direct, _ = call(path,payload,base=f"http://localhost:{port}")
        assert direct["code"] == "OK"
    call("/api/v1/analyses", {**BODY, "resumeText": " "}, 400)
    call("/api/v1/analyses", {**BODY, "unknown": True}, 400)
    call("/api/v1/analyses", {**BODY, "resumeText": "a" * 170000}, 413)
    unicode_result, _ = call("/api/v1/analyses", {**BODY, "resumeText": "😀" * 15000 + " Java"})
    assert len(unicode_result["data"]["evidence"][0]["text"]) == 15005
    no_requirements, _ = call("/api/v1/analyses", {**BODY, "jdText": "请积极主动，拥有良好的沟通能力和团队合作精神。"})
    assert no_requirements["data"]["score"]["value"] is None
    result, _ = call("/api/v1/analyses", {**BODY, "options": {"useExternalModel": True}})
    expected = os.getenv("EXPECTED_EXTERNAL_MODE", "llm" if os.getenv("OPENAI_API_KEY") else "degraded")
    assert result["data"]["mode"] == expected, result["data"]["mode"]
    if not legacy:
        account,_=call('/api/v1/account');assert account['data']['user']['credits']==104
        assert len(account['data']['recharges'])==1
        assert len(account['data']['analyses'])==6
    print(f"PASS four-service HTTP smoke; auth/quota/recharge={not legacy}; 86/100, gaps, direct REST, 400, null score, external={expected}; traceId={trace}")


if __name__ == "__main__":
    main()
