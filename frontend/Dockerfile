FROM nginx:1.27

# Copy pre-built frontend (run `npm install && npm run build` locally first)
COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Generate self-signed TLS certificate
RUN mkdir -p /etc/nginx/ssl \
 && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/selfsigned.key \
    -out  /etc/nginx/ssl/selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=FaceID/CN=face-id"

EXPOSE 80 443
