---
name: weaviate-setup
description: Interactive onboarding for the Weaviate knowledge store. Guides users through choosing a deployment type (Cloud, Local Docker, or Custom), setting environment variables, and verifying the connection. Activates when users want to set up or configure Weaviate for persistent knowledge storage.
---

# Weaviate Knowledge Store Setup

You are guiding a user through setting up Weaviate as the persistent knowledge store for the video-research MCP server. All 13 existing tools automatically write results to Weaviate when configured. 4 knowledge query tools (`knowledge_search`, `knowledge_related`, `knowledge_stats`, `knowledge_ingest`) enable semantic search across accumulated research.

## Setup Flow

Follow these steps IN ORDER. Use `AskUserQuestion` for each decision point.

### Step 1: Deployment Type

Ask the user which Weaviate deployment they want to use:

```
AskUserQuestion:
  question: "Which Weaviate deployment will you use?"
  header: "Deployment"
  options:
    - label: "Weaviate Cloud (Recommended)"
      description: "Managed cloud service at console.weaviate.cloud — free tier available, no infrastructure to manage"
    - label: "Local Docker"
      description: "Run Weaviate locally via Docker on port 8080 — full control, no network latency"
    - label: "Custom/Self-hosted"
      description: "Your own Weaviate deployment at a custom URL"
```

### Step 2: Collect Credentials (based on choice)

**If Weaviate Cloud:**
- Tell the user to go to https://console.weaviate.cloud, create a free cluster, then copy the cluster URL and API key
- Ask them to provide both values

**If Local Docker:**
- Provide the docker-compose snippet:
```yaml
services:
  weaviate:
    image: cr.weaviate.io/semitechnologies/weaviate:1.28.4
    ports:
      - "8080:8080"
      - "50051:50051"
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
      PERSISTENCE_DATA_PATH: "/var/lib/weaviate"
      DEFAULT_VECTORIZER_MODULE: text2vec-transformers
      ENABLE_MODULES: text2vec-transformers
      TRANSFORMERS_INFERENCE_API: http://t2v-transformers:8080
  t2v-transformers:
    image: cr.weaviate.io/semitechnologies/transformers-inference:sentence-transformers-all-MiniLM-L6-v2
    environment:
      ENABLE_CUDA: 0
```
- The URL will be `http://localhost:8080`
- No API key needed for local

**If Custom:**
- Ask for the full URL (including port)
- Ask if authentication is required (API key)

### Step 3: Configure Environment

Once you have the URL (and optionally API key), tell the user to set the environment variables. There are two ways:

**Option A — In `.mcp.json` (recommended for plugin users):**
The MCP server config in `~/.claude/.mcp.json` or `.mcp.json` should include:
```json
{
  "mcpServers": {
    "video-research": {
      "command": "uvx",
      "args": ["video-research-mcp"],
      "env": {
        "GEMINI_API_KEY": "${GEMINI_API_KEY}",
        "WEAVIATE_URL": "<their-url>",
        "WEAVIATE_API_KEY": "<their-key-if-any>"
      }
    }
  }
}
```

**Option B — Shell environment:**
```bash
export WEAVIATE_URL="<their-url>"
export WEAVIATE_API_KEY="<their-key-if-any>"  # only for Cloud/authenticated deployments
```

### Step 4: Verify Connection

After the user has configured the environment, tell them to restart Claude Code (or the MCP server) and test with:

```
knowledge_stats()
```

This should return counts for all 7 collections (all 0 initially). If it returns an error, troubleshoot based on the error category:

| Error | Fix |
|-------|-----|
| `WEAVIATE_CONNECTION` | Check URL is reachable, Docker is running, firewall allows the port |
| `WEAVIATE_SCHEMA` | Collections couldn't be created — check Weaviate version (need >= 1.25) |
| `Weaviate not configured` | `WEAVIATE_URL` env var is not set or server wasn't restarted |

### Step 5: Confirm Working

Once `knowledge_stats` returns successfully, tell the user:

1. All 13 existing tools now automatically store results to Weaviate
2. Use `knowledge_search(query="...")` to find past results semantically
3. Use `knowledge_related(object_id="...", collection="...")` to find similar items
4. Use `knowledge_stats()` to see how much knowledge has accumulated
5. The file cache continues to work alongside Weaviate — dual persistence

## 7 Collections Created Automatically

| Collection | Populated by | Searchable fields |
|---|---|---|
| `ResearchFindings` | `research_deep`, `research_assess_evidence` | claim, reasoning, executive_summary |
| `VideoAnalyses` | `video_analyze`, `video_batch_analyze` | title, summary, key_points, instruction |
| `ContentAnalyses` | `content_analyze` | title, summary, key_points, entities |
| `VideoMetadata` | `video_metadata` | title, description, tags |
| `SessionTranscripts` | `video_continue_session` | turn_prompt, turn_response, video_title |
| `WebSearchResults` | `web_search` | query, response |
| `ResearchPlans` | `research_plan` | topic, task_decomposition |

## Supported Deployment URLs

| Type | Example URL | API Key |
|------|------------|---------|
| Weaviate Cloud | `https://my-cluster-abc123.weaviate.network` | Required |
| Local Docker | `http://localhost:8080` | Not needed |
| Custom | `https://weaviate.mycompany.com:8080` | Depends |

## Graceful Degradation

If `WEAVIATE_URL` is not set, the server works identically to before — no errors, no changes. All store operations silently return `None`. Knowledge tools return empty results with a hint to configure Weaviate.
