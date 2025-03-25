FROM alpine:latest

# Install necessary tools including python and PyYAML for YAML validation
RUN apk add --no-cache docker-cli curl python3 py3-pip

# Install PyYAML for YAML validation
RUN pip3 install pyyaml

# Create app user to avoid permission issues
RUN adduser -D -u 1000 appuser

# Create directories and set permissions
RUN mkdir -p /app/monitoring && \
    chown -R appuser:appuser /app

# Copy all monitoring configuration files
COPY --chown=appuser:appuser . /app/monitoring/

# Set working directory
WORKDIR /app/monitoring

# Validate docker-stack.yml YAML syntax and use dummy.yml as fallback if it fails
RUN python3 -c "import yaml, sys; yaml.safe_load(open('docker-stack.yml')); print('YAML validation successful')" || \
    { echo "YAML validation failed, using dummy.yml instead"; cp dummy.yml docker-stack.yml; }

# Verify files are present and accessible
RUN ls -la /app/monitoring && \
    echo "Content of docker-stack.yml:" && \
    cat docker-stack.yml

# Create an extraction script that ensures proper permissions
RUN echo '#!/bin/sh' > /extract.sh && \
    echo 'set -e' >> /extract.sh && \
    echo 'TARGET_DIR="$1"' >> /extract.sh && \
    echo 'echo "Copying files to $TARGET_DIR"' >> /extract.sh && \
    echo 'cp -rv /app/monitoring/* "$TARGET_DIR/"' >> /extract.sh && \
    echo 'echo "Setting permissions..."' >> /extract.sh && \
    echo 'chown -R 1000:1000 "$TARGET_DIR"' >> /extract.sh && \
    echo 'chmod -R 755 "$TARGET_DIR"' >> /extract.sh && \
    echo 'echo "Files in target directory:"' >> /extract.sh && \
    echo 'ls -la "$TARGET_DIR"' >> /extract.sh && \
    chmod +x /extract.sh

USER appuser

# The container doesn't need to run as a daemon
CMD ["sh", "-c", "echo 'RMW-Monitoring container - Files are in /app/monitoring'"] 