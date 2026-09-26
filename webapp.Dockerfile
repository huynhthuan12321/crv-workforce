FROM node:20-alpine as builder

WORKDIR /app

COPY webapp/package*.json ./
RUN npm ci

COPY webapp/ ./
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/nginx.webapp.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
