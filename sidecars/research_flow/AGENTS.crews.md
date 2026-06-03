# CrewAI Crew Reference

Companion reference for [AGENTS.md](AGENTS.md). Follow the freshness checks in the root file before changing CrewAI code.

## Architecture Overview

- **Agent**: Autonomous unit with a role, goal, backstory, tools, and an LLM. Makes decisions and executes tasks.
- **Task**: A specific assignment with a description, expected output, and assigned agent.
- **Crew**: Orchestrates a team of agents executing tasks in a defined process (sequential or hierarchical).
- **Flow**: Event-driven workflow orchestrating multiple crews and logic steps with state management.

## YAML Configuration

### agents.yaml

```yaml
researcher:
  role: >
    {topic} Senior Data Researcher
  goal: >
    Uncover cutting-edge developments in {topic}
  backstory: >
    You're a seasoned researcher with a knack for uncovering
    the latest developments in {topic}. Known for your ability
    to find the most relevant information.
  # Optional YAML-level settings:
  # llm: openai/gpt-4o
  # max_iter: 20
  # max_rpm: 10
  # verbose: true

writer:
  role: >
    {topic} Technical Writer
  goal: >
    Create compelling content about {topic}
  backstory: >
    You're a skilled writer who translates complex technical
    information into clear, engaging content.
```

Variables like `{topic}` are interpolated from `crew.kickoff(inputs={"topic": "AI Agents"})`.

### tasks.yaml

```yaml
research_task:
  description: >
    Conduct thorough research about {topic}.
    Identify key trends, breakthrough technologies,
    and potential industry impacts.
  expected_output: >
    A detailed report with analysis of the top 5
    developments in {topic}, with sources and implications.
  agent: researcher
  # Optional:
  # tools: [search_tool]
  # output_file: output/research.md
  # markdown: true
  # async_execution: false

writing_task:
  description: >
    Write an article based on the research findings about {topic}.
  expected_output: >
    A polished 4-paragraph article formatted in markdown.
  agent: writer
  output_file: output/article.md
```

## Crew Class Pattern

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from crewai_tools import SerperDevTool

@CrewBase
class ResearchCrew:
    """Research and writing crew."""

    agents: List[BaseAgent]
    tasks: List[Task]

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            tools=[SerperDevTool()],
            verbose=True,
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config["writer"],
            verbose=True,
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config["research_task"],
        )

    @task
    def writing_task(self) -> Task:
        return Task(
            config=self.tasks_config["writing_task"],
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Research Crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
```

### Key formatting rules

- Prefer typed config helpers or validated casts for config dictionary access
- Agent/task method names must match YAML keys exactly
- Tools go on agents (not tasks) unless task-specific override is needed
- Never leave commented-out code in crew classes

### Lifecycle hooks

```python
@CrewBase
class MyCrew:
    @before_kickoff
    def prepare(self, inputs):
        # Modify inputs before execution
        inputs["extra"] = "value"
        return inputs

    @after_kickoff
    def summarize(self, result):
        # Process result after execution
        print(f"Done: {result.raw[:100]}")
        return result
```

## main.py Pattern

```python
#!/usr/bin/env python
from my_crew.crew import ResearchCrew

def run():
    inputs = {"topic": "AI Agents"}
    ResearchCrew().crew().kickoff(inputs=inputs)

if __name__ == "__main__":
    run()
```

## Agent Configuration

### Required Parameters

| Parameter   | Description                            |
| ----------- | -------------------------------------- |
| `role`      | Function and expertise within the crew |
| `goal`      | Individual objective guiding decisions |
| `backstory` | Context and personality                |

### Key Optional Parameters

| Parameter                | Default    | Description                                 |
| ------------------------ | ---------- | ------------------------------------------- |
| `llm`                    | GPT-4      | Language model (string or LLM object)       |
| `tools`                  | []         | List of tool instances                      |
| `max_iter`               | 20         | Max iterations before best answer           |
| `max_execution_time`     | None       | Timeout in seconds                          |
| `max_rpm`                | None       | Rate limiting (requests per minute)         |
| `max_retry_limit`        | 2          | Retries on errors                           |
| `verbose`                | False      | Detailed logging                            |
| `memory`                 | False      | Conversation history                        |
| `allow_delegation`       | False      | Can delegate tasks to other agents          |
| `allow_code_execution`   | False      | Can run code                                |
| `code_execution_mode`    | "safe"     | "safe" (Docker) or "unsafe" (direct)        |
| `respect_context_window` | True       | Auto-summarize when exceeding token limits  |
| `cache`                  | True       | Tool result caching                         |
| `reasoning`              | False      | Reflect and plan before task execution      |
| `multimodal`             | False      | Process text and visual content             |
| `knowledge_sources`      | []         | Domain-specific knowledge bases             |
| `function_calling_llm`   | None       | Separate LLM for tool invocation            |
| `inject_date`            | False      | Auto-inject current date into agent context |
| `date_format`            | "%Y-%m-%d" | Date format when inject_date is True        |

### Direct Agent Usage (without a Crew)

Agents can execute tasks independently via `kickoff()` — no Crew required:

```python
from crewai import Agent
from crewai_tools import SerperDevTool
from pydantic import BaseModel

class ResearchFindings(BaseModel):
    main_points: list[str]
    key_technologies: list[str]
    future_predictions: str

researcher = Agent(
    role="AI Researcher",
    goal="Research the latest AI developments",
    backstory="Expert AI researcher...",
    tools=[SerperDevTool()],
    verbose=True,
)

# Unstructured output
result = researcher.kickoff("What are the latest LLM developments?")
print(result.raw)           # str
print(result.agent_role)    # "AI Researcher"
print(result.usage_metrics) # token usage

# Structured output with response_format
result = researcher.kickoff(
    "Summarize latest AI developments",
    response_format=ResearchFindings,
)
print(result.pydantic.main_points)  # List[str]

# Async variant
result = await researcher.kickoff_async("Your query", response_format=ResearchFindings)
```

Returns `LiteAgentOutput` with: `.raw`, `.pydantic`, `.agent_role`, `.usage_metrics`.

### LLM Configuration

**IMPORTANT**: Always use `crewai.LLM` LLM class.

```python
from crewai import LLM

# String shorthand (simplest)
agent = Agent(llm="openai/gpt-4o", ...)

# Full configuration with crewai.LLM
llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    temperature=0.7,
    max_tokens=4000,
)
agent = Agent(llm=llm, ...)

