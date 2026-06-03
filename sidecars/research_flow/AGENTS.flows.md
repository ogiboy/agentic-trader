# CrewAI Flow Reference

Companion reference for [AGENTS.md](AGENTS.md). Follow the freshness checks in the root file before changing CrewAI Flow code.

## Flows

### Basic Flow

```python
from crewai.flow.flow import Flow, listen, start

class MyFlow(Flow):
    @start()
    def begin(self):
        return "initial data"

    @listen(begin)
    def process(self, data):
        return f"processed: {data}"
```

### Flow Decorators

| Decorator         | Purpose                                                                      |
| ----------------- | ---------------------------------------------------------------------------- |
| `@start()`        | Entry point(s), execute when flow begins. Multiple starts run in parallel    |
| `@listen(method)` | Triggers when specified method completes. Receives output as argument        |
| `@router(method)` | Conditional branching. Returns string labels that trigger `@listen("label")` |

### Structured State

```python
from pydantic import BaseModel

class ResearchState(BaseModel):
    topic: str = ""
    research: str = ""
    report: str = ""

class ResearchFlow(Flow[ResearchState]):
    @start()
    def set_topic(self):
        self.state.topic = "AI Agents"

    @listen(set_topic)
    def do_research(self):
        # self.state.topic is available
        result = ResearchCrew().crew().kickoff(
            inputs={"topic": self.state.topic}
        )
        self.state.research = result.raw
```

### Unstructured State (dict-based)

```python
class SimpleFlow(Flow):
    @start()
    def begin(self):
        self.state["counter"] = 0  # Dict access

    @listen(begin)
    def increment(self):
        self.state["counter"] += 1
```

### Conditional Routing

```python
from crewai.flow.flow import Flow, listen, router, start

class QualityFlow(Flow):
    @start()
    def generate(self):
        return {"score": 0.85}

    @router(generate)
    def check_quality(self, result):
        if result["score"] > 0.8:
            return "high_quality"
        return "needs_revision"

    @listen("high_quality")
    def publish(self, result):
        print("Publishing...")

    @listen("needs_revision")
    def revise(self, result):
        print("Revising...")
```

### Parallel Triggers with or*and and*

```python
from crewai.flow.flow import or_, and_

class ParallelFlow(Flow):
    @start()
    def task_a(self):
        return "A done"

    @start()
    def task_b(self):
        return "B done"

    # Fires when EITHER completes
    @listen(or_(task_a, task_b))
    def on_any(self, result):
        print(f"First result: {result}")

    # Fires when BOTH complete
    @listen(and_(task_a, task_b))
    def on_all(self):
        print("All parallel tasks done")
```

### Integrating Crews in Flows

```python
from crewai.flow.flow import Flow, listen, start
from my_project.crews.research_crew.research_crew import ResearchCrew
from my_project.crews.writing_crew.writing_crew import WritingCrew

class ContentFlow(Flow[ContentState]):
    @start()
    def research(self):
        result = ResearchCrew().crew().kickoff(
            inputs={"topic": self.state.topic}
        )
        self.state.research = result.raw

    @listen(research)
    def write(self):
        result = WritingCrew().crew().kickoff(
            inputs={
                "topic": self.state.topic,
                "research": self.state.research,
            }
        )
        self.state.article = result.raw
```

### Using Agents Directly in Flows

```python
from crewai.agent import Agent

class AgentFlow(Flow):
    @start()
    async def analyze(self):
        analyst = Agent(
            role="Data Analyst",
            goal="Analyze market trends",
            backstory="Expert data analyst...",
            tools=[SerperDevTool()],
        )
        result = await analyst.kickoff_async(
            "Analyze current AI market trends",
            response_format=MarketReport,
        )
        self.state.report = result.pydantic
```

### Human-in-the-Loop (v1.8.0+)

```python
from crewai.flow.flow import Flow, listen, start
from crewai.flow.human_feedback import human_feedback

class ReviewFlow(Flow):
    @start()
    @human_feedback(
        message="Approve this content?",
        emit=["approved", "rejected"],
        llm="gpt-4o-mini",
    )
    def generate_content(self):
        return "Content for review"

    @listen("approved")
    def on_approval(self, result):
        feedback = self.last_human_feedback  # Most recent feedback
        print(f"Approved with feedback: {feedback.feedback}")

    @listen("rejected")
    def on_rejection(self, result):
        history = self.human_feedback_history  # All feedback as list
        print("Rejected, revising...")
```

### State Persistence

```python
from crewai.flow.flow import persist

@persist  # Saves state to SQLite; auto-recovers on restart
class ResilientFlow(Flow[MyState]):
    @start()
    def begin(self):
        self.state.step = 1
```

### Flow Execution

```python
flow = MyFlow()
result = flow.kickoff()
print(result)                  # Output of last method
print(flow.state)              # Final state

# Async execution
result = await flow.kickoff_async(inputs={"key": "value"})
```

### Flow Streaming (v1.8.0+)

```python
class StreamingFlow(Flow):
    stream = True  # Enable streaming at class level

    @start()
    def generate(self):
        return "streamed content"

flow = StreamingFlow()
streaming = flow.kickoff()
for chunk in streaming:
    print(chunk.content, end="", flush=True)
result = streaming.result  # Final result after iteration
```

### Flow Visualization

```python
flow.plot("my_flow")           # Generates my_flow.html
```

---
