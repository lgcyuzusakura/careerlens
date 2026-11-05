# Optional local fallback when an OCI mirror stalls; the Node archive hash is verified against nodejs.org.
FROM m.daocloud.io/docker.io/library/python:3.11.14-slim-bookworm@sha256:65a93d69fa75478d554f4ad27c85c1e69fa184956261b4301ebaf6dbb0a3543d
ARG NODE_ARCHIVE_URL=https://npmmirror.com/mirrors/node/v24.11.0/node-v24.11.0-linux-x64.tar.xz
RUN python -c "import hashlib,urllib.request,tarfile,shutil; p='/tmp/node.tar.xz'; urllib.request.urlretrieve('${NODE_ARCHIVE_URL}',p); assert hashlib.sha256(open(p,'rb').read()).hexdigest() == '46da9a098973ab7ba4fca76945581ecb2eaf468de347173897044382f10e0a0a'; tarfile.open(p).extractall('/tmp/node',filter='data'); shutil.copytree('/tmp/node/node-v24.11.0-linux-x64','/usr/local',symlinks=True,dirs_exist_ok=True); shutil.rmtree('/tmp/node'); __import__('os').remove(p)"
RUN useradd --uid 1000 --create-home node && node --version && npm --version
