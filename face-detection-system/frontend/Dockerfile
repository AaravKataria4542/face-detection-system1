FROM node:18-alpine AS builder

WORKDIR /app

ENV NODE_OPTIONS=--max-old-space-size=2048
ENV CI=false
ENV GENERATE_SOURCEMAP=false

COPY package.json ./
RUN npm install --legacy-peer-deps --no-audit --no-fund && \
    npm install ajv@^8 --legacy-peer-deps --no-audit --no-fund
COPY . .
RUN npm run build

# Production image
FROM nginx:1.27-alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
