# Build stage
FROM node:18-alpine as build-stage

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy project files
COPY . .

# Build the H5 app
RUN npm run build:h5

# Production stage
FROM nginx:alpine as production-stage

# Copy built assets from build-stage
COPY --from=build-stage /app/dist/build/h5 /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
