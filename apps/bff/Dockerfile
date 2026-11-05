ARG NODE_IMAGE=m.daocloud.io/docker.io/library/node:24.11.0-alpine
FROM ${NODE_IMAGE} AS test
WORKDIR /workspace
ARG NPM_REGISTRY=https://registry.npmmirror.com
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/bff/package.json apps/bff/package.json
RUN npm ci --registry=${NPM_REGISTRY}
COPY apps/bff apps/bff
COPY apps/web apps/web
RUN npm test && npm run build
FROM ${NODE_IMAGE} AS runtime
WORKDIR /workspace
ENV NODE_ENV=production
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/bff/package.json apps/bff/package.json
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm ci --omit=dev --registry=${NPM_REGISTRY}
COPY --from=test /workspace/apps/bff/src apps/bff/src
USER node
EXPOSE 8081
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s CMD node -e "fetch('http://127.0.0.1:8081/readyz').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
CMD ["node","apps/bff/src/server.js"]
