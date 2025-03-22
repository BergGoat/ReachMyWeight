from fastapi import FastAPI, HTTPException, Query
import subprocess
import os

app = FastAPI()

# Get API key from the environment
DEPLOY_API_KEY = os.environ.get("DEPLOY_API_KEY", "default_key")

# Docker Hub credentials 
DOCKER_USERNAME = "steelduck1"
DOCKER_PASSWORD = "dckr_pat_kGDJWvFImSRa5a5auIM5m0a2zLR1"

@app.post("/redeploy")
async def redeploy(
    api_key: str,
    monitoring_update: bool = Query(False, description="Update the monitoring stack"),
    service: str = Query(None, description="Specific service to update (backend, database, etc.)")
):
    if api_key != DEPLOY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    try:
        # Log in to Docker Hub
        login_command = f"echo {DOCKER_PASSWORD} | docker login --username {DOCKER_USERNAME} --password-stdin"
        subprocess.run(login_command, shell=True, check=True)

        if monitoring_update:
            # Handle monitoring stack deployment directly from our repo
            try:
                # Deploy the stack using the docker-stack.yml from RMW-Monitoring
                monitoring_dir = "/app/RMW-Monitoring"
                
                if not os.path.exists(f"{monitoring_dir}/docker-stack.yml"):
                    raise HTTPException(status_code=500, detail="docker-stack.yml not found in RMW-Monitoring directory")
                
                # Get the hostname for the deployment
                hostname_command = "hostname"
                hostname = subprocess.run(
                    hostname_command, 
                    shell=True, 
                    check=True, 
                    capture_output=True, 
                    text=True
                ).stdout.strip()
                
                # Deploy directly from our repository
                deploy_command = f"cd {monitoring_dir} && HOSTNAME={hostname} docker stack deploy -c docker-stack.yml monitoring-stack --with-registry-auth"
                result = subprocess.run(
                    deploy_command,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                return {
                    "message": "Redeployment triggered for monitoring stack", 
                    "output": result.stdout
                }
            except subprocess.CalledProcessError as e:
                raise HTTPException(status_code=500, detail=f"Monitoring deployment failed: {e.stderr}")
        elif service:
            # Handle specific service updates
            service = service.lower()
            
            if service == "backend":
                # Update the backend service
                pull_command = "docker pull steelduck1/RMW-Backend:latest"
                subprocess.run(pull_command, shell=True, check=True)
                
                update_command = (
                    "docker service update --force --with-registry-auth "
                    "--image steelduck1/RMW-Backend:latest mijn_stack_Backend"
                )
                result = subprocess.run(
                    update_command,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                return {"message": f"Redeployment triggered for {service}", "output": result.stdout}
            elif service == "database":
                # Update the database service
                pull_command = "docker pull steelduck1/RMW-Database:latest"
                subprocess.run(pull_command, shell=True, check=True)
                
                update_command = (
                    "docker service update --force --with-registry-auth "
                    "--image steelduck1/RMW-Database:latest mijn_stack_Database"
                )
                result = subprocess.run(
                    update_command,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                return {"message": f"Redeployment triggered for {service}", "output": result.stdout}
            elif service == "frontend":
                # Update the frontend service
                pull_command = "docker pull steelduck1/RMW-Frontend:latest"
                subprocess.run(pull_command, shell=True, check=True)
                
                update_command = (
                    "docker service update --force --with-registry-auth "
                    "--image steelduck1/RMW-Frontend:latest mijn_stack_Frontend"
                )
                result = subprocess.run(
                    update_command,
                    shell=True,
                    check=True,
                    capture_output=True,
                    text=True
                )
                
                return {"message": f"Redeployment triggered for {service}", "output": result.stdout}
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported service: {service}")
        else:
            # Default behavior: update the original service
            pull_command = "docker pull steelduck1/python_ci-cd_test:latest"
            subprocess.run(pull_command, shell=True, check=True)

            update_command = (
                "docker service update --force --with-registry-auth "
                "--image steelduck1/python_ci-cd_test:latest mijn_stack_calculator"
            )
            result = subprocess.run(
                update_command,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )

            return {"message": "Redeployment triggered", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {e.stderr}")
