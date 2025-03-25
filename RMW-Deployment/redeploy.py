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
            # For monitoring, we use a special approach:
            # Create a temporary directory to extract the monitoring files
            with tempfile.TemporaryDirectory() as tmpdirname:
                # Set proper permissions on the temporary directory
                os.chmod(tmpdirname, 0o777)
                print(f"Created temporary directory: {tmpdirname}")
                
                # Create a simplified stack file directly
                print("Creating simplified stack file with named volumes")
                simplified_stack = """version: '3.7'

volumes:
    prometheus_data: {}
    grafana_data: {}
    alertmanager_data: {}

networks:
  monitor-net:

services:
  prometheus:
    image: prom/prometheus:v2.36.2
    volumes:
      - prometheus_data:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    ports:
      - 9090:9090
    networks:
      - monitor-net
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure

  node-exporter:
    image: quay.io/prometheus/node-exporter:latest
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command: 
      - '--path.procfs=/host/proc' 
      - '--path.sysfs=/host/sys'
      - --collector.filesystem.ignored-mount-points
      - "^/(sys|proc|dev|host|etc|rootfs/var/lib/docker/containers|rootfs/var/lib/docker/overlay2|rootfs/run/docker/netns|rootfs/var/lib/docker/aufs)($$|/)"
    ports:
      - 9100:9100
    networks:
      - monitor-net
    deploy:
      mode: global
      restart_policy:
        condition: on-failure

  alertmanager:
    image: prom/alertmanager
    ports:
      - 9093:9093
    volumes:
      - alertmanager_data:/alertmanager
    networks:
      - monitor-net
    command:
      - '--storage.path=/alertmanager'
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure    

  cadvisor:
    image: gcr.io/cadvisor/cadvisor
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:rw
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    ports:
      - 8081:8080
    networks:
      - monitor-net
    deploy:
      mode: global
      restart_policy:
        condition: on-failure

  grafana:
    image: grafana/grafana
    depends_on:
      - prometheus
    ports:
      - 3000:3000
    volumes:
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - monitor-net
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
"""
                
                # Write the simplified stack file
                stack_file_path = f"{tmpdirname}/docker-stack.yml"
                with open(stack_file_path, 'w') as f:
                    f.write(simplified_stack)
                
                print(f"Created stack file at {stack_file_path}")
                
                # Make sure the stack file is readable
                os.chmod(stack_file_path, 0o644)
                
                # Deploy the stack with the simplified file
                stack_command = f"cd {tmpdirname} && docker stack deploy -c docker-stack.yml {config['stack_name']} --with-registry-auth"
                result = subprocess.run(
                    stack_command,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                return {"message": f"Redeployment triggered for stack: {service}", "output": result.stdout}
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
