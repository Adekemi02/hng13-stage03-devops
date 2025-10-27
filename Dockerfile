FROM nginx:alpine

RUN apk add --no-cache gettext

COPY nginx.conf.template /etc/nginx/nginx.conf.template

COPY envsubst.sh /envsubst.sh

RUN chmod +x /envsubst.sh

ENTRYPOINT ["/envsubst.sh"]
