from fastapi import FastAPI, HTTPException, Query
import subprocess
import os
import tempfile
import shutil

app = FastAPI()

# Get API key from the environment
DEPLOY_API_KEY = os.environ.get("DEPLOY_API_KEY", "Belastingdienst321!")

# Docker Hub credentials from environment
DOCKER_USERNAME = os.environ.get("DOCKER_USERNAME", "steelduck1")
DOCKER_PASSWORD = os.environ.get("DOCKER_PASSWORD", "dckr_pat_TpcaLQTc0H7-1P_yi2JN54qoqnY")

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
    "monitoring": {
        "image": "steelduck1/rmw-monitoring:latest",
        "stack_name": "rmw_monitoring",
        "stack_file": "docker-stack.yml"
    }
}

@app.post("/redeploy")
async def redeploy(
    api_key: str,
    service: str = Query(None, description="Specific service to update (frontend, backend, database, deployment, monitoring)"),
    skip_docker_login: bool = Query(False, description="Skip Docker login step (useful when credentials are already available)")
):
    if api_key != DEPLOY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not service or service not in SERVICE_CONFIG:
        raise HTTPException(status_code=400, detail="Invalid or missing service parameter. Must be one of: frontend, backend, database, deployment, monitoring")
    
    config = SERVICE_CONFIG[service]
    
    try:
        # 1. Log in to Docker Hub (if not skipped)
        if not skip_docker_login:
            login_command = f"echo {DOCKER_PASSWORD} | docker login --username {DOCKER_USERNAME} --password-stdin"
            subprocess.run(login_command, shell=True, check=True)
        
        # 2. Pull the latest image
        pull_command = f"docker pull {config['image']}"
        subprocess.run(pull_command, shell=True, check=True)
        
        # 3. Update the service or deploy the stack
        if service == "monitoring":
            # For monitoring, use direct Docker service commands instead of stack file
            print("Deploying monitoring services using direct Docker service commands")

            try:
                # Create network if it doesn't exist
                network_command = "docker network create --driver overlay rmw_monitoring_network || true"
                subprocess.run(network_command, shell=True, check=False)
                
                # Define service commands for each monitoring component
                services = [
                    # Prometheus
                    """docker service create --name rmw_monitoring_prometheus --network rmw_monitoring_network \
                    --publish 9090:9090 --mount type=volume,source=prometheus_data,target=/prometheus \
                    --constraint 'node.role==manager' \
                    prom/prometheus:v2.36.2 \
                    --storage.tsdb.path=/prometheus \
                    --web.console.libraries=/usr/share/prometheus/console_libraries \
                    --web.console.templates=/usr/share/prometheus/consoles \
                    --web.enable-lifecycle""",
                    
                    # Node Exporter
                    """docker service create --name rmw_monitoring_node-exporter --network rmw_monitoring_network \
                    --publish 9100:9100 --mode global \
                    --mount type=bind,source=/proc,target=/host/proc,readonly \
                    --mount type=bind,source=/sys,target=/host/sys,readonly \
                    --mount type=bind,source=/,target=/rootfs,readonly \
                    quay.io/prometheus/node-exporter:latest \
                    --path.procfs=/host/proc \
                    --path.sysfs=/host/sys \
                    --collector.filesystem.ignored-mount-points="^/(sys|proc|dev|host|etc|rootfs/var/lib/docker/containers|rootfs/var/lib/docker/overlay2|rootfs/run/docker/netns|rootfs/var/lib/docker/aufs)($$|/)" """,
                    
                    # cAdvisor
                    """docker service create --name rmw_monitoring_cadvisor --network rmw_monitoring_network \
                    --publish 8081:8080 --mode global \
                    --mount type=bind,source=/,target=/rootfs,readonly \
                    --mount type=bind,source=/var/run,target=/var/run \
                    --mount type=bind,source=/sys,target=/sys,readonly \
                    --mount type=bind,source=/var/lib/docker/,target=/var/lib/docker,readonly \
                    gcr.io/cadvisor/cadvisor""",
                    
                    # Grafana
                    """docker service create --name rmw_monitoring_grafana --network rmw_monitoring_network \
                    --publish 3000:3000 --mount type=volume,source=grafana_data,target=/var/lib/grafana \
                    --constraint 'node.role==manager' \
                    -e GF_SECURITY_ADMIN_PASSWORD=foobar \
                    -e GF_USERS_ALLOW_SIGN_UP=false \
                    -e GF_AUTH_ANONYMOUS_ENABLED=true \
                    -e GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer \
                    -e GF_INSTALL_PLUGINS=grafana-piechart-panel \
                    grafana/grafana""",
                    
                    # Alertmanager
                    """docker service create --name rmw_monitoring_alertmanager --network rmw_monitoring_network \
                    --publish 9093:9093 --mount type=volume,source=alertmanager_data,target=/alertmanager \
                    --constraint 'node.role==manager' \
                    prom/alertmanager \
                    --storage.path=/alertmanager"""
                ]
                
                # For each service, try to create it, if it exists, update it
                for service_cmd in services:
                    service_name = service_cmd.split("--name ")[1].split(" ")[0]
                    print(f"Deploying {service_name}")
                    
                    # Check if service exists
                    check_command = f"docker service inspect {service_name} > /dev/null 2>&1"
                    exists = subprocess.run(check_command, shell=True).returncode == 0
                    
                    if exists:
                        # Service exists, update it
                        print(f"Service {service_name} exists, updating...")
                        # Extract image name from the create command - fix the extraction logic
                        if "prometheus" in service_name:
                            image = "prom/prometheus:v2.36.2"
                        elif "node-exporter" in service_name:
                            image = "quay.io/prometheus/node-exporter:latest"
                        elif "cadvisor" in service_name:
                            image = "gcr.io/cadvisor/cadvisor"
                        elif "grafana" in service_name:
                            image = "grafana/grafana"
                        elif "alertmanager" in service_name:
                            image = "prom/alertmanager"
                        else:
                            # Fallback to the original extraction logic but with better filtering
                            image_parts = service_cmd.split("\n")[-1].strip().split(" ")
                            for part in image_parts:
                                if "/" in part and ":" in part and not part.startswith("--") and not part.startswith("-"):
                                    image = part
                                    break
                            else:
                                image = None
                            
                        if image:
                            update_cmd = f"docker service update --with-registry-auth --image {image} {service_name}"
                            print(f"Running: {update_cmd}")
                            subprocess.run(update_cmd, shell=True, check=True)
                        else:
                            print(f"Could not extract image from command for {service_name}, skipping update")
                    else:
                        # Service doesn't exist, create it
                        print(f"Service {service_name} doesn't exist, creating...")
                        print(f"Running: {service_cmd}")
                        subprocess.run(service_cmd, shell=True, check=True)
                
                return {"message": f"Redeployment triggered for services: monitoring", "output": "All monitoring services deployed successfully"}
                
            except subprocess.CalledProcessError as e:
                error_message = e.stderr if hasattr(e, 'stderr') and e.stderr else str(e)
                raise HTTPException(status_code=500, detail=f"Deployment failed: {error_message}")
        else:
            # For regular services
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
