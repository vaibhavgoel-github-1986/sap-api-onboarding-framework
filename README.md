# SAP Tools API 🚀

An intelligent FastAPI-based service that provides AI-powered SAP technical tools using LangGraph agents.

## 🌟 Features

- **🤖 AI-Powered Agent**: Natural language interface for SAP operations
- **📊 Table Schema Retrieval**: Get detailed SAP table structures and field information
- **💻 Source Code Access**: Fetch ABAP objects source code
- **🔍 API Metadata**: Retrieve OData service metadata and structure
- **📋 Generic SAP API**: Unified interface for all SAP OData operations
- **🏗️ Connection Pooling**: Optimized HTTP connections for better performance
- **📝 Comprehensive Logging**: Structured logging with request/response tracking
- **🔒 Security**: Token-based authentication and secure configuration management

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │ -> │  LangGraph Agent │ -> │   SAP Systems   │
│                 │    │                  │    │   (D2A, QHA,    │
│  • Endpoints    │    │  • Tool Routing  │    │    RHA, etc.)   │
│  • Validation   │    │  • LLM Reasoning │    │                 │
│  • Error Handle │    │  • Task Planning │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Access to SAP systems
- Azure OpenAI credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-powered-tools
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the application**
   ```bash
   python run_server.py
   ```

The API will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Azure Authentication
AZURE_APP_KEY=your_app_key
AZURE_USER_ID=your_user_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_TOKEN_URL=https://id.cisco.com/oauth2/default/v1/token

# Azure OpenAI
AZURE_ENDPOINT=https://chat-ai.cisco.com
AZURE_API_VERSION=2025-04-01-preview
AZURE_DEPLOYMENT_NAME=gpt-4.1

# SAP Systems
SAP_DEFAULT_SYSTEM_ID=D2A
SAP_USERNAME=your_sap_username
SAP_PASSWORD=your_sap_password

# Logging
LOG_LEVEL=INFO

# Optional: LangSmith tracing
LANGSMITH_API_KEY=your_langsmith_key
```

### Supported SAP Systems

| System ID | Environment | Description |
|-----------|-------------|-------------|
| `D2A` | Development | Development System |
| `DHA` | Development | Alternative Dev System |
| `QHA` | QA | Quality Assurance |
| `Q2A` | QA | Alternative QA System |
| `RHA` | Pre-Prod | Pre-Production |
| `SHA` | Sandbox | Sandbox Environment |

## 📚 API Usage

### Basic Query Examples

```bash
# Get table schema
curl "http://localhost:8000/sap_tech/tools?user_query=Get table schema for MAKT from D2A system"

# Get source code  
curl "http://localhost:8000/sap_tech/tools?user_query=Show source code for ZCL_JIRA_ISSUES from D2A system"

# Get service metadata
curl "http://localhost:8000/sap_tech/tools?user_query=Get metadata for ZSD_PRODUCTS service, Namespace ZSB_PRODUCTS, System D2A"
```

### Response Format

```json
{
    "success": true,
    "response": "Table MAKT contains 10 fields: MANDT, MATNR, SPRAS, ...",
    "error": null
}
```

## 🧪 Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## 🐳 Docker Deployment

### Build and run with Docker

```bash
# Build the image
docker build -t sap-tools-api .

# Run the container
docker run -p 8000:8000 --env-file .env sap-tools-api
```

### Docker Compose (recommended)

```yaml
version: '3.8'
services:
  sap-tools-api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 📊 Monitoring & Logging

### Structured Logging

The application uses structured JSON logging for better observability:

```json
{
  "event_type": "api_request",
  "http_method": "GET",
  "user_query": "Get schema for MAKT table",
  "system_id": "D2A",
  "timestamp": "2024-01-01T12:00:00"
}
```

### Health Check

Monitor application health:

```bash
curl http://localhost:8000/health
```

## 🛠️ Development

### Project Structure

```
src/
├── agents/              # LangGraph agents
├── config.py           # Configuration management
├── llm_model/          # Azure OpenAI integration
├── pydantic_models/    # Data models
├── routers/            # FastAPI routers
├── tools/              # SAP tools for agents
├── utils/              # Utilities (logging, HTTP client)
└── main.py             # FastAPI application
```

### Adding New Tools

1. Create a new tool in `src/tools/`
2. Inherit from `BaseSAPTool`
3. Implement required methods
4. Add to agent in `sap_tech_agent.py`

### Code Quality

```bash
# Format code
black src/
isort src/

# Lint code  
flake8 src/
mypy src/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

[Add your license information here]

## 🆘 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Check Azure credentials in `.env`
   - Verify token URL and client credentials

2. **SAP Connection Issues**  
   - Verify SAP system connectivity
   - Check SAP username/password
   - Ensure system ID is correct

3. **Performance Issues**
   - Check connection pool settings
   - Monitor memory usage
   - Review log files for bottlenecks

### Support

For support, please:
1. Check the documentation
2. Search existing issues
3. Create a new issue with details

---

**Built with ❤️ using FastAPI, LangGraph, and Azure OpenAI**