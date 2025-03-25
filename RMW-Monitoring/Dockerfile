FROM alpine:latest

# Install necessary tools
RUN apk add --no-cache docker-cli curl

# Copy all monitoring configuration files
COPY . /app/monitoring

# Set working directory
WORKDIR /app/monitoring

# Make sure we can execute the deploy script
RUN chmod +x /app/monitoring/deploy.sh || echo "No deploy.sh script present"

# The container doesn't need to run as a daemon, it will be used to deploy the stack
CMD ["sh", "-c", "echo 'RMW-Monitoring container - use for deploying monitoring stack'"] 