ARG NODE_IMAGE=m.daocloud.io/docker.io/library/node:24.11.0-alpine
ARG NGINX_IMAGE=m.daocloud.io/docker.io/library/nginx:1.28.0-alpine
FROM ${NODE_IMAGE} AS build
WORKDIR /workspace
ARG NPM_REGISTRY=https://registry.npmmirror.com
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/bff/package.json apps/bff/package.json
RUN npm ci --registry=${NPM_REGISTRY}
COPY apps/web apps/web
RUN npm run build
FROM ${NGINX_IMAGE} AS runtime
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /workspace/apps/web/dist /usr/share/nginx/html
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid
USER nginx
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s CMD wget -q -O /dev/null http://127.0.0.1:3000/healthz || exit 1
