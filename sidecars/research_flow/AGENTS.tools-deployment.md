# CrewAI Tools, Deployment, And Environment Reference

Companion reference for [AGENTS.md](AGENTS.md). Follow the freshness checks in the root file before changing CrewAI tools, deployment, or environment behavior.

## Custom Tools

### Using BaseTool

```python
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    """Input schema for search tool."""
    query: str = Field(..., description="Search query string")

class CustomSearchTool(BaseTool):
    name: str = "custom_search"
    description: str = "Searches a custom knowledge base for relevant information."
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str) -> str:
        # Implementation
        return f"Results for: {query}"
```

### Using @tool Decorator

```python
from crewai.tools import tool

@tool("Calculator")
def calculator(expression: str) -> str:
    """Evaluates a mathematical expression and returns the result."""
    return str(eval(expression))
```

### Built-in Tools (install with `uv add crewai-tools`)

Web/Search: SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool, EXASearchTool, FirecrawlSearchTool
Documents: FileReadTool, DirectoryReadTool, PDFSearchTool, DOCXSearchTool, CSVSearchTool, JSONSearchTool, XMLSearchTool, MDXSearchTool
Code: CodeInterpreterTool, CodeDocsSearchTool, GithubSearchTool
Media: DALL-E Tool, YoutubeChannelSearchTool, YoutubeVideoSearchTool
Other: RagTool, ApifyActorsTool, ComposioTool, LlamaIndexTool

Always check <https://docs.crewai.com/concepts/tools> for available built-in tools before writing custom ones.

---

## Memory System

Enable with `memory=True` on the Crew:

```python
crew = Crew(agents=..., tasks=..., memory=True)
```

Four memory types work together automatically:

- **Short-Term** (ChromaDB + RAG): Recent interactions during current execution
- **Long-Term** (SQLite): Persists insights across sessions
- **Entity** (RAG): Tracks people, places, concepts
- **Contextual**: Integrates all types for coherent responses

### Custom Embedding Provider

```python
crew = Crew(
    memory=True,
    embedder={
        "provider": "ollama",
        "config": {"model": "mxbai-embed-large"},
    },
)
```

Supported providers: OpenAI (default), Ollama, Google AI, Azure OpenAI, Cohere, VoyageAI, Bedrock, Hugging Face.

---

## Knowledge System

```python
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource

# String source
string_source = StringKnowledgeSource(content="Domain knowledge here...")

# PDF source
pdf_source = PDFKnowledgeSource(file_paths=["docs/manual.pdf"])

# Agent-level knowledge
agent = Agent(..., knowledge_sources=[string_source])

# Crew-level knowledge (shared across all agents)
crew = Crew(..., knowledge_sources=[pdf_source])
```

Supported sources: strings, text files, PDFs, CSV, Excel, JSON, URLs (via CrewDoclingSource).

---

## Agent Collaboration

Enable delegation with `allow_delegation=True`:

```python
agent = Agent(
    role="Project Manager",
    allow_delegation=True,  # Can delegate to and ask other agents
    ...
)
```

- **Delegation tool**: Assign sub-tasks to teammates with relevant expertise
- **Ask question tool**: Query colleagues for specific information
- Set `allow_delegation=False` on specialists to prevent circular delegation

---

## Event Listeners

```python
from crewai.events import BaseEventListener, CrewKickoffStartedEvent

class MyListener(BaseEventListener):
    def __init__(self):
        super().__init__()

    def setup_listeners(self, crewai_event_bus):
        @crewai_event_bus.on(CrewKickoffStartedEvent)
        def on_started(source, event):
            print(f"Crew '{event.crew_name}' started")
```

Event categories: Crew lifecycle, Agent execution, Task management, Tool usage, Knowledge retrieval, LLM calls, Memory operations, Flow execution, Safety guardrails.

---

## Deployment to CrewAI AMP

### Prerequisites

- Crew or Flow runs successfully locally
- Code is in a GitHub repository
- `pyproject.toml` has `[tool.crewai]` with correct type (`"crew"` or `"flow"`)
- `uv.lock` is committed (generate with `uv lock`)

### CLI Deployment

```bash
# Authenticate
crewai login

# Create deployment (auto-detects repo, transfers .env vars securely)
crewai deploy create

# Monitor (first deploy takes 10-15 min)
crewai deploy status
crewai deploy logs

# Manage deployments
crewai deploy list              # List all deployments
crewai deploy push              # Push code updates
crewai deploy remove <id>       # Delete deployment
```

