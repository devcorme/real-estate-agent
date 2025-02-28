# Use Node.js LTS (Long Term Support) as base image
FROM node:20-slim

# Set working directory
WORKDIR /app

# Install system dependencies including PostgreSQL client and Python
RUN apt-get update && apt-get install -y \
    openssl \
    python3 \
    python-is-python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application
COPY . .

# Add environment variables needed for build
ENV OPENAI_API_KEY="dummy-key-for-build" \
    LLM_MODEL="gpt-4o-mini" \
    FIRECRAWL_API_KEY="dummy-key-for-build" \
    DATABASE_URL="postgres://dummy:dummy@localhost:5432/dummy" 

# Build the application
RUN npm run build

# Expose the port the app runs on
EXPOSE 3000

# Start the application
CMD ["npm", "start"] 