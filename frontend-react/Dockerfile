# Dockerfile del frontend — colócalo dentro de frontend-react/
# Etapa 1: compilar la app de React/Vite
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=/backend
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Etapa 2: servir los archivos estáticos compilados con nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
