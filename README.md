# SAP Tools API 🚀

An intelligent FastAPI service that uses AI agents to query SAP systems through natural language.

## ✨ Features

- **🤖 AI Agent**: Ask questions in natural language, get SAP data
- **📊 Dynamic Tool Registry**: Manage SAP tools via REST API (no code changes needed!)
- **� Hot Reload**: Tool changes take effect immediately
- **🔍 Multiple Tools**: Table schema, source code, service items, metadata, and more
- **🏗️ Connection Pooling**: Optimized HTTP connections
- **📝 Structured Logging**: Request/response tracking
- **🎛️ Admin UI**: Optional Streamlit interface for tool management

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Clone and navigate
cd ai-powered-tools

# 2. Create environment file
cp .env.example .env
# Edit .env with your credentials

# 3. Start with Docker Compose
docker-compose up -d

# 4. Check logs
docker-compose logs -f api
```

### Option 2: Python

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Start the server
python3 run_server.py
```

**Endpoints:**
- API: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/docs`
- Admin API: `http://localhost:8000/admin/registry/*`

📖 **Full deployment guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)

## 🔧 Configuration

Create a `.env` file with your credentials:

```env
# Azure Authentication
AZURE_APP_KEY=your_app_key
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret

# Azure OpenAI
AZURE_ENDPOINT=https://chat-ai.cisco.com
AZURE_DEPLOYMENT_NAME=gpt-4.1

# SAP Credentials
SAP_DEFAULT_SYSTEM_ID=D2A
SAP_USERNAME=your_sap_username
SAP_PASSWORD=your_sap_password
```

**Supported SAP Systems:** D2A, DHA, QHA, Q2A, RHA, SHA

## � Usage

### Query the AI Agent

```bash
# Ask in natural language
curl "http://localhost:8000/sap/tools?user_query=Get table schema for MAKT from D2A"
```

### Manage Tools Dynamically (No Code Changes!)

```bash
# List all tools
curl "http://localhost:8000/admin/registry/tools"

# Create a new tool
curl -X POST "http://localhost:8000/admin/registry/tools" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_new_tool",
    "description": "My custom SAP tool",
    "service_config": {
      "service_name": "Z_MY_SERVICE",
      "entity_name": "MyEntity",
      "odata_version": "v4",
      "http_method": "GET"
    },
    "enabled": true
  }'

# Tool is available immediately (no restart needed!)
```

### Optional: Use Streamlit UI

```bash
pip install streamlit
streamlit run ui/tool_registry_admin.py
```

## 🎯 Key Benefits

- ✅ **No deployments** - Add/edit tools via API
- ✅ **Instant updates** - Hot reload without server restart  
- ✅ **Simple queries** - Natural language instead of complex API calls
- ✅ **Automatic backups** - Safe tool modifications
- ✅ **Version tracking** - Every tool change is versioned

## 📁 Project Structure

```
src/
├── routers/            # FastAPI endpoints
│   ├── sap_tools.py   # Main query endpoint
│   └── admin.py       # Tool management API
├── tools/             # Dynamic tool registry
├── services/          # Tool storage & management
├── agents/            # LangGraph AI agent
└── utils/             # HTTP client, logging
```

## 📚 Documentation

- **DYNAMIC_REGISTRY_GUIDE.md** - Complete guide to tool management
- **QUICK_START_DYNAMIC_REGISTRY.md** - Quick reference
- **CLEANUP_COMPLETE.md** - Recent cleanup summary

## 🆘 Support

Create an issue with details about your problem.

---
