class IntentPlanningAgent:
    def __init__(self, llm):
        self.llm = llm
        
    def analyze(self, query: str) -> dict:
        prompt = f"""
        Analyze the user's query and create an execution plan.
        
        Query: "{query}"
        
        Steps:
        1. Classify intent: 'document_search', 'web_search', 'calculation', 'complex_task'
        2. If complex, break into sub-tasks.
        3. Determine which specialist agents are needed and in what order.
        
        Return a JSON with: intent, steps[], and next_agent.
        """
        # Use LLM with structured output
        plan = self.llm.with_structured_output(PlanSchema).invoke(prompt)
        return plan

# Example structured output schema
from pydantic import BaseModel
class PlanStep(BaseModel):
    agent: str  # 'retriever', 'web', 'calculator', 'analyst'
    task: str   # Specific instruction
class PlanSchema(BaseModel):
    intent: str
    steps: List[PlanStep]