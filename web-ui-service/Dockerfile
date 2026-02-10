FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

RUN mkdir -p /var/cache/nginx /var/run /run \
	&& chown -R nginx:nginx /var/cache/nginx /var/run /run /etc/nginx /usr/share/nginx/html \
	&& touch /var/run/nginx.pid \
	&& chown nginx:nginx /var/run/nginx.pid

USER nginx

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
	CMD wget -q -O - http://127.0.0.1:8080/health | grep -q ok || exit 1

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

