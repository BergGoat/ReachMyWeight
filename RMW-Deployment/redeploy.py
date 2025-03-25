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
                os.chmod(tmpdirname, 0o755)
                
                # First, try to list the contents of the container
                list_command = f"docker run --rm {config['image']} ls -la /app/monitoring"
                result_list = subprocess.run(list_command, shell=True, check=True, capture_output=True, text=True)
                print(f"Container contents: {result_list.stdout}")
                
                # Run a container with the monitoring image, mounting the temp directory
                extract_command = f"docker run --rm -v {tmpdirname}:/target --user root {config['image']} /bin/sh -c 'mkdir -p /target && cp -rv /app/monitoring/* /target/ && chown -R 1000:1000 /target && chmod -R 755 /target && ls -la /target'"
                result_extract = subprocess.run(extract_command, shell=True, check=True, capture_output=True, text=True)
                print(f"Extraction output: {result_extract.stdout}")
                
                # Debug: list the extracted files
                print(f"Contents of extracted directory: {os.listdir(tmpdirname)}")
                
                # Check if docker-stack.yml exists in the extracted files
                if not os.path.exists(f"{tmpdirname}/docker-stack.yml"):
                    raise HTTPException(
                        status_code=500, 
                        detail=f"docker-stack.yml file not found in the extracted monitoring files. Contents: {os.listdir(tmpdirname)}"
                    )
                
                # Make sure the stack file is readable
                os.chmod(f"{tmpdirname}/docker-stack.yml", 0o644)
                
                # Deploy the stack with the extracted files
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
