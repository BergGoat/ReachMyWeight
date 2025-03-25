#!/bin/sh

# Deploy the monitoring stack using the docker-stack.yml file
echo "Deploying RMW-Monitoring stack..."
docker stack deploy -c docker-stack.yml prom --with-registry-auth

# Check deployment status
echo "Deployment triggered. Check status with 'docker stack ps rmw_monitoring'"
echo "Grafana will be available at: http://localhost:3000"
echo "Prometheus will be available at: http://localhost:9090" 