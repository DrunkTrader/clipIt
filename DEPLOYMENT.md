# Deployment Guide

This guide provides instructions for deploying the Clip-It application to production.

## Prerequisites

- Docker and Docker Compose installed on the deployment server
- Domain name configured (optional but recommended)
- SSL certificates (via Let's Encrypt or similar)
- Redis connection string (if using external Redis)

## Quick Start with Docker Compose

### 1. Clone and Configure

```bash
git clone <repository-url>
cd clip-it
```

### 2. Configure Environment Variables

**Server (.env.production):**
```bash
cp server/.env.example server/.env.production
# Edit server/.env.production with production values
```

Key variables to update:
- `ALLOWED_ORIGINS`: Your frontend domain(s)
- `BASE_URL`: Your API base URL
- `REDIS_URL`: Redis connection string

**Client (.env.production):**
```bash
cp client/.env.local.example client/.env.production
# Edit client/.env.production with production values
```

Key variables to update:
- `NEXT_PUBLIC_API_URL`: Your backend API URL

### 3. Deploy with Docker Compose

```bash
docker-compose -f docker-compose.yml up -d --build
```

### 4. Verify Deployment

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Health checks
curl http://localhost:8080/health
curl http://localhost:3000
```

## Production Considerations

### Security

1. **SSL/TLS Configuration**
   - Use a reverse proxy (Nginx, Traefik) for HTTPS
   - Obtain SSL certificates via Let's Encrypt
   - Redirect HTTP to HTTPS

2. **Environment Variables**
   - Never commit `.env.production` files
   - Use secrets management (Docker Swarm secrets, Kubernetes Secrets, AWS Secrets Manager)

3. **Firewall Rules**
   - Only expose necessary ports (80, 443)
   - Block direct access to backend ports
   - Restrict Redis access to internal network only

### Scaling

**Horizontal Scaling:**
```yaml
# In docker-compose.yml, adjust worker count
server:
  environment:
    - GUNICORN_WORKERS=4  # Adjust based on CPU cores
```

**Resource Limits:**
```yaml
server:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

### Monitoring

1. **Health Checks**: Built into docker-compose.yml
2. **Logging**: Configure log rotation
3. **Metrics**: Add Prometheus/Grafana for monitoring
4. **Alerting**: Set up alerts for service failures

### Backup Strategy

```bash
# Backup Redis data
docker-compose exec redis redis-cli SAVE

# Backup downloaded clips
docker-compose exec server tar -czf downloads-backup.tar.gz /app/downloads
```

## Alternative Deployment Options

### Kubernetes

For Kubernetes deployment, create:
- Deployment manifests for server and client
- Service definitions
- ConfigMaps for environment variables
- Secrets for sensitive data
- Ingress rules for routing

### Cloud Platforms

**AWS:**
- ECS/Fargate for container orchestration
- ElastiCache for Redis
- Application Load Balancer
- S3 for clip storage (alternative to local volume)

**DigitalOcean:**
- App Platform for managed deployment
- Managed Redis
- Load Balancer

**Google Cloud:**
- Cloud Run for serverless containers
- Memorystore for Redis
- Cloud Load Balancing

### Nginx Reverse Proxy Example

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## CI/CD Pipeline

The project includes a GitHub Actions workflow (`.github/workflows/ci-cd.yml`) that:

1. **Lint and Test**: Validates code quality on every PR
2. **Build Docker Images**: Creates and pushes images on main branch
3. **Deploy**: Triggers deployment (customize for your infrastructure)

### Required GitHub Secrets

- `DOCKER_USERNAME`: Docker Hub username
- `DOCKER_PASSWORD`: Docker Hub password or access token
- `DEPLOY_TOKEN`: Deployment platform token

## Troubleshooting

### Common Issues

**Container won't start:**
```bash
docker-compose logs server
docker-compose logs client
```

**Redis connection failed:**
- Ensure Redis service is healthy: `docker-compose ps redis`
- Check REDIS_URL environment variable

**CORS errors:**
- Verify ALLOWED_ORIGINS includes your frontend domain
- Check for trailing slashes in URLs

**High memory usage:**
- Reduce GUNICORN_WORKERS
- Add resource limits in docker-compose.yml
- Implement clip cleanup strategy

### Performance Optimization

1. **Enable caching** in Redis for frequently accessed clips
2. **Use CDN** for static assets
3. **Implement rate limiting** (already included via slowapi)
4. **Optimize ffmpeg** encoding settings based on use case

## Support

For issues and questions:
- Check existing issues on GitHub
- Review server/server_readme.md for API details
- Consult FastAPI and Next.js documentation
