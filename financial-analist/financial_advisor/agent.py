from google.adk.agent import Agent
from google.adk.models.lite_llm import LiteLLM

MODEL = LiteLLM(
    "openai/gpt-4o"
)

weather_agent = Agent(
    name = "WeatehrAgent",
    instruction= "you help teh user with weather related questions ",
    model = MODEL,
)
root_agent = weather_agent
