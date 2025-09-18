# RAG Console

A production-grade per-user Retrieval-Augmented Generation (RAG) backend and console built with FastAPI, Postgres, Qdrant, and Redis. It provides secure per-user authentication, document ingestion and processing, vector search, and RAG query endpoints with both non-streaming and streaming (SSE) modes.

![UI Overview](./docs/images/ui-overview.png)
*Caption: RAG Console UI (Chat, Documents, History). Replace this image with your own screenshot.*

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HTTP Client   │────│     FastAPI     │────│    PostgreSQL    │
│ (e.g., browser) │    │     Backend     │    │    Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ├─────────────────────────────────┐
                               │                                 │
                    ┌─────────────────┐              ┌─────────────────┐
                    │     Qdrant      │              │      Redis      │
                    │  Vector DB      │              │      Cache      │
                    └─────────────────┘              └─────────────────┘

External: LLM Providers (OpenAI / Anthropic)
```

## Demo Video

<video src="./docs/rag.webm" controls width="720">
  Your browser does not support the video tag. You can download and view the demo video here:
  <a href="./docs/rag.webm">docs/rag.webm</a>
</video>

- [Download/view demo video (rag.webm)](./docs/rag.webm)

Optional GIF preview (for GitHub inline display):

![Demo](./docs/demo.gif)

## Screenshots

![Chat Screen](./docs/images/chat.png)
*Chat screen demonstrating a streaming RAG response*

![Documents Screen](./docs/images/documents.png)
*Documents screen showing upload and processing lifecycle*

![History Screen](./docs/images/history.png)
*History screen with query list, tokens, and status*


## Features

**Core Capabilities**
- Per-user model with strict user-level isolation
- Vector database integration using Qdrant (user_id in payload metadata; filtered retrieval)
- Support for multiple LLM providers (OpenAI, Anthropic, local models)
- Document processing for PDF, TXT, and DOCX files
- JWT-based authentication with role-based access control
- Background document processing
- Dockerized local development

**Security**
- Per-user isolation at database (Postgres) and vector store (Qdrant) levels
- Secure JWT authentication
- Input validation and sanitization
- Environment-based configuration management

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development, optional)
- OpenAI/Anthropic API keys (optional, for LLM functionality)

**1. Clone and Setup**

**2. Start the System**
```bash
docker-compose up -d --build
```

**3. Access**
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Usage Guide

**Authentication (Per-User)**
- Sign up: `POST /api/v1/auth/signup`
- Login (JWT): `POST /api/v1/auth/login`
- Current user: `GET /api/v1/auth/me` (Authorization: Bearer <token>)

**Documents**
1. Upload documents via `POST /api/v1/documents/upload` (multipart/form-data)
2. Processing runs in background: `uploaded → processing → processed`
3. Files are chunked, embedded, and stored in Qdrant with `user_id` metadata

**Queries (RAG)**
- `POST /api/v1/queries/rag` (non-stream): returns final response; exact provider token usage persisted
- `POST /api/v1/queries/rag/stream` (SSE): streams chunks; tokens estimated on finalize; metadata flag set
- `GET /api/v1/queries/history`: paginated query history for current user

**How It Works**
1. User authenticates (JWT)
2. Documents are uploaded and processed per user
3. Chunks are embedded and upserted to Qdrant with user_id in payload
4. Queries search only within the user’s document space
5. LLM generates responses using retrieved context; results and usage are persisted

## Development

### Local Development Setup

1. **Install Dependencies (optional)**
```bash
pip install -r requirements.txt
```

2. **Start Data Services Only**
```bash
docker-compose up -d postgres redis qdrant
```

3. **Run Backend Locally**
```bash
# Example environment setup
export DATABASE_URL="postgresql://postgres:password@localhost:5432/rag_console"
export QDRANT_HOST="localhost"
export REDIS_URL="redis://localhost:6379"

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Code Quality
```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string (db name: rag_console) | Required |
| `QDRANT_HOST` | Qdrant server host | localhost |
| `QDRANT_PORT` | Qdrant server port | 6333 |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `JWT_SECRET_KEY` | JWT signing secret | Required |
| `MAX_FILE_SIZE_MB` | Maximum upload file size | 10 |
| `EMBEDDING_MODEL` | Sentence transformer model | all-MiniLM-L6-v2 |

### Docker Compose Customization

Edit `docker-compose.yml` to customize:
- Resource limits
- Volume mounts
- Network configuration
- Environment variables

## Deployment

### Production Notes
- Scale FastAPI instances horizontally (behind a reverse proxy)
- Use managed Postgres (backups, replicas)
- Qdrant clustering for vector scale
- Object storage for large file persistence (e.g., S3)
- TLS termination at proxy (e.g., Nginx)

### Security Checklist
- [ ] Change default JWT secret key
- [ ] Use strong passwords for database
- [ ] Enable HTTPS/TLS in production
- [ ] Configure proper firewall rules
- [ ] Set up monitoring and structured logging
- [ ] Regular security updates

## Monitoring

### Health Checks
- API Health: `GET /health`
- Database: connection and query tests
- Vector Store: Qdrant `/health`
- LLM Services: Provider availability

### Logging (Structured JSON)
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "app.services.rag",
  "message": "RAG query completed",
  "user_id": "uuid",
  "processing_time_ms": 150
}
```

## API Documentation

**Authentication**
- `POST /api/v1/auth/signup` - User signup
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Current user info

**Document Management**
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/` - List documents
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document

**RAG Queries**
- `POST /api/v1/queries/rag` - Submit RAG query (non-stream)
- `POST /api/v1/queries/rag/stream` - Streaming RAG query (SSE)
- `GET /api/v1/queries/history` - Get query history
- `GET /api/v1/queries/analytics/summary` - Query analytics summary (optional)
- `GET /api/v1/queries/debug/vector-status` - Vector DB status
- `GET /api/v1/queries/debug/search-test` - Vector search test

## Troubleshooting

**Common Issues**

Database Connection Errors
```bash
docker-compose ps postgres
docker-compose logs postgres
```

Qdrant Connection Issues
```bash
curl http://localhost:6333/health
docker-compose logs qdrant
```

File Upload Failures
- Check file size limits (default 10MB)
- Verify supported file types (PDF, TXT, DOCX)
- Check upload directory permissions

LLM API Errors
- Verify API keys in .env file
- Check API rate limits
- Ensure network connectivity

**Debug Mode**
```bash
export DEBUG=true
docker-compose restart backend
```

## License

MIT (or your preferred license)

## Acknowledgments

Thanks to the open-source community around FastAPI, Qdrant, and the broader RAG ecosystem.

# rag_console