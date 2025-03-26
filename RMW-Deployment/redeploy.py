from fastapi import FastAPI, HTTPException, Query
import subprocess
import os

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
        pull_command = f"docker pull {config['image']}"
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
