FROM alpine:latest

# Install necessary tools
RUN apk add --no-cache docker-cli curl

# Create directories
RUN mkdir -p /app/monitoring

# Copy all monitoring configuration files
COPY . /app/monitoring/

# Set working directory
WORKDIR /app/monitoring

# List files for debugging
RUN echo "Files in /app/monitoring:" && \
    ls -la /app/monitoring && \
    echo "Docker stack file:" && \
    cat /app/monitoring/docker-stack.yml

# Make the deploy script executable
RUN chmod +x /app/monitoring/deploy.sh || echo "No deploy.sh script present"

# Add a simple entrypoint script to help with extraction
RUN echo '#!/bin/sh' > /extract.sh && \
    echo 'cp -rv /app/monitoring/* "$1"' >> /extract.sh && \
    echo 'echo "Copied files to $1:"' >> /extract.sh && \
    echo 'ls -la "$1"' >> /extract.sh && \
    chmod +x /extract.sh

# The container doesn't need to run as a daemon, it will be used to deploy the stack
ENTRYPOINT ["/bin/sh"]
CMD ["-c", "echo 'RMW-Monitoring container - Use /extract.sh /your/destination to extract files'"] 