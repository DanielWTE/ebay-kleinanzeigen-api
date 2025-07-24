# Raspberry Pi Deployment Guide

This guide will help you deploy the Kleinanzeigen API on your Raspberry Pi using Docker.

## Prerequisites

- Raspberry Pi (3 or 4 recommended) with Raspberry Pi OS (64-bit recommended)
- At least 2GB RAM (4GB recommended for better performance)
- At least 8GB free storage space
- Internet connection

## Step 1: Prepare Your Raspberry Pi

### 1.1 Update your Raspberry Pi

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group (replace 'pi' with your username)
sudo usermod -aG docker $USER

# Log out and log back in for the group changes to take effect
# Or run: newgrp docker
```

### 1.3 Install Docker Compose

```bash
# Install Docker Compose plugin
sudo apt-get install docker-compose-plugin

# Verify installation
docker compose version
```

## Step 2: Transfer Your Project

### Option A: Using Git (Recommended)

```bash
# Clone your repository
git clone <your-repository-url>
cd ebay-kleinanzeigen-api
```

### Option B: Using SCP/SFTP

```bash
# From your development machine
scp -r /path/to/your/project pi@<raspberry-pi-ip>:/home/pi/
```

### Option C: Using USB Drive

1. Copy your project folder to a USB drive
2. Insert the USB drive into your Raspberry Pi
3. Copy the files to your home directory

## Step 3: Deploy the Application

### 3.1 Make the deployment script executable

```bash
chmod +x deploy.sh
```

### 3.2 Run the deployment script

```bash
./deploy.sh
```

The script will:

- Check if Docker and Docker Compose are installed
- Build the Docker image optimized for ARM64
- Start the application in a container
- Verify the application is running

### 3.3 Manual deployment (alternative)

If you prefer to deploy manually:

```bash
# Build and start the application
docker-compose up --build -d

# Check the logs
docker-compose logs -f

# Check if the application is running
curl http://localhost:8000/
```

## Step 4: Verify Deployment

### 4.1 Check if the application is running

```bash
# Check container status
docker ps

# Check application health
curl http://localhost:8000/
```

### 4.2 Access the API

- **API Base URL**: `http://<raspberry-pi-ip>:8000`
- **API Documentation**: `http://<raspberry-pi-ip>:8000/docs`
- **Health Check**: `http://<raspberry-pi-ip>:8000/`

### 4.3 Test the endpoints

```bash
# Test the root endpoint
curl http://localhost:8000/

# Test the API documentation
curl http://localhost:8000/docs
```

## Step 5: Configuration and Management

### 5.1 View logs

```bash
# View real-time logs
docker-compose logs -f

# View logs for a specific service
docker-compose logs kleinanzeigen-api
```

### 5.2 Stop the application

```bash
docker-compose down
```

### 5.3 Restart the application

```bash
docker-compose restart
```

### 5.4 Update the application

```bash
# Pull latest changes (if using git)
git pull

# Redeploy
./deploy.sh
```

## Step 6: Optional Configurations

### 6.1 Set up auto-start on boot

```bash
# Enable Docker service to start on boot
sudo systemctl enable docker

# Create a systemd service for auto-start
sudo nano /etc/systemd/system/kleinanzeigen-api.service
```

Add the following content:

```ini
[Unit]
Description=Kleinanzeigen API Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/ebay-kleinanzeigen-api
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Enable the service:

```bash
sudo systemctl enable kleinanzeigen-api.service
sudo systemctl start kleinanzeigen-api.service
```

### 6.2 Configure reverse proxy (optional)

If you want to access the API from outside your network or use a domain name, consider setting up a reverse proxy with Nginx or Traefik.

### 6.3 Set up monitoring (optional)

Consider setting up monitoring tools like:

- Portainer for Docker management
- Prometheus + Grafana for metrics
- Log aggregation with ELK stack

## Troubleshooting

### Common Issues

1. **Out of memory errors**

   - Increase swap space: `sudo dphys-swapfile swapoff && sudo dphys-swapfile set 2048 && sudo dphys-swapfile swapon`
   - Reduce Docker memory limits in `docker-compose.yml`

2. **Playwright browser issues**

   - The ARM64 Dockerfile includes all necessary dependencies
   - If issues persist, check the logs: `docker-compose logs kleinanzeigen-api`

3. **Port already in use**

   - Change the port in `docker-compose.yml`: `"8001:8000"`
   - Or stop other services using port 8000

4. **Permission issues**
   - Make sure your user is in the docker group
   - Run `newgrp docker` or log out and back in

### Performance Optimization

1. **Use SSD storage** if possible for better I/O performance
2. **Increase swap space** for memory-intensive operations
3. **Use a Raspberry Pi 4** with 4GB or 8GB RAM for better performance
4. **Monitor resource usage**: `htop` or `docker stats`

## Security Considerations

1. **Change default passwords** on your Raspberry Pi
2. **Use a firewall** to restrict access to necessary ports only
3. **Keep your system updated** regularly
4. **Use HTTPS** in production (set up SSL certificates)
5. **Monitor logs** for suspicious activity

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify Docker installation: `docker --version`
3. Check system resources: `htop`
4. Review the troubleshooting section above

For additional help, check the project's main README or create an issue in the repository.
