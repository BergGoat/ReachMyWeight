# ReachMyWeight Frontend

This is the frontend web application for the ReachMyWeight platform. It provides a user interface for weight tracking and goal setting, and communicates with the Database API for data storage and the Backend API for weight goal calculations.

## Features

- User login and authentication
- Weight tracking dashboard with visualization
- Weight entry form with detailed input options
- API endpoints for weight data

## Architecture

The frontend is built using:
- FastAPI for both the web application and API
- Jinja2 for HTML templating
- Bootstrap for responsive UI
- httpx for making API calls to the Database and Backend services

## Configuration

The frontend communicates with:
- Database API: for user data and weight storage
- Backend API: for weight goal calculations

Configuration is set through environment variables:
- `DATABASE_API_URL`: URL of the Database API (default: http://Database:8000)
- `ORIGINAL_API_URL`: URL of the Backend API (default: http://Backend:8000)

## API Endpoints

### Web Routes (HTML Pages)
- `GET /`: Redirect to login
- `GET /login`: Login page
- `POST /login`: Process login
- `GET /dashboard`: User dashboard with weight history
- `GET /entry`: Weight entry form
- `POST /entry`: Process weight entry form

### API Routes (JSON)
- `GET /api/weights/{user_id}`: Get weight entries for a user
- `POST /api/weights`: Add a new weight entry
- `POST /api/calculate`: Calculate time to reach weight goal

## Docker Deployment

The application is containerized and can be deployed using Docker:

```bash
docker build -t steelduck1/RMW-Frontend:latest .
docker run -p 8000:8000 -e DATABASE_API_URL=http://Database:8000 -e ORIGINAL_API_URL=http://Backend:8000 steelduck1/RMW-Frontend:latest
```

Or using Docker Compose/Swarm as defined in the deployment configuration. 