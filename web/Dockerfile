FROM node:20-alpine

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy package files
COPY package.json pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install

# Copy app files
COPY . .

# Expose port
EXPOSE 5173

# Start dev server
CMD ["pnpm", "dev", "--host"]
