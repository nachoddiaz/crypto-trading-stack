FROM node:20-alpine as builder

WORKDIR /app

# Instalar dependencias
COPY package.json ./
RUN npm install

# Copiar código y construir
COPY . .
RUN npm run build

# Etapa de producción con Nginx
FROM nginx:alpine

# Copiar configuración de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copiar archivos construidos
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
