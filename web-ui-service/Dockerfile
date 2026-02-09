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
	&& chown -R nginx:nginx /var/cache/nginx /var/run /run /etc/nginx /usr/share/nginx/html

USER nginx

EXPOSE 8080

