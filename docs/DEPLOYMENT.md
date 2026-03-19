# Deployment Guide

This guide covers how to deploy MemBlocks infrastructure and services.

## Table of Contents

- [Docker Compose Setup](#docker-compose-setup)
- [Environment Configuration](#environment-configuration)
- [Service Architecture](#service-architecture)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## Docker Compose Setup

MemBlocks uses Docker Compose to manage its infrastructure services. This provides a consistent development and deployment environment.

### Services Overview

The `docker-compose.yml` defines three key services:

#### 1. Qdrant (Vector Database)
- **Purpose**: Stores memory embeddings and metadata for semantic search
- **Ports**: 6333 (REST API), 6334 (gRPC)
- **Volume**: `memblocks_qdrant_data` for persistence
- **Image**: `qdrant/qdrant:latest`

#### 2. Ollama (Local Embeddings)
- **Purpose**: Provides local embedding generation (nomic-embed-text model)
- **Port**: 11434
- **Volume**: `memblocks_ollama_data` for model storage
- **Custom Build**: Uses `Dockerfile.ollama` to pre-pull embedding model

#### 3. MongoDB (Optional - Currently Commented Out)
- **Purpose**: Stores user data, memory block metadata, and authentication
- **Port**: 27017
- **Volume**: `memblocks_mongodb_data` for persistence
- **Credentials**: admin/memblocks123 (change in production!)

### Quick Start

1. **Start all services**:
   ```bash
   docker-compose up -d
   ```

2. **Check service status**:
   ```bash
   docker-compose ps
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f
   ```

4. **Stop services**:
   ```bash
   docker-compose down
   ```

5. **Stop and remove volumes** (⚠️ data loss):
   ```bash
   docker-compose down -v
   ```

### First-Time Setup

On first startup, Ollama will:
1. Start the service
2. Pull the `nomic-embed-text` model (~274MB)
3. Make it available for embedding generation

This is handled automatically by the `Dockerfile.ollama` build process.

---

## Environment Configuration

### Required Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

### Core Configuration

#### LLM Providers

Choose at least one LLM provider for memory extraction and processing:

```bash
# Groq (recommended for speed)
GROQ_API_KEY=your_groq_api_key_here

# OpenRouter (for diverse model access)
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

#### Vector Database

```bash
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

For cloud Qdrant deployment:
```bash
QDRANT_HOST=your-cluster.qdrant.io
QDRANT_PORT=6333
QDRANT_API_KEY=your_api_key_here
```

#### Embeddings

```bash
# Local Ollama (default)
OLLAMA_BASE_URL=http://localhost:11434

# Or use OpenAI embeddings
OPENAI_API_KEY=your_key_here
```

#### Reranking (Optional but Recommended)

```bash
COHERE_API_KEY=your_cohere_api_key_here
```

Improves retrieval quality by reranking search results.

#### Authentication (For Backend API)

```bash
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...
```

Get these from [Clerk Dashboard](https://dashboard.clerk.com).

### Configuration Files

The project uses a UV workspace structure with separate `pyproject.toml` files:

- **Root `pyproject.toml`**: Workspace configuration
- **`memblocks_lib/pyproject.toml`**: Core library dependencies
- **`backend/pyproject.toml`**: API server dependencies
- **`mcp_server/pyproject.toml`**: MCP server dependencies

---

## Service Architecture

### Network Architecture

All services run on a shared Docker network (`memblocks-network`) for internal communication:

```
┌─────────────────────────────────────┐
│  Host Machine (your computer)       │
│                                     │
│  ┌──────────┐  ┌─────────────────┐ │
│  │ Backend  │  │  MCP Server     │ │
│  │ (Python) │  │  (Python)       │ │
│  └────┬─────┘  └────┬────────────┘ │
│       │             │               │
│  ┌────▼─────────────▼────────────┐ │
│  │  memblocks-network (Docker)   │ │
│  │                                │ │
│  │  ┌──────────┐  ┌───────────┐  │ │
│  │  │ Qdrant   │  │  Ollama   │  │ │
│  │  │ :6333    │  │  :11434   │  │ │
│  │  └──────────┘  └───────────┘  │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### Data Persistence

Docker volumes ensure data persists across container restarts:

- **`memblocks_qdrant_data`**: All vector embeddings and metadata
- **`memblocks_ollama_data`**: Downloaded models
- **`memblocks_mongodb_data`**: User and block metadata (if enabled)

### Port Mapping

| Service | Internal Port | External Port | Purpose |
|---------|--------------|---------------|---------|
| Qdrant REST | 6333 | 6333 | Vector search API |
| Qdrant gRPC | 6334 | 6334 | High-performance queries |
| Ollama | 11434 | 11434 | Embedding generation |
| MongoDB | 27017 | 27017 | Database access |
| Backend | 8000 | 8000 | REST API (not in compose) |

---

## Production Deployment

### Security Considerations

#### 1. Environment Variables
- **Never commit `.env` files** to version control
- Use secure secret management (AWS Secrets Manager, HashiCorp Vault)
- Rotate API keys regularly

#### 2. Database Security
- Change default MongoDB credentials
- Enable authentication on all services
- Use TLS/SSL for connections
- Restrict network access with firewall rules

#### 3. API Keys
- Use separate API keys for production
- Set up rate limiting
- Monitor API usage and costs

### Cloud Deployment Options

#### Option 1: Single Server Deployment

Deploy all services on a single VM (suitable for small-medium scale):

**Requirements**:
- 4GB+ RAM
- 2+ CPU cores
- 50GB+ storage (for models and vectors)
- Ubuntu 22.04 or similar

**Setup**:
```bash
# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Clone repository
git clone <your-repo-url>
cd MemBlocks

# Configure environment
cp .env.example .env
nano .env  # Edit with production values

# Start services
docker-compose up -d

# Deploy backend (example with systemd)
sudo systemctl enable memblocks-backend.service
sudo systemctl start memblocks-backend
```

#### Option 2: Managed Services

Use cloud-managed versions of infrastructure:

**Qdrant**: [Qdrant Cloud](https://cloud.qdrant.io)
- Managed vector database
- Automatic scaling and backups
- Update `.env` with cluster URL and API key

**MongoDB**: [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- Free tier available
- Automatic backups and scaling
- Update connection string in `.env`

**Ollama**: Self-hosted or use OpenAI embeddings
- For production, consider OpenAI embeddings API for reliability
- Update config to use `openai` embeddings provider

#### Option 3: Container Orchestration

For large-scale deployments:

**Kubernetes**:
```yaml
# Example deployment structure
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qdrant
spec:
  replicas: 3
  # ... (full K8s config would go here)
```

**Docker Swarm**:
```bash
docker stack deploy -c docker-compose.yml memblocks
```

### Scaling Considerations

#### Horizontal Scaling
- **Backend API**: Stateless, can scale to multiple instances behind a load balancer
- **MCP Server**: Each user connection is independent
- **Qdrant**: Supports clustering for high availability

#### Vertical Scaling
- **RAM**: Increase for larger vector collections
- **CPU**: More cores improve embedding generation speed
- **Storage**: SSDs recommended for Qdrant performance

### Backup Strategy

#### Vector Database (Qdrant)
```bash
# Create snapshot
curl -X POST 'http://localhost:6333/collections/memblocks/snapshots'

# Download snapshot
curl -X GET 'http://localhost:6333/collections/memblocks/snapshots/{snapshot_name}' \
  --output snapshot.tar
```

#### MongoDB
```bash
# Backup
mongodump --uri="mongodb://admin:password@localhost:27017" --out=/backup

# Restore
mongorestore --uri="mongodb://admin:password@localhost:27017" /backup
```

#### Docker Volumes
```bash
# Backup volume
docker run --rm \
  -v memblocks_qdrant_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/qdrant-backup.tar.gz /data
```

---

## Troubleshooting

### Common Issues

#### Qdrant Connection Failed
```bash
# Check if Qdrant is running
docker-compose ps qdrant

# Check logs
docker-compose logs qdrant

# Verify port is accessible
curl http://localhost:6333/health
```

#### Ollama Model Not Found
```bash
# Check Ollama status
docker-compose logs ollama

# Manually pull model
docker-compose exec ollama ollama pull nomic-embed-text

# List available models
docker-compose exec ollama ollama list
```

#### MongoDB Connection Issues
```bash
# Check if MongoDB is running
docker-compose ps mongodb

# Test connection
docker-compose exec mongodb mongosh -u admin -p memblocks123
```

#### Port Already in Use
```bash
# Find process using port
netstat -ano | findstr :6333  # Windows
lsof -i :6333                 # Linux/Mac

# Stop conflicting service or change port in docker-compose.yml
```

#### Docker Volume Permissions
```bash
# On Linux, may need to fix permissions
sudo chown -R 1000:1000 /path/to/volumes
```

### Performance Optimization

#### Qdrant Performance
- Use SSD storage for better I/O
- Increase RAM allocation if needed
- Configure HNSW parameters for your use case
- Enable quantization for large collections

#### Ollama Performance
- GPU support: Add NVIDIA GPU passthrough to container
- Batch embedding requests when possible
- Consider using external embedding API for very high throughput

### Monitoring

#### Health Checks
```bash
# Qdrant
curl http://localhost:6333/health

# Ollama
curl http://localhost:11434/api/version

# MongoDB
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"
```

#### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f qdrant

# Last 100 lines
docker-compose logs --tail=100 ollama
```

#### Resource Usage
```bash
# Docker stats
docker stats

# Detailed container info
docker-compose exec qdrant top
```

---

## Additional Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Ollama Documentation](https://ollama.ai/docs)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [MemBlocks Architecture](./ARCHITECTURE.md)

---

**Need Help?** Open an issue on GitHub or check existing issues for solutions.
