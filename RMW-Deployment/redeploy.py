from fastapi import FastAPI, HTTPException, Query
import subprocess
import os
import time

app = FastAPI()

# Get API key from the environment
DEPLOY_API_KEY = os.environ.get("DEPLOY_API_KEY")

# Service configuration mapping
SERVICE_CONFIG = {
    "frontend": {
        "image": "steelduck1/rmw-frontend:latest",
        "service_name": "rmw_rmw_frontend"
    },
    "backend": {
        "image": "steelduck1/rmw-backend:latest",
        "service_name": "rmw_rmw_backend"
    },
    "database": {
        "image": "steelduck1/rmw-database:latest",
        "service_name": "rmw_rmw_database"
    },
    "deployment": {
        "image": "steelduck1/rmw-deployment:latest",
        "service_name": "rmw_rmw_deployment"
    },
    "prometheus": {
        "image": "prom/prometheus:latest",
        "service_name": "monitoring_prometheus"
    },
    "grafana": {
        "image": "grafana/grafana:latest",
        "service_name": "monitoring_grafana"
    },
    "node-exporter": {
        "image": "prom/node-exporter:latest",
        "service_name": "monitoring_node-exporter"
    },
    "alertmanager": {
        "image": "prom/alertmanager:latest",
        "service_name": "monitoring_alertmanager"
    },
    "cadvisor": {
        "image": "gcr.io/cadvisor/cadvisor:latest",
        "service_name": "monitoring_cadvisor"
    },
    "monitoring-full": {
        "image": "none",
        "service_name": "monitoring"
    }
}

@app.post("/redeploy")
async def redeploy(
    api_key: str,
    service: str = Query(None, description="Specific service to update (frontend, backend, database, deployment, prometheus, grafana, node-exporter, alertmanager, cadvisor)")
):
    if not DEPLOY_API_KEY or api_key != DEPLOY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not service or service not in SERVICE_CONFIG:
        services_list = ", ".join(SERVICE_CONFIG.keys())
        raise HTTPException(status_code=400, detail=f"Invalid or missing service parameter. Must be one of: {services_list}")
    
    config = SERVICE_CONFIG[service]
    
    try:
        # Pull the latest image
        print(f"Pulling latest image for {service}...")
        
        # Special handling for full monitoring redeployment
        if service == "monitoring-full":
            print("Using special handler for complete monitoring stack redeployment...")
            
            # 1. Remove the existing stack
            print("Removing existing monitoring stack...")
            remove_cmd = "docker stack rm monitoring"
            subprocess.run(remove_cmd, shell=True, check=True)
            
            # 2. Wait for stack to be fully removed
            print("Waiting for monitoring stack to be fully removed...")
            time.sleep(15)
            
            # 3. Clean up all related volumes
            print("Cleaning up all monitoring volumes...")
            clean_cmd = "for vol in $(docker volume ls --format \"{{.Name}}\" | grep -E 'monitoring_|prometheus_data|grafana_data'); do docker volume rm $vol || true; done"
            subprocess.run(clean_cmd, shell=True, check=True)
            
            # 4. Update only RMW-Monitoring folder via sparse checkout
            print("Updating RMW-Monitoring configurations...")
            repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            monitoring_dir = os.path.join(repo_dir, "RMW-Monitoring")
            
            # Remove old monitoring directory if it exists
            if os.path.exists(monitoring_dir):
                rm_cmd = f"rm -rf {monitoring_dir}"
                subprocess.run(rm_cmd, shell=True, check=True)
            
            # Create sparse checkout for just RMW-Monitoring folder
            clone_cmd = f"""
            cd {repo_dir} && \
            git remote update && \
            git checkout main && \
            mkdir -p RMW-Monitoring && \
            git checkout main -- RMW-Monitoring
            """
            subprocess.run(clone_cmd, shell=True, check=True)
            
            # 5. Create network if needed
            print("Ensuring network exists...")
            net_cmd = "docker network create --driver overlay rmw-network || true"
            subprocess.run(net_cmd, shell=True, check=True)
            
            # 6. Update network name if needed
            print("Updating network configuration if needed...")
            sed_cmd = f"cd {repo_dir} && if grep -q 'monitor-net' RMW-Monitoring/docker-stack.yml; then sed -i 's/monitor-net/rmw-network/g' RMW-Monitoring/docker-stack.yml; fi"
            subprocess.run(sed_cmd, shell=True, check=True)
            
            # 7. Deploy the monitoring stack
            print("Deploying fresh monitoring stack...")
            deploy_cmd = f"cd {repo_dir} && docker stack deploy -c RMW-Monitoring/docker-stack.yml monitoring"
            result = subprocess.run(deploy_cmd, shell=True, check=True, capture_output=True, text=True)
            
            return {"message": "Complete monitoring stack redeployment successful", "output": result.stdout}
        
        # For all other services, continue with normal flow
        pull_command = f"docker pull {config['image']}"
        if service != "monitoring-full":  # Skip for monitoring-full since it doesn't have a real image
            subprocess.run(pull_command, shell=True, check=True)
        
        # Update the service with the new image
        print(f"Updating service {config['service_name']}...")
        update_command = (
            f"docker service update --with-registry-auth "
            f"--image {config['image']} {config['service_name']} "
            f"--update-parallelism 1 --update-delay 10s --update-order start-first"
        )
        result = subprocess.run(
            update_command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        return {"message": f"Redeployment triggered for service: {service}", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        error_message = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
        raise HTTPException(status_code=500, detail=f"Deployment failed: {error_message}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
