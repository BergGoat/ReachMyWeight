FROM python:3.9-slim

# Installeer afhankelijkheden en de Docker CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    docker.io \
    ca-certificates \
    curl \
    gnupg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installeer Python-afhankelijkheden met specifieke versies
RUN pip install --no-cache-dir fastapi==0.95.1 pydantic==1.10.8 uvicorn httpx

# Maak de monitoring directory
RUN mkdir -p /app/monitoring_files

# Kopieer de redeploy.py naar de container
COPY redeploy.py .

# Voeg een standaard stack bestand toe in geval van extractie mislukt
RUN echo 'version: "3.7"\n\nvolumes:\n  prometheus_data: {}\n  grafana_data: {}\n\nnetworks:\n  monitor-net:\n\nservices:\n  prometheus:\n    image: prom/prometheus:v2.36.2\n    volumes:\n      - ./prometheus/:/etc/prometheus/\n      - prometheus_data:/prometheus\n    command:\n      - "--config.file=/etc/prometheus/prometheus.yml"\n      - "--storage.tsdb.path=/prometheus"\n      - "--web.console.libraries=/usr/share/prometheus/console_libraries"\n      - "--web.console.templates=/usr/share/prometheus/consoles"\n      - "--web.enable-lifecycle"\n      - "--web.enable-admin-api"\n    ports:\n      - 9090:9090\n    networks:\n      - monitor-net\n    deploy:\n      placement:\n        constraints:\n          - node.role==manager\n      restart_policy:\n        condition: on-failure\n\n  node-exporter:\n    image: quay.io/prometheus/node-exporter:latest\n    volumes:\n      - /proc:/host/proc:ro\n      - /sys:/host/sys:ro\n      - /:/rootfs:ro\n    command: \n      - "--path.procfs=/host/proc" \n      - "--path.sysfs=/host/sys"\n      - --collector.filesystem.ignored-mount-points\n      - "^/(sys|proc|dev|host|etc|rootfs/var/lib/docker/containers|rootfs/var/lib/docker/overlay2|rootfs/run/docker/netns|rootfs/var/lib/docker/aufs)($$|/)"\n    ports:\n      - 9100:9100\n    networks:\n      - monitor-net\n    deploy:\n      mode: global\n      restart_policy:\n          condition: on-failure\n\n  cadvisor:\n    image: gcr.io/cadvisor/cadvisor\n    volumes:\n      - /:/rootfs:ro\n      - /var/run:/var/run:rw\n      - /sys:/sys:ro\n      - /var/lib/docker/:/var/lib/docker:ro\n    ports:\n      - 8081:8080\n    networks:\n      - monitor-net\n    deploy:\n      mode: global\n      restart_policy:\n          condition: on-failure\n\n  grafana:\n    image: grafana/grafana\n    depends_on:\n      - prometheus\n    ports:\n      - 3000:3000\n    volumes:\n      - grafana_data:/var/lib/grafana\n      - ./grafana/provisioning/:/etc/grafana/provisioning/\n    networks:\n      - monitor-net\n    user: "472"\n    deploy:\n      placement:\n        constraints:\n          - node.role==manager\n      restart_policy:\n        condition: on-failure' > /app/monitoring_files/docker-stack.yml

# Start de redeploy-service met uvicorn op poort 8080
CMD ["uvicorn", "redeploy:app", "--host", "0.0.0.0", "--port", "8080"]
