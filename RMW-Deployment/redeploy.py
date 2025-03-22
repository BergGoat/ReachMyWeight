from fastapi import FastAPI, HTTPException
import subprocess
import os

app = FastAPI()

# Haal de API key op uit de omgeving; zorg dat deze correct is ingesteld in je deployment
DEPLOY_API_KEY = os.environ.get("DEPLOY_API_KEY", "default_key")

# Hardcoded Docker Hub credentials (let op: in productie liever als secrets)
DOCKER_USERNAME = "steelduck1"
DOCKER_PASSWORD = "dckr_pat_kGDJWvFImSRa5a5auIM5m0a2zLR1"

@app.post("/redeploy")
async def redeploy(api_key: str):
    if api_key != DEPLOY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    try:
        # 0. Log in bij Docker Hub
        login_command = f"echo {DOCKER_PASSWORD} | docker login --username {DOCKER_USERNAME} --password-stdin"
        subprocess.run(login_command, shell=True, check=True)

        # 1. Pull de nieuwste image
        pull_command = "docker pull steelduck1/python_ci-cd_test:latest"
        subprocess.run(pull_command, shell=True, check=True)

        # 2. Update de Swarm-service met de nieuwe image
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
