from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from typing import List
import logging
from logger_config import setup_logger

logger = setup_logger("intent")

class PlanSchema(BaseModel):
    """Structured output for the intent and execution plan."""
    intent: str = Field(description="The user's primary intent.")
    steps: List[str] = Field(description="List of steps to fulfill the request.")
    reasoning: str = Field(description="Brief reasoning for the plan.")

class IntentPlanningAgent:
    def __init__(self, llm):
        self.llm = llm
        self.intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an Intent & Planning Agent. 
            Analyze the user's query, conversation history, and summary to determine the user's intent and create a step-by-step execution plan.
            
            **Conversation Summary:**
            {summary}
            
            **Guidelines:**
            1. Identify the core goal of the user.
            2. Break down the task into logical steps.
            3. Consider past preferences or context from the history and summary.
            4. If the query is ambiguous, use the context to resolve it.
            
            Return your analysis as structured JSON."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "User Query: {query}")
        ])
        # Create a chain that outputs the structured PlanSchema
        self.chain = self.intent_prompt | self.llm.with_structured_output(PlanSchema)

    def analyze(self, user_query: str, chat_history: list = None, summary: str = "") -> PlanSchema:
        """Analyze intent and create a plan."""
        logger.info(f"Analyzing intent for: {user_query[:100]}...")
        plan = self.chain.invoke({
            "query": user_query,
            "chat_history": chat_history or [],
            "summary": summary or "No previous summary available."
        })
        return plan
