# SAP API Onboarding Framework 🚀

A no-code framework for onboarding SAP OData APIs and making them accessible to LLMs through natural language queries.

---

## �� What is This?

An intelligent system that allows you to:
1. **Onboard SAP APIs** dynamically without writing code
2. **Query SAP systems** using natural language (e.g., "Get subscription details for ID XYZ")
3. **Manage APIs** through a simple web interface

**Key Feature:** Add/edit/remove SAP APIs instantly - no code changes or server restarts required!

---

## 🚀 Quick Start with Docker

### Step 1: Clone Repository

```bash
git clone https://github.com/vaibhavgoel-github-1986/sap-api-onboarding-framework.git
cd sap-api-onboarding-framework
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

### Step 3: Build & Start

```bash
# Build all containers
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

---

## 🌐 Access Applications

| Service | URL | Purpose |
|---------|-----|---------|
| **Chatbot** | http://localhost:8501 | Query SAP using natural language |
| **Admin Portal** | http://localhost:8502 | Onboard & manage SAP APIs |
| **API** | http://localhost:8000 | Backend API |
| **API Docs** | http://localhost:8000/docs | Swagger documentation |

---

## 📋 Environment Variables

Required in `.env` file:

```env
# Azure OpenAI
AZURE_ENDPOINT=https://your-endpoint.com
AZURE_DEPLOYMENT_NAME=gpt-4
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_secret

# SAP Credentials
SAP_USERNAME=your_sap_user
SAP_PASSWORD=your_sap_password
SAP_DEFAULT_SYSTEM_ID=D2A
```

---

## 🛠️ Common Commands

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down
```

---

**Built with:** FastAPI • LangGraph • Streamlit • Azure OpenAI
