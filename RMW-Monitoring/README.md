# RMW Monitoring

This directory contains the monitoring setup for the ReachMyWeight application using Prometheus and Grafana.

## Components

- **Prometheus**: Collects metrics from all services
- **Grafana**: Visualizes metrics with dashboards
- **Node Exporter**: Provides system-level metrics

## Configuration

The monitoring stack is configured with Infrastructure as Code:

- `prometheus.yml`: Main Prometheus configuration
- `grafana/provisioning/`: Grafana provisioning files (datasources and dashboards)
- `node-exporter/`: Node exporter configuration

## Access

- Prometheus UI: http://localhost:9090
- Grafana UI: http://localhost:3000 (admin/ReachMyWeight321)

## Deployment

The monitoring stack is deployed as part of the main docker-stack.yml and can be redeployed using the `/redeploy` endpoint:

```
curl -X POST "http://localhost:8080/redeploy?api_key=Belastingdienst321!&service=prometheus"
curl -X POST "http://localhost:8080/redeploy?api_key=Belastingdienst321!&service=grafana"
curl -X POST "http://localhost:8080/redeploy?api_key=Belastingdienst321!&service=node-exporter"
```

## Adding Metrics to Services

To add metrics to your services:

1. For Backend/Frontend/Database services, expose a metrics endpoint (typically at `/metrics`) using a library like:
   - Python: `prometheus_client`
   - JavaScript: `prom-client`

2. Update the `prometheus.yml` file if new endpoints are added

## Default Dashboards

The monitoring stack comes with a default dashboard that provides:
- Service health overview
- System metrics 