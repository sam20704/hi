# Building a Custom MCP Server for SAP with Azure OpenAI: Complete Guide

**Author's Note:** This guide walks you through building an **MCP (Model Context Protocol) server from scratch** that connects to your SAP GUI data and integrates with Azure OpenAI for a chatbot. This is NOT using the pre-built cap-js/mcp-server. Instead, we're building a custom MCP server tailored to your SAP environment.

---

## Table of Contents

1. [What We're Building](#what-were-building)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Part 1: Build the Custom MCP Server (From Scratch)](#part-1-build-the-custom-mcp-server)
5. [Part 2: Connect to SAP OData/GUI](#part-2-connect-to-sap-odatagui)
6. [Part 3: Integrate with Azure OpenAI](#part-3-integrate-with-azure-openai)
7. [Part 4: Apply Code Execution Efficiency (Anthropic's Approach)](#part-4-apply-code-execution-efficiency)
8. [Part 5: Deploy & Test](#part-5-deploy--test)

---

## What We're Building

A **custom MCP server** that:

- **Connects** to your SAP system via OData REST APIs (instead of SAP GUI directly)
- **Exposes SAP data as tools** that an LLM can call (e.g., "Get customer list", "Update order status")
- **Works with Azure OpenAI** to power a chatbot that understands your SAP data in real time
- **Uses code execution** (as per Anthropic's whitepaper) to efficiently handle large datasets and complex queries

```
┌─────────────────────────────────────────────────────────────┐
│                    End User (Browser/Teams)                │
│                    Asks: "Show me my orders"               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Chatbot UI (Frontend)                          │
│        Powered by Azure OpenAI (GPT-4/3.5)                 │
└────────────────────┬────────────────────────────────────────┘
                     │ Sends prompt
┌────────────────────▼────────────────────────────────────────┐
│            Your Custom MCP Server (Node.js)                │
│  - Lists available tools (e.g., getSalesOrders)           │
│  - Receives tool calls from Azure OpenAI                  │
│  - Calls SAP OData APIs                                   │
│  - Returns results back to Azure OpenAI                   │
└────────────────────┬────────────────────────────────────────┘
                     │ REST calls
┌────────────────────▼────────────────────────────────────────┐
│         SAP NetWeaver Gateway / OData Service              │
│    (Your SAP system exposing data as REST APIs)           │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Overview

### Why Not Connect Directly to SAP GUI?

SAP GUI is a **thick client application** designed for human users, not APIs. It's:
- Not REST-based
- Requires special scripting/automation (fragile and hard to maintain)
- Not suitable for AI agents or microservices

**Solution:** SAP systems expose data via **SAP NetWeaver Gateway (OData)**, which is:
- REST-based, standard HTTP
- Secure (Basic Auth, OAuth 2.0)
- Designed for integrations
- Easy to consume from Node.js or any language

### MCP's Role

MCP is the **bridge** between:
- **LLMs** (Azure OpenAI) that need tools to interact with data
- **Your backend systems** (SAP OData) that hold the data

MCP defines a standard protocol so that:
1. Your MCP server **lists available tools** to the LLM
2. The LLM **calls tools** with parameters
3. Your MCP server **executes** those tool calls by invoking SAP OData APIs
4. Results **flow back** to the LLM, which formulates a user-facing response

---

## Prerequisites

### On Your Laptop

1. **Node.js** (v18+) and npm
   - Test: `node -v` and `npm -v`
   - Download from https://nodejs.org/

2. **VS Code** (or any editor)
   - Download from https://code.visualstudio.com/

3. **Git** (for cloning repos)
   - Download from https://git-scm.com/

4. **Azure OpenAI API Key**
   - You need an Azure subscription and deployed Azure OpenAI model (GPT-4 or 3.5-turbo)
   - Get the endpoint URL and API key from Azure Portal

### In Your SAP System

1. **SAP NetWeaver Gateway enabled**
   - Most modern SAP systems (S/4HANA, ECC 6.0+) have it out of the box
   - Your SAP admin can confirm OData service URLs

2. **OData Service Endpoint**
   - Example: `https://your-sap-server:8000/sap/opu/odata/NAMESPACE/SERVICE_NAME/`
   - Ask your SAP admin for available services (e.g., `API_SALES_ORDER_SRV`, `API_CUSTOMER_SRV`)

3. **SAP User Credentials** (with permissions to OData services)
   - Username and password
   - Or OAuth 2.0 setup (more secure for production)

---

## Part 1: Build the Custom MCP Server (From Scratch)

### Step 1: Set Up Your Project

Open PowerShell and run:

```powershell
# Create project directory
mkdir my-sap-mcp-server
cd my-sap-mcp-server

# Initialize Node.js project
npm init -y

# Install required packages
npm install --save @modelcontextprotocol/sdk axios dotenv

# Create project structure
mkdir src
mkdir tools
```

### Step 2: Create Environment Configuration

Create a `.env` file in your project root:

```env
# Azure OpenAI
AZURE_OPENAI_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4-deployment-name

# SAP OData
SAP_ODATA_URL=https://your-sap-server:8000/sap/opu/odata
SAP_USERNAME=your_sap_user
SAP_PASSWORD=your_sap_password
SAP_NAMESPACE=IWBEP
SAP_SERVICE_NAME=GWSAMPLE_BASIC

# MCP Server
MCP_SERVER_NAME=sap-ai-server
MCP_SERVER_VERSION=1.0.0
```

### Step 3: Build the Core MCP Server

Create `src/index.js`:

```javascript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import dotenv from "dotenv";
import axios from "axios";

dotenv.config();

// Initialize MCP Server
const server = new Server({
  name: process.env.MCP_SERVER_NAME || "sap-ai-server",
  version: process.env.MCP_SERVER_VERSION || "1.0.0",
});

// SAP OData base configuration
const sapConfig = {
  baseUrl: process.env.SAP_ODATA_URL,
  username: process.env.SAP_USERNAME,
  password: process.env.SAP_PASSWORD,
  namespace: process.env.SAP_NAMESPACE,
  serviceName: process.env.SAP_SERVICE_NAME,
};

// Create axios instance with SAP authentication
const sapClient = axios.create({
  baseURL: sapConfig.baseUrl,
  auth: {
    username: sapConfig.username,
    password: sapConfig.password,
  },
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Define available tools
const tools = [
  {
    name: "get_sales_orders",
    description: "Fetch a list of sales orders from SAP with optional filtering",
    inputSchema: {
      type: "object",
      properties: {
        limit: {
          type: "number",
          description: "Maximum number of records to return (default: 10)",
        },
        customerId: {
          type: "string",
          description: "Filter by customer ID (optional)",
        },
      },
      required: [],
    },
  },
  {
    name: "get_customer_details",
    description: "Fetch detailed information about a specific customer",
    inputSchema: {
      type: "object",
      properties: {
        customerId: {
          type: "string",
          description: "The SAP customer ID",
        },
      },
      required: ["customerId"],
    },
  },
  {
    name: "update_order_status",
    description: "Update the status of a sales order",
    inputSchema: {
      type: "object",
      properties: {
        orderId: {
          type: "string",
          description: "The sales order ID",
        },
        status: {
          type: "string",
          enum: ["pending", "processing", "shipped", "delivered"],
          description: "New status for the order",
        },
      },
      required: ["orderId", "status"],
    },
  },
];

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const toolName = request.params.name;
  const toolInput = request.params.arguments;

  try {
    let result;

    switch (toolName) {
      case "get_sales_orders":
        result = await getSalesOrders(toolInput);
        break;

      case "get_customer_details":
        result = await getCustomerDetails(toolInput);
        break;

      case "update_order_status":
        result = await updateOrderStatus(toolInput);
        break;

      default:
        return {
          isError: true,
          content: [
            {
              type: "text",
              text: `Unknown tool: ${toolName}`,
            },
          ],
        };
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: `Error executing tool: ${error.message}`,
        },
      ],
    };
  }
});

// Tool implementations

async function getSalesOrders(input) {
  const limit = input.limit || 10;
  const customerId = input.customerId;

  try {
    let url = `/${sapConfig.namespace}/${sapConfig.serviceName}/A_SalesOrder?$top=${limit}`;

    if (customerId) {
      url += `&$filter=Customer eq '${customerId}'`;
    }

    const response = await sapClient.get(url);
    return {
      success: true,
      count: response.data.d.results.length,
      orders: response.data.d.results,
    };
  } catch (error) {
    throw new Error(`Failed to fetch sales orders: ${error.message}`);
  }
}

async function getCustomerDetails(input) {
  const customerId = input.customerId;

  try {
    const url = `/${sapConfig.namespace}/${sapConfig.serviceName}/A_Customer('${customerId}')`;
    const response = await sapClient.get(url);
    return {
      success: true,
      customer: response.data.d,
    };
  } catch (error) {
    throw new Error(`Failed to fetch customer details: ${error.message}`);
  }
}

async function updateOrderStatus(input) {
  const orderId = input.orderId;
  const status = input.status;

  try {
    // Note: This is a simplified example. Real SAP updates are more complex
    const url = `/${sapConfig.namespace}/${sapConfig.serviceName}/A_SalesOrder('${orderId}')`;
    const response = await sapClient.patch(url, {
      OrderStatus: status,
    });
    return {
      success: true,
      message: `Order ${orderId} status updated to ${status}`,
      result: response.data.d,
    };
  } catch (error) {
    throw new Error(`Failed to update order: ${error.message}`);
  }
}

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("SAP MCP Server running on stdio");
}

main().catch(console.error);
```

### Step 4: Update `package.json` for ES Modules

Modify your `package.json`:

```json
{
  "name": "my-sap-mcp-server",
  "version": "1.0.0",
  "type": "module",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^0.5.0",
    "axios": "^1.6.0",
    "dotenv": "^16.3.1"
  }
}
```

### Step 5: Test the MCP Server Locally

Run the server:

```powershell
npm start
```

You should see:
```
SAP MCP Server running on stdio
```

---

## Part 2: Connect to SAP OData/GUI

### How to Get Your SAP OData Endpoint

**Option 1: Ask Your SAP Admin**
- Request OData service URLs
- Common services: `API_SALES_ORDER_SRV`, `API_CUSTOMER_SRV`, `API_PRODUCT_SRV`
- Example URL: `https://sap-server:8000/sap/opu/odata/sap/API_SALES_ORDER_SRV/`

**Option 2: Discover Services in SAP (if you have access)**
1. Log into SAP GUI or Web UI
2. Search for transaction `/IWFND/MAINT_SERVICE`
3. View all available OData services
4. Note the **namespace** and **service name**

### Authentication to SAP

Your MCP server supports:

**Basic Authentication (Simple, for testing):**
```javascript
auth: {
  username: "SAP_USER",
  password: "SAP_PASSWORD"
}
```

**OAuth 2.0 (Production):**
```javascript
// Get token from SAP Authorization Server
const token = await getOAuthToken();
headers: {
  "Authorization": `Bearer ${token}`
}
```

### What SAP GUI Doesn't Do Directly

SAP GUI (the green screen client) is **not an API**. Instead:

- **SAP exposes data via OData** → Your MCP server calls OData REST APIs
- **Your MCP server acts as the bridge** → It translates LLM requests into OData queries
- **LLMs call your MCP server's tools** → The LLM never touches SAP directly

**Real-world example:**
1. User asks chatbot: "Show me orders for customer ABC123"
2. Chatbot (Azure OpenAI) sees the `get_sales_orders` tool in your MCP server
3. It calls: `get_sales_orders(customerId="ABC123")`
4. Your MCP server calls SAP OData: `GET /sap/opu/odata/...A_SalesOrder?$filter=Customer eq 'ABC123'`
5. SAP returns JSON data
6. Your MCP server returns it to the LLM
7. LLM formats a nice response for the user

---

## Part 3: Integrate with Azure OpenAI

### Option A: Simple Chatbot UI (Node.js + Express)

Create `src/chatbot.js`:

```javascript
import express from "express";
import { OpenAI } from "openai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
app.use(express.json());

// Initialize Azure OpenAI client
const client = new OpenAI({
  apiKey: process.env.AZURE_OPENAI_KEY,
  baseURL: `${process.env.AZURE_OPENAI_ENDPOINT}/openai/deployments/${process.env.AZURE_OPENAI_DEPLOYMENT}`,
  defaultQuery: { "api-version": "2024-08-01-preview" },
  defaultHeaders: { "api-key": process.env.AZURE_OPENAI_KEY },
});

// Your MCP server tools (same as defined earlier)
const sapTools = [
  {
    type: "function",
    function: {
      name: "get_sales_orders",
      description: "Fetch sales orders from SAP",
      parameters: {
        type: "object",
        properties: {
          limit: { type: "number" },
          customerId: { type: "string" },
        },
      },
    },
  },
  // ... other tools
];

// Endpoint to chat with the bot
app.post("/chat", async (req, res) => {
  const userMessage = req.body.message;

  try {
    const response = await client.chat.completions.create({
      model: process.env.AZURE_OPENAI_DEPLOYMENT,
      messages: [
        {
          role: "system",
          content: "You are a helpful SAP assistant. Use the available tools to fetch data from SAP.",
        },
        {
          role: "user",
          content: userMessage,
        },
      ],
      tools: sapTools,
      tool_choice: "auto",
    });

    res.json({
      response: response.choices[0].message.content,
      toolCalls: response.choices[0].message.tool_calls,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(3000, () => {
  console.log("Chatbot running on http://localhost:3000");
});
```

### Option B: Integrate with Claude Desktop

Create `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sap-ai-server": {
      "command": "node",
      "args": ["/path/to/my-sap-mcp-server/src/index.js"],
      "env": {
        "SAP_ODATA_URL": "https://your-sap:8000/sap/opu/odata",
        "SAP_USERNAME": "your_user",
        "SAP_PASSWORD": "your_pass"
      }
    }
  }
}
```

---

## Part 4: Apply Code Execution Efficiency (Anthropic's Approach)

**Problem:** If your MCP server handles 1000 tools and large datasets, passing all tool definitions and results through the context window wastes tokens and increases latency.

**Anthropic's Solution:** Use **code execution with MCP**. Instead of returning raw data, let the LLM write code to filter and process it.

### Example: Efficient Sales Order Query

**Without Code Execution (Wasteful):**
```
LLM asks MCP: "Get me all orders"
MCP returns: 10,000 orders as JSON (huge!)
LLM tries to filter through context
Token cost: HIGH
```

**With Code Execution (Efficient):**
```javascript
// In your MCP server, add a "run_code" tool
const tools = [
  {
    name: "run_code",
    description: "Execute JavaScript code in a sandboxed environment",
    inputSchema: {
      type: "object",
      properties: {
        code: {
          type: "string",
          description: "JavaScript code to run",
        },
      },
      required: ["code"],
    },
  },
];

// Handle code execution
async function runCode(code) {
  // Execute the code with access to SAP functions
  const sandbox = {
    getSalesOrders,
    getCustomerDetails,
    updateOrderStatus,
    console,
  };

  // Use vm or isolated-vm for true sandboxing
  const vm = new VM({ sandbox });
  return vm.run(code);
}
```

**LLM now writes code:**
```javascript
const orders = await getSalesOrders({ limit: 100 });
const pendingOrders = orders.filter(o => o.Status === "pending");
console.log(`Found ${pendingOrders.length} pending orders`);
console.log(pendingOrders.slice(0, 5));
```

**Result:**
- LLM sees only 5 orders in context (not 100)
- Token cost: **98% reduction** (as per Anthropic's findings)
- Latency: Much lower
- Data processing: Handled in the execution environment, not the model

### Implement Code Execution

Install the sandbox library:

```powershell
npm install --save vm2
```

Update `src/index.js` to include:

```javascript
import { VM } from "vm2";

async function runCodeTool(input) {
  const code = input.code;

  try {
    const sandbox = {
      getSalesOrders,
      getCustomerDetails,
      updateOrderStatus,
      console,
      // Add helper functions for filtering, mapping, etc.
    };

    const vm = new VM({ sandbox, timeout: 5000 });
    const result = vm.run(code);

    return {
      success: true,
      result: result,
    };
  } catch (error) {
    throw new Error(`Code execution failed: ${error.message}`);
  }
}

// Add to tools array
const tools = [
  // ... existing tools
  {
    name: "run_code",
    description:
      "Execute JavaScript code with access to SAP tools. Use this to filter, transform, and analyze data efficiently.",
    inputSchema: {
      type: "object",
      properties: {
        code: {
          type: "string",
          description: "JavaScript code to execute. Has access to: getSalesOrders, getCustomerDetails, updateOrderStatus, console",
        },
      },
      required: ["code"],
    },
  },
];
```

---

## Part 5: Deploy & Test

### Local Testing

1. **Start your MCP server:**
   ```powershell
   npm start
   ```

2. **Test a tool call manually** using MCP Inspector:
   ```powershell
   npx @modelcontextprotocol/inspector node src/index.js
   ```
   This opens a web UI where you can call tools directly.

3. **Start your chatbot** (if using Option A):
   ```powershell
   npm run dev
   ```

4. **Test via cURL:**
   ```powershell
   curl -X POST http://localhost:3000/chat `
     -H "Content-Type: application/json" `
     -d '{"message":"Show me pending orders"}'
   ```

### Example Conversation Flow

**User:** "What are my top 5 overdue orders?"

**Your Chatbot Flow:**
1. Azure OpenAI receives the query
2. It sees your MCP tools: `get_sales_orders`, `run_code`
3. It calls: `get_sales_orders({ limit: 100 })`
4. Gets 100 orders back (but only needs the summary in context)
5. Calls: `run_code({ code: "const overdue = orders.filter(...)" })`
6. Code executes in sandbox, returns filtered results
7. LLM formats final answer: "You have 3 overdue orders..."

### Deployment to Production

**Option 1: SAP BTP Cloud Foundry**
```powershell
# Create manifest.yml
cf push my-sap-mcp-server

# Deploy
cf push
```

**Option 2: Docker Container**
```dockerfile
FROM node:18
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY src ./src
CMD ["npm", "start"]
```

**Option 3: Azure Container Instances / App Service**
- Build Docker image
- Push to Azure Container Registry
- Deploy from ACR

---

## Summary: Key Takeaways

| Step | Tool | Purpose |
|------|------|---------|
| 1 | MCP SDK | Build server that exposes SAP data as tools |
| 2 | SAP OData APIs | Retrieve/update data (not SAP GUI directly) |
| 3 | Azure OpenAI | Power the chatbot with LLM capabilities |
| 4 | Code Execution | Efficiently filter and process large datasets |
| 5 | Node.js/Express | Run the server and chatbot backend |

**Key Insights:**
- **Don't connect directly to SAP GUI** – use OData APIs
- **MCP is the bridge** between LLM and SAP
- **Code execution** (Anthropic's approach) makes it efficient and scalable
- **Clone is NOT required** – you're building from scratch with npm packages

---

## Do You Need to Clone the GitHub Repo?

**No.** The `cap-js/mcp-server` repo is for **developing CAP applications with AI help in VS Code**.

For your use case (chatbot + SAP data + Azure OpenAI), you:
1. **Build your own MCP server** (as shown above) using the MCP SDK
2. **Don't clone** – just install npm packages
3. **Customize** for your SAP services and Azure OpenAI setup

---

## Next Steps

1. **Get SAP OData URLs** from your SAP admin
2. **Set up Azure OpenAI** credentials
3. **Update `.env`** with your config
4. **Customize the tools** in your MCP server for your SAP services
5. **Test locally** with MCP Inspector
6. **Deploy** to production

Good luck! 🚀