# Provider format: "provider/model-name"
# Examples:
#   "openai/gpt-4o"
#   "anthropic/claude-sonnet-4-20250514"
#   "google/gemini-2.0-flash"
#   "ollama/llama3"
#   "groq/llama-3.3-70b-versatile"
#   "bedrock/anthropic.claude-3-sonnet-20240229-v1:0"
```

Supported providers: OpenAI, Anthropic, Google Gemini, AWS Bedrock, Azure, Ollama, Groq, Mistral, and 20+ others via LiteLLM routing.

Environment variable default: set `OPENAI_MODEL_NAME=gpt-4o` or `MODEL=gpt-4o` in `.env`.

## Task Configuration

### Key Parameters

| Parameter               | Type            | Description                                    |
| ----------------------- | --------------- | ---------------------------------------------- |
| `description`           | str             | Clear statement of requirements                |
| `expected_output`       | str             | Completion criteria                            |
| `agent`                 | BaseAgent       | Assigned agent (optional in hierarchical)      |
| `tools`                 | List[BaseTool]  | Task-specific tools                            |
| `context`               | List[Task]      | Dependencies on other task outputs             |
| `async_execution`       | bool            | Non-blocking execution                         |
| `output_file`           | str             | File path for results                          |
| `output_json`           | Type[BaseModel] | Pydantic model for JSON output                 |
| `output_pydantic`       | Type[BaseModel] | Pydantic model for structured output           |
| `human_input`           | bool            | Require human review                           |
| `markdown`              | bool            | Format output as markdown                      |
| `callback`              | Callable        | Post-completion function                       |
| `guardrail`             | Callable or str | Output validation                              |
| `guardrails`            | List            | Multiple validation steps                      |
| `guardrail_max_retries` | int             | Retry on validation failure (default: 3)       |
| `create_directory`      | bool            | Auto-create output directories (default: True) |

### Task Dependencies (context)

```python
@task
def analysis_task(self) -> Task:
    return Task(
        config=self.tasks_config["analysis_task"],
        context=[self.research_task()],  # Gets output from research_task
    )
```

### Structured Output

```python
from pydantic import BaseModel

class Report(BaseModel):
    title: str
    summary: str
    findings: list[str]

@task
def report_task(self) -> Task:
    return Task(
        config=self.tasks_config["report_task"],
        output_pydantic=Report,
    )
```

### Guardrails

```python
# Function-based
def validate(result: TaskOutput) -> tuple[bool, Any]:
    if len(result.raw.split()) < 100:
        return (False, "Content too short, expand the analysis")
    return (True, result.raw)

# LLM-based (string prompt)
task = Task(..., guardrail="Must be under 200 words and professional tone")

# Multiple guardrails
task = Task(..., guardrails=[validate_length, validate_tone, "Must be factual"])
```

## Process Types

### Sequential (default)

Tasks execute in definition order. Output of one task serves as context for the next.

```python
Crew(agents=..., tasks=..., process=Process.sequential)
```

### Hierarchical

Manager agent delegates tasks based on agent capabilities. Requires `manager_llm` or `manager_agent`.

```python
Crew(
    agents=...,
    tasks=...,
    process=Process.hierarchical,
    manager_llm="gpt-4o",
)
```

## Crew Execution

```python
# Synchronous
result = crew.kickoff(inputs={"topic": "AI"})
print(result.raw)              # String output
print(result.pydantic)         # Structured output (if configured)
print(result.json_dict)        # Dict output
print(result.token_usage)      # Token metrics
print(result.tasks_output)     # List[TaskOutput]

# Async (native)
result = await crew.akickoff(inputs={"topic": "AI"})

# Batch execution
results = crew.kickoff_for_each(inputs=[{"topic": "AI"}, {"topic": "ML"}])

# Streaming output (v1.8.0+)
crew = Crew(agents=..., tasks=..., stream=True)
streaming = crew.kickoff(inputs={"topic": "AI"})
for chunk in streaming:
    print(chunk.content, end="", flush=True)
```

## Crew Options

| Parameter           | Description                                 |
| ------------------- | ------------------------------------------- |
| `process`           | Process.sequential or Process.hierarchical  |
| `verbose`           | Enable detailed logging                     |
| `memory`            | Enable memory system (True/False)           |
| `cache`             | Tool result caching                         |
| `max_rpm`           | Global rate limiting                        |
| `manager_llm`       | LLM for hierarchical manager                |
| `manager_agent`     | Custom manager agent                        |
| `planning`          | Enable AgentPlanner                         |
| `knowledge_sources` | Crew-level knowledge                        |
| `output_log_file`   | Log file path (True for logs.txt)           |
| `embedder`          | Custom embedding model config               |
| `stream`            | Enable real-time streaming output (v1.8.0+) |

---
