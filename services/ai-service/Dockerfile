ARG PYTHON_IMAGE=m.daocloud.io/docker.io/library/python:3.11.14-slim-bookworm
FROM ${PYTHON_IMAGE} AS test
WORKDIR /workspace
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY services/ai-service/requirements.lock /workspace/services/ai-service/requirements.lock
RUN pip install --no-cache-dir --index-url ${PIP_INDEX_URL} -r services/ai-service/requirements.lock
COPY config config
COPY services/ai-service services/ai-service
WORKDIR /workspace/services/ai-service
RUN python -m pytest -q
FROM test AS runtime
RUN useradd --uid 10001 --create-home app
USER app
EXPOSE 8082
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8082/readyz',timeout=2)"
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8082","--no-access-log"]
