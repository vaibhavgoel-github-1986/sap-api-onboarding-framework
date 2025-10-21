# SAP API Onboarding Framework 🚀# SAP Tools API 🚀



A no-code framework for onboarding SAP OData APIs and making them accessible to LLMs through natural language queries.An intelligent FastAPI service that uses AI agents to query SAP systems through natural language.



---## ✨ Features



## 🎯 What is This?- **🤖 AI Agent**: Ask questions in natural language, get SAP data

- **📊 Dynamic Tool Registry**: Manage SAP tools via REST API (no code changes needed!)

An intelligent system that allows you to:- **� Hot Reload**: Tool changes take effect immediately

1. **Onboard SAP APIs** dynamically without writing code- **🔍 Multiple Tools**: Table schema, source code, service items, metadata, and more

2. **Query SAP systems** using natural language (e.g., "Get subscription details for ID XYZ")- **🏗️ Connection Pooling**: Optimized HTTP connections

3. **Manage APIs** through a simple web interface- **📝 Structured Logging**: Request/response tracking

- **🎛️ Admin UI**: Optional Streamlit interface for tool management

**Key Feature:** Add/edit/remove SAP APIs instantly - no code changes or server restarts required!

## 🚀 Quick Start

---

### Option 1: Docker (Recommended)

## 🏗️ Architecture & Design

```bash

### High-Level Flow# 1. Clone and navigate df

cd ai-powered-tools

```

User Query (Natural Language)# 2. Create environment file

        ↓cp .env.example .env

   Chatbot UI (Streamlit)# Edit .env with your credentials

        ↓

   FastAPI Backend# 3. Start with Docker Compose

        ↓docker-compose up -d

   LangGraph AI Agent

        ↓# 4. Check logs

   Dynamic Tool Registry (JSON-based)docker-compose logs -f api

        ↓```

   SAP OData API Client

        ↓### Option 2: Python

   SAP Systems (D2A, QHA, RHA, etc.)

``````bash

# Install dependencies

### Core Componentspip install -r requirements.txt



1. **Dynamic Tool Registry**# Set up environment

   - JSON-based storage (`tool_registry.json`)cp .env.example .env

   - No code deployment needed to add new APIs# Edit .env with your credentials

   - Hot-reload: changes take effect immediately

   - Each tool = 1 SAP OData endpoint# Start the server

python3 run_server.py

2. **LangGraph AI Agent**```

   - Processes natural language queries

   - Selects appropriate tool from registry**Endpoints:**

   - Calls SAP API with correct parameters- API: `http://localhost:8000`

   - Returns formatted results- Swagger Docs: `http://localhost:8000/docs`

- Admin API: `http://localhost:8000/admin/registry/*`

3. **Three User Interfaces**

   - **Chatbot UI** (`:8501`) - End users ask questions📖 **Full deployment guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)

   - **Admin UI** (`:8502`) - Onboard & manage APIs

   - **API** (`:8000`) - Programmatic access## 🔧 Configuration



4. **SAP API Client**Create a `.env` file with your credentials:

   - Generic OData v2/v4 connector

   - Connection pooling for performance```env

   - Handles authentication & error handling# Azure Authentication

AZURE_APP_KEY=your_app_key

---AZURE_CLIENT_ID=your_client_id

AZURE_CLIENT_SECRET=your_client_secret

## 🚀 Quick Start

# Azure OpenAI

### PrerequisitesAZURE_ENDPOINT=https://chat-ai.cisco.com

- Docker & Docker ComposeAZURE_DEPLOYMENT_NAME=gpt-4.1

- SAP system credentials

- Azure OpenAI access (for LLM)# SAP Credentials

SAP_DEFAULT_SYSTEM_ID=D2A

### Step 1: Clone & ConfigureSAP_USERNAME=your_sap_username

SAP_PASSWORD=your_sap_password

```bash```

# Clone repository

git clone https://github.com/vaibhavgoel-github-1986/sap-api-onboarding-framework.git**Supported SAP Systems:** D2A, DHA, QHA, Q2A, RHA, SHA

cd sap-api-onboarding-framework

## � Usage

# Copy environment template

cp .env.example .env### Query the AI Agent



# Edit .env with your credentials```bash

nano .env# Ask in natural language

```curl "http://localhost:8000/sap/tools?user_query=Get table schema for MAKT from D2A"

```

### Step 2: Build Docker Images

### Manage Tools Dynamically (No Code Changes!)

```bash

# Build all three containers```bash

docker-compose build# List all tools

```curl "http://localhost:8000/admin/registry/tools"



This creates:# Create a new tool

- `ai-powered-tools-api` - FastAPI backendcurl -X POST "http://localhost:8000/admin/registry/tools" \

- `ai-powered-tools-ui` - Chatbot interface  -H "Content-Type: application/json" \

- `ai-powered-tools-admin-ui` - Admin portal  -d '{

    "name": "my_new_tool",

### Step 3: Start Services    "description": "My custom SAP tool",

    "service_config": {

```bash      "service_name": "Z_MY_SERVICE",

# Start all services      "entity_name": "MyEntity",

docker-compose up -d      "odata_version": "v4",

      "http_method": "GET"

# Check status    },

docker-compose ps    "enabled": true

  }'

# View logs

docker-compose logs -f# Tool is available immediately (no restart needed!)

