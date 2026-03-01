FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# Production nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Generate self-signed TLS certificate
RUN apk add --no-cache openssl \
 && mkdir -p /etc/nginx/ssl \
 && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/selfsigned.key \
    -out  /etc/nginx/ssl/selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=FaceID/CN=face-id" \
 && apk del openssl

EXPOSE 80 443
