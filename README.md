# SAP Tools API 🚀

An intelligent FastAPI-based service that provides AI-powered SAP technical tools using LangGraph agents.

## 🌟 Features

- **🤖 AI-Powered Agent**: Natural language interface for SAP operations
- **📊 Table Schema Retrieval**: Get detailed SAP table structures and field information
- **💻 Source Code Access**: Fetch ABAP objects source code
- **🔍 API Metadata**: Retrieve OData service metadata and structure
- **🔍 Service Items**: Retrieve Service Items, CC Config Params, Material Characterstics
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
curl "http://localhost:8000/sap/tools?user_query=Get table schema for MAKT from D2A system"

# Get source code  
curl "http://localhost:8000/sap/tools?user_query=Show source code for ZCL_JIRA_ISSUES from D2A system"

# Get Service Items
curl "http://localhost:8000/sap/tools?user_query=Get Subs details for INTVG1232 from D2A System"

# Get service metadata
curl "http://localhost:8000/sap/tools?user_query=Get metadata for ZSD_PRODUCTS service, Namespace ZSB_PRODUCTS, System D2A"
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
curl http://localhost:8000/
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
4. Add to agent in `sap_agent.py`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

Vaibhav Goel

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

For support, please create a new issue with details

---
