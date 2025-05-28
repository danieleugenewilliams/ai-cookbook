# AI Cookbook

A comprehensive collection of AI workflow patterns and examples using modern LLM techniques. This repository demonstrates various approaches to building AI-powered applications, from basic implementations to complex orchestration patterns.

## Project Structure

```
patterns/
├── workflows/
│   ├── 1-introduction/       # Basic concepts and fundamentals
│   ├── 2-workflow-patterns/  # Advanced patterns and implementations
│   └── 3-projects/           # Project examples
```

### Introduction
- Basic LLM interactions
- Structured outputs
- Tool usage
- Knowledge retrieval

### Workflow Patterns
- Prompt chaining
- Request routing
- Parallel processing
- Orchestration

### Projects
1. **Blog Post Orchestrator**: Demonstrates content generation and management using prompt chaining and local LLMs.
2. **Legislation Reviewer**: Analyzes legislative documents using both OpenAI and local LLMs, with chunking and structured output.
3. **Image Recognition**: Uses a vision-enabled local LLM (Gemma 3-4B IT QAT) to describe images. 
   - Example settings for image recognition LLM:
     - Offload KV Cache to GPU Memory: true
     - Keep Model in Memory: true
     - Try mmap(): true
     - Seed: -1
     - Flash Attention: true
     - K Cache Quantization Type: Q8_0
     - V Cache Quantization Type: Q8_0
     - Context Length: 30246
     - Evaluation Batch Size: 512
     - CPU Thread Pool Size: 8

## Getting Started

1. Clone the repository
2. Install dependencies:
```bash
pip install openai python-dotenv tiktoken pydantic
```
3. Set up your environment variables:
```bash
export OPENAI_API_KEY="your-api-key"
```
Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key
```

## Usage

### Basic Example
```python
from openai import OpenAI
import os
import dotenv

dotenv.load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

### Using Local LLMs
For local LLM setup (example from legislation reviewer):
```python
client = OpenAI(
    base_url="http://your-local-llm:1234/v1",
    api_key="not-needed-for-local-llm"
)
```

## Key Features

- Structured data handling with Pydantic models
- Error handling and logging
- Local LLM integration
- Parallel processing capabilities
- Complex workflow orchestration
- Token management and context windowing

## Requirements

- Python 3.8+
- OpenAI API key (for OpenAI models)
- Local LLM setup (optional, for local model usage)
- Dependencies listed in requirements.txt

## Best Practices

1. Always use environment variables for API keys
2. Implement proper error handling
3. Use structured data models
4. Monitor token usage
5. Implement logging for debugging

## License

MIT License