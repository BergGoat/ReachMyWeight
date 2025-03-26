#!/bin/bash

# ReachMyWeight Complete Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/BergGoat/ReachMyWeight/main/install-rmw.sh | bash
set -e

echo "🚀 Setting up ReachMyWeight stack..."

# Check requirements
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check for swarm mode
if ! docker node ls &> /dev/null; then
    echo "❌ Docker swarm not initialized. Initializing now..."
    docker swarm init
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# Create prometheus.yml
mkdir -p RMW-Monitoring
cat > RMW-Monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['prometheus:9090']
  
  - job_name: 'rmw_backend'
    static_configs:
      - targets: ['rmw_backend:8001']
    
  - job_name: 'rmw_frontend'
    static_configs:
      - targets: ['rmw_frontend:8000']
    
  - job_name: 'rmw_database'
    static_configs:
      - targets: ['rmw_database:8002']
    
  - job_name: 'rmw_deployment'
    static_configs:
      - targets: ['rmw_deployment:8080']
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
EOF

# Create Grafana datasource
mkdir -p RMW-Monitoring/grafana/provisioning/datasources
cat > RMW-Monitoring/grafana/provisioning/datasources/datasources.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF

# Create Grafana dashboard config
mkdir -p RMW-Monitoring/grafana/provisioning/dashboards
cat > RMW-Monitoring/grafana/provisioning/dashboards/dashboards.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'RMW Default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /etc/grafana/provisioning/dashboards/json
EOF

# Create dashboard json directory
mkdir -p RMW-Monitoring/grafana/provisioning/dashboards/json
cat > RMW-Monitoring/grafana/provisioning/dashboards/json/rmw-dashboard.json << 'EOF'
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": 1,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "PBFA97CFB590B2093"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisCenteredZero": false,
            "axisColorMode": "text",
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "drawStyle": "line",
            "fillOpacity": 10,
            "gradientMode": "none",
            "hideFrom": {
              "legend": false,
              "tooltip": false,
              "viz": false
            },
            "lineInterpolation": "linear",
            "lineWidth": 1,
            "pointSize": 5,
            "scaleDistribution": {
              "type": "linear"
            },
            "showPoints": "never",
            "spanNulls": false,
            "stacking": {
              "group": "A",
              "mode": "normal"
            },
            "thresholdsStyle": {
              "mode": "off"
            }
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "red",
                "value": 80
              }
            ]
          },
          "unit": "short"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "legend": {
          "calcs": [],
          "displayMode": "list",
          "placement": "bottom",
          "showLegend": true
        },
        "tooltip": {
          "mode": "single",
          "sort": "none"
        }
      },
      "title": "RMW Service Status",
      "type": "timeseries"
    }
  ],
  "refresh": "5s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": [],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {
    "refresh_intervals": [
      "5s",
      "10s",
      "30s",
      "1m",
      "5m",
      "15m",
      "30m",
      "1h",
      "2h",
      "1d"
    ]
  },
  "timezone": "",
  "title": "RMW Overview",
  "uid": "rmw-overview",
  "version": 1,
  "weekStart": ""
}
EOF

# Create node-exporter config
mkdir -p RMW-Monitoring/node-exporter
cat > RMW-Monitoring/node-exporter/config.yml << 'EOF'
---
# Node exporter configuration
collectors:
  enabled: all
  disabled:
    - mdadm  # Disable if not needed
    - wifi   # Disable if not needed
  filesystem:
    ignored-mount-points: "^/(dev|proc|sys|var/lib/docker/.+)($|/)"
    ignored-fs-types: "^(autofs|binfmt_misc|bpf|cgroup2?|configfs|debugfs|devpts|devtmpfs|fusectl|hugetlbfs|mqueue|nsfs|overlay|proc|procfs|pstore|rpc_pipefs|securityfs|selinuxfs|squashfs|sysfs|tracefs)$"
EOF

# Create the docker-stack.yml
cat > docker-stack.yml << 'EOF'
version: '3.8'

services:
  rmw_deployment:
    image: steelduck1/rmw-deployment:latest
    ports:
      - "8080:8080"
    environment:
      - DEPLOY_API_KEY=Belastingdienst321!
      - DOCKER_USERNAME=steelduck1
      - DOCKER_PASSWORD=dckr_pat_kGDJWvFImSRa5a5auIM5m0a2zLR1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    networks:
      - rmw-network

  rmw_frontend:
    image: steelduck1/rmw-frontend:latest
    ports:
      - "80:8000"
    environment:
      - DATABASE_API_URL=http://rmw_database:8002
      - ORIGINAL_API_URL=http://rmw_backend:8001
    deploy:
      replicas: 2
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    networks:
      - rmw-network

  rmw_backend:
    image: steelduck1/rmw-backend:latest
    ports:
      - "8001:8001"
    environment:
      - DATABASE_API_URL=http://rmw_database:8002
    deploy:
      replicas: 2
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    networks:
      - rmw-network
    depends_on:
      - rmw_database

  rmw_database:
    image: steelduck1/rmw-database:latest
    ports:
      - "8002:8002"
    environment:
      - SQLITE_CONNECTION_PARAMS=check_same_thread=False
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    volumes:
      - rmw_database_data:/app/data
    networks:
      - rmw-network

  # Monitoring Services
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./RMW-Monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    networks:
      - rmw-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - ./RMW-Monitoring/grafana/provisioning:/etc/grafana/provisioning
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=ReachMyWeight321
      - GF_USERS_ALLOW_SIGN_UP=false
    deploy:
      replicas: 1
      restart_policy:
        condition: any
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
    networks:
      - rmw-network
    depends_on:
      - prometheus

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
      - ./RMW-Monitoring/node-exporter/config.yml:/etc/node-exporter/config.yml
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--path.rootfs=/rootfs'
      - '--collector.filesystem.ignored-mount-points=^/(sys|proc|dev|host|etc)($$|/)'
    deploy:
      mode: global
      restart_policy:
        condition: any
    networks:
      - rmw-network

networks:
  rmw-network:
    driver: overlay

volumes:
  rmw_database_data:
  prometheus_data:
  grafana_data:
EOF

# Deploy the stack
echo "📦 Deploying stack..."
docker stack deploy -c docker-stack.yml rmw

# Save files to a permanent location
mkdir -p ~/rmw-stack
cp -r * ~/rmw-stack/
echo "💾 Configuration files saved to ~/rmw-stack/"

# Cleanup
cd - > /dev/null
rm -rf $TEMP_DIR

echo "✅ ReachMyWeight installation complete!"
echo "Frontend: http://localhost:80"
echo "Backend API: http://localhost:8001"
echo "Database API: http://localhost:8002"
echo "Deployment Service: http://localhost:8080"
echo "Grafana UI: http://localhost:3000 (admin/ReachMyWeight321)"
echo "Prometheus UI: http://localhost:9090"
echo ""
echo "You can check stack status with: docker stack services rmw" 