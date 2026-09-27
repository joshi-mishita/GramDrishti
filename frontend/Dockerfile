# GramDrishti web image (S14): build the app with Node, serve it with nginx (non-root, port 8080).
# Build context: the repository root (the build copies contract/examples into public/mock).
# VITE_SNAPSHOT=1 builds the offline variant, which reads /snapshot/ (a volume) and never calls the API.
FROM node:22-alpine AS build
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY contract /src/contract
COPY frontend ./
ARG VITE_REAL_ENDPOINTS=health,meta,geo,forecast,observed,explain,risk,priority,advisories,audio,farmers,feedback,verification,impact,data-quality
ARG VITE_SNAPSHOT=
ARG VITE_DEFAULT_ISSUE_DATE=
ENV VITE_REAL_ENDPOINTS=$VITE_REAL_ENDPOINTS \
    VITE_SNAPSHOT=$VITE_SNAPSHOT \
    VITE_DEFAULT_ISSUE_DATE=$VITE_DEFAULT_ISSUE_DATE
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.29-alpine
# API_UPSTREAM is read by the image's envsubst step at start (templates/*.template).
ENV API_UPSTREAM=http://api:8000
COPY frontend/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY frontend/nginx/errors /usr/share/nginx/errors
COPY --from=build /src/frontend/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
