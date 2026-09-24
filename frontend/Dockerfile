# UI: static SPA + nginx reverse proxy to the backends and the manager service.
# nginx's envsubst renders /etc/nginx/templates/*.template at container start,
# so the proxy targets and the Hermes key come from the environment, not the image.
FROM nginx:1.27-alpine

COPY index.html /usr/share/nginx/html/
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/
COPY assets/ /usr/share/nginx/html/assets/
COPY fonts/ /usr/share/nginx/html/fonts/
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Only these are substituted; nginx's own $uri/$host etc. are left alone.
ENV NGINX_ENVSUBST_FILTER="^(UI_PORT|NETOPS_AGENT_URL|HERMES_URL|MANAGER_URL)$" \
    UI_PORT=3000 \
    NETOPS_AGENT_URL=http://127.0.0.1:8100 \
    HERMES_URL=http://127.0.0.1:8642 \
    MANAGER_URL=http://127.0.0.1:8200

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD wget -qO /dev/null http://127.0.0.1:${UI_PORT}/ || exit 1
