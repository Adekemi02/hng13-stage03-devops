# Blue-Green Deployment with Nginx Reverse Proxy

This project demonstrates a **Blue-Green Deployment** setup using **Docker Compose** and **Nginx** as a reverse proxy.  
The setup allows **zero-downtime deployments** by routing traffic between two identical application environments:  
- **Blue Environment (Primary Application)**  
- **Green Environment (Backup Application)**

Nginx dynamically proxies requests to either the **Blue** or **Green** container, based on the configured upstream target.

---

## Image

<img width="1826" height="814" alt="image" src="https://github.com/user-attachments/assets/64b71d44-ae95-4195-bcef-884b96067177" />

---

## Project Structure

<img width="264" height="194" alt="image" src="https://github.com/user-attachments/assets/9a9303c9-df69-492a-bbb2-f881b7df276f" />

---

## Features

- Dynamic Reverse Proxy with Nginx
- Health check endpoint
- Zero downtime during failover
- Configuration via environment variables
- 

---

## Prerequisite

- Docker and Docker-Compose must be installed and running before running this project.
- Basic knowledge of environment variables and container networking.

---

## Usage

1. Clone this repository
    ```sh
    git clone https://github.com/Adekemi02/hng13-stage03-devops.git

2. Navigate into the project directory
    ```sh
    cd hng13-stage03-devops

3. Create and configure the .env file.
    ```sh
    cp .env.example .env
    ```
    Edit the .env file with the following variables:
    ```sh
    BLUE_IMAGE=<blue-image-name>
    GREEN_IMAGE=<green-image-name>
    ACTIVE_POOL=blue
    RELEASE_ID_BLUE=<blue-release-id-of-choice>
    RELEASE_ID_GREEN=<green-release-id-of-choice>
    PORT=8080
    ```

4. Run the application
    ```sh
    docker-compose up --build

5. Access the services.
    - Nginx Reverse Proxy: http://localhost:8080
    - Blue App(Direct): http://localhost:8081
    - Green App(Direct): http://localhost:8082

---

## Testing

1. Normal operation
    ```sh
    curl -i http://localhost:8080/version
    ```
    - **Expected** 
    ```sh
    HTTP/1.1 200 OK 
    X-App-Pool: blue 
    X-Release-Id: blue-v1
    ```

2. Trigger Failover (Blue App Failure)
    ```sh
    curl -X POST "http://localhost:8081/chaos/start?mode=error"
    ```
    - **Expected**  
    ```sh
    {"message":"Simulation mode 'error' activated"}
    ```

3. Verify Failover via Nginx
    ```sh
    curl -i http://localhost:8080/version
    ```
    - **Expected**  
    ```sh
    HTTP/1.1 200 OK 
    X-App-Pool: green 
    X-Release-Id: green-v1
    ```

4. Stop the Error Simulation
    ```sh
    curl -X POST http://localhost:8081/chaos/stop
    ```

---

## How it works

1. Two identical Node.js containers are run: one as the primary (Blue) and one as the backup (Green).

2. Nginx routes incoming traffic to Blue by default using the upstream configuration.
    - If Blue fails (5xx or timeout), Nginx retries the request on Green instantly.
    - Nginx monitors the Blue app via the health check endpoint.
    - Failures are detected based on max_fails and fail_timeout thresholds in the nginx.conf.template file.

3. The .env file controls which pool is active and passes release identifiers into containers.

4. Nginx dynamically substitutes the port variable via envsubst before loading the configuration.

---

## Cleaning Up
- To stop and remove containers:
    ```sh
    docker-compose down
    ```
