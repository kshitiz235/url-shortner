# Frontend image: a two-stage build.
#   Stage 1 (build): use Node to compile the React app into static files.
#   Stage 2 (serve): copy just those static files into a tiny Nginx image.
# The final image contains NO Node or source code — only the built assets.

# ---- Stage 1: build ----
FROM node:24-slim AS build
WORKDIR /app

# Install deps from the lockfile (reproducible), cached unless lockfile changes.
COPY package*.json ./
RUN npm ci

# The API URL is a BUILD-time value in Vite (baked into the bundle). Passed in
# from docker-compose so the built app knows where the backend lives.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY . .
RUN npm run build

# ---- Stage 2: serve ----
FROM nginx:alpine
# Copy the compiled site from the build stage.
COPY --from=build /app/dist /usr/share/nginx/html
# SPA routing config (see nginx.conf).
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