``````



### Step 4: Access Applications### Optional: Use Streamlit UI



| Service | URL | Purpose |```bash

|---------|-----|---------|pip install streamlit

| **Chatbot** | http://localhost:8501 | Query SAP using natural language |streamlit run ui/tool_registry_admin.py

| **Admin Portal** | http://localhost:8502 | Onboard & manage APIs |```

| **API Docs** | http://localhost:8000/docs | Swagger documentation |

## 🎯 Key Benefits

---

- ✅ **No deployments** - Add/edit tools via API

## 📋 Environment Configuration- ✅ **Instant updates** - Hot reload without server restart  

- ✅ **Simple queries** - Natural language instead of complex API calls

Required variables in `.env`:- ✅ **Automatic backups** - Safe tool modifications

- ✅ **Version tracking** - Every tool change is versioned

```env

# Azure OpenAI (for LLM)## 📁 Project Structure

AZURE_ENDPOINT=https://your-endpoint.com

AZURE_DEPLOYMENT_NAME=gpt-4```

AZURE_CLIENT_ID=your_client_idsrc/

AZURE_CLIENT_SECRET=your_secret├── routers/            # FastAPI endpoints

│   ├── sap_tools.py   # Main query endpoint

# SAP Credentials│   └── admin.py       # Tool management API

SAP_USERNAME=your_sap_user├── tools/             # Dynamic tool registry

SAP_PASSWORD=your_sap_password├── services/          # Tool storage & management

SAP_DEFAULT_SYSTEM_ID=D2A├── agents/            # LangGraph AI agent

└── utils/             # HTTP client, logging

# Optional: Logging```

LOG_LEVEL=INFO

```## 📚 Documentation



---- **DYNAMIC_REGISTRY_GUIDE.md** - Complete guide to tool management

- **QUICK_START_DYNAMIC_REGISTRY.md** - Quick reference

## 💡 How to Use- **CLEANUP_COMPLETE.md** - Recent cleanup summary



### For End Users (Chatbot)## 🆘 Support



1. Go to http://localhost:8501Create an issue with details about your problem.

2. Type natural language questions:

   - "Get subscription details for INTVG1232 from D2A"---

   - "Show table schema for MAKT"
   - "Get metadata for ZSD_PRODUCTS service"
3. View formatted results

### For Admins (Onboard New APIs)

1. Go to http://localhost:8502
2. Click **"Onboard SAP API"** tab
3. Fill in the form:
   - Tool name (e.g., `get_subscription_data`)
   - Description (what it does)
   - SAP service details (service name, entity, OData version)
4. Click **"Onboard API"**
5. ✅ API is immediately available to the LLM - no restart needed!

### Editing Existing APIs

1. Go to **"Tool Details"** tab
2. Select a tool
3. Expand **"Edit Tool JSON"**
4. Modify the JSON configuration
5. Click **"Update Tool"**
6. Changes take effect instantly

---

## 🔄 Workflow Example

**Scenario:** User wants subscription data from SAP

1. **User asks:** "Get details for subscription INTVG1232 from D2A"

2. **LLM analyzes query:**
   - Extracts: subscription ID, system ID
   - Selects tool: `get_subs_data` (from registry)

3. **Agent calls SAP:**
   - Service: `ZSD_SERVICE_API`
   - Entity: `ServiceModel`
   - Filter: `SubscriptionReferenceId eq 'INTVG1232'`

4. **SAP responds** with subscription data

5. **LLM formats result** and presents to user

---

## 📁 Project Structure

```
sap-api-onboarding-framework/
├── docker-compose.yml          # Multi-container setup
├── Dockerfile                  # API container
├── Dockerfile.admin            # Admin UI container
├── Dockerfile.streamlit        # Chatbot container
├── requirements.txt            # Python dependencies
├── tool_registry.json          # Dynamic API registry (auto-created)
├── src/
│   ├── main.py                 # FastAPI application
│   ├── routers/
│   │   ├── sap_tools.py        # Query endpoint
│   │   └── admin.py            # API management endpoints
│   ├── agents/
│   │   └── sap_agent.py        # LangGraph AI agent
│   ├── tools/
│   │   ├── dynamic_registry.py # Tool registry manager
│   │   ├── get_metadata.py     # Metadata fetcher
│   │   └── call_sap_api.py     # Generic API caller
│   └── utils/
│       └── sap_api_client.py   # SAP OData client
└── ui/
    ├── chatbot.py              # End-user interface
    └── tool_registry_admin.py  # Admin interface
```

---

## 🛠️ Common Commands

```bash
# Rebuild after code changes
docker-compose build

# Restart specific service
docker-compose restart api

# View logs for specific service
docker-compose logs -f ui

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Check container status
docker ps
```

---

## 🎯 Key Benefits

✅ **No-Code Onboarding** - Add APIs through UI, not code  
✅ **Instant Updates** - Changes take effect without restart  
✅ **Natural Language** - Non-technical users can query SAP  
✅ **Scalable** - Easy to add new SAP services  
✅ **Version Control** - Tool registry tracked in Git  

---

## 📞 Support

For issues or questions, create a GitHub issue with:
- What you were trying to do
- Error messages (if any)
- Relevant logs from `docker-compose logs`

---

**Built with:** FastAPI • LangGraph • Streamlit • Azure OpenAI
