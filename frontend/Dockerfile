# ---- Giai đoạn 1: Build React 19 Frontend ----
FROM node:20-alpine AS build

WORKDIR /app

# Cài đặt dependencies
COPY package*.json ./
RUN npm ci

# Copy toàn bộ mã nguồn
COPY . .

# Đặt biến môi trường build thời gian chạy API qua Nginx proxy
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build production bundle
RUN npm run build

# ---- Giai đoạn 2: Serve tĩnh bằng Nginx Alpine ----
FROM nginx:1.27-alpine

# Copy kết quả build từ giai đoạn 1
COPY --from=build /app/dist /usr/share/nginx/html

# Copy file cấu hình Nginx reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