### Web Interface Deployment

1. Push code to GitHub
2. Log into <https://app.crewai.com>
3. Connect GitHub and select repository
4. Configure environment variables (KEY=VALUE, one per line)
5. Click Deploy and monitor via dashboard

### CI/CD API Deployment

Get a Personal Access Token from app.crewai.com → Settings → Account → Personal Access Token.
Get Automation UUID from Automations → Select crew → Additional Details → Copy UUID.

```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_PERSONAL_ACCESS_TOKEN" \
     https://app.crewai.com/crewai_plus/api/v1/crews/YOUR-AUTOMATION-UUID/deploy
```

#### GitHub Actions Example

```yaml
name: Deploy CrewAI Automation
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger CrewAI Redeployment
        run: |
          curl -X POST \
               -H "Authorization: Bearer ${{ secrets.CREWAI_PAT }}" \
               https://app.crewai.com/crewai_plus/api/v1/crews/${{ secrets.CREWAI_AUTOMATION_UUID }}/deploy
```

### Project Structure Requirements for Deployment

- Entry point: `src/<project_name>/main.py`
- Crews must expose a `run()` function
- Flows must expose a `kickoff()` function
- All crew classes require `@CrewBase` decorator

### Deployed Automation REST API

| Endpoint               | Purpose                        |
| ---------------------- | ------------------------------ |
| `/inputs`              | List required input parameters |
| `/kickoff`             | Trigger execution with inputs  |
| `/status/{kickoff_id}` | Check execution status         |

### AMP Dashboard Tabs

- **Status**: Deployment info, API endpoint, auth token
- **Run**: Crew structure visualization
- **Executions**: Run history
- **Metrics**: Performance analytics
- **Traces**: Detailed execution insights

### Deployment Troubleshooting

| Error            | Fix                                                        |
| ---------------- | ---------------------------------------------------------- |
| Missing uv.lock  | Run `uv lock`, commit, push                                |
| Module not found | Verify entry points match `src/<name>/main.py` structure   |
| Crew not found   | Ensure `@CrewBase` decorator on all crew classes           |
| API key errors   | Check env var names match code and are set in the platform |

---

## Environment Setup

### Required `.env`

```.env
OPENAI_API_KEY=sk-...
# Optional depending on tools/providers:
SERPER_API_KEY=...
ANTHROPIC_API_KEY=...
# Override default model:
MODEL=gpt-4o
```

### Python Version

Python >=3.10, <3.14

### Installation

```bash
uv tool install crewai        # Install CrewAI CLI
uv tool list                  # Verify installation
crewai create crew my_crew --skip_provider   # Scaffold a new project
crewai install                # Install project dependencies
crewai run                    # Execute
```

---

## Development Best Practices

1. **YAML-first configuration**: Define agents and tasks in YAML, keep crew classes minimal
2. **Check built-in tools** before writing custom ones
3. **Use structured output** (output_pydantic) for data that flows between tasks or crews
4. **Use guardrails** to validate task outputs programmatically
5. **Enable memory** for crews that benefit from cross-session learning
6. **Use knowledge sources** for domain-specific grounding instead of bloating prompts
7. **Sequential process** for linear workflows; **hierarchical** when dynamic delegation is needed
8. **Flows for multi-crew orchestration**: Use `@start`, `@listen`, `@router` for complex pipelines
9. **Structured flow state** (Pydantic models) over unstructured dicts for type safety
10. **Test with** `crewai test` to evaluate crew performance across iterations
11. **Verbose mode** during development, disable in production
12. **Rate limiting** (`max_rpm`) to avoid API throttling
13. **`respect_context_window=True`** to auto-handle token limits

## Common Pitfalls

- **Using `ChatOpenAI()`** — Always use `crewai.LLM` or string shorthand like `"openai/gpt-4o"`
- Leaving config dictionary access untyped in crew classes
- Agent/task method names not matching YAML keys
- Missing `expected_output` in task configuration (required)
- Not passing `inputs` to `kickoff()` when YAML uses `{variable}` interpolation
- Using `process=Process.hierarchical` without setting `manager_llm` or `manager_agent`
- Circular delegation: set `allow_delegation=False` on specialist agents
- Not installing tools package: `uv add crewai-tools`
