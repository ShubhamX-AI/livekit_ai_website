# -------- BUILD STAGE --------
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./

# Install only needed deps
RUN npm install

# Copy rest of the project
COPY . .

# Build Vite production bundle
RUN npm run build


# -------- NGINX SERVE STAGE --------
FROM nginx:1.25-alpine

# Remove default nginx site config
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled dist to nginx html
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]



# Docker build command
# docker build -t shubhamint/ai_website_frontend:latest .
# Docker run command
# docker run -d -p 3000:80 --name ai_website_frontend shubhamint/ai_website_frontend:latest