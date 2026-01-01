from pydantic import BaseModel, Field
from typing import List

class CritiqueSchema(BaseModel):
    """Structured output for the critic's review."""
    pass_: bool = Field(
        alias="pass",
        description="Whether the draft answer passes quality checks."
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of specific issues found in the draft answer."
    )
    reasoning: str = Field(
        description="Detailed reasoning for the verdict."
    )

class CriticAgent:
    def __init__(self, llm):
        self.llm = llm
    
    def review(self, original_query: str, draft_answer: str, source_data: list) -> dict:
        critique_prompt = f"""
        You are a strict quality assurance agent. Review the draft answer based on:
        
        1. **Factual Consistency**: Does the answer match the provided source data?
        2. **Completeness**: Does it fully address '{original_query}'?
        3. **Hallucination Check**: Are any claims made without source support?
        4. **Safety & Tone**: Is it appropriate and helpful?
        
        Source Data: {source_data}
        Draft Answer: {draft_answer}
        
        Provide a structured critique and a pass/fail verdict.
        """
        
        critique = self.llm.with_structured_output(CritiqueSchema).invoke(critique_prompt)
        
        if not critique.pass_:
            # Generate specific instructions for correction
            correction_plan = self._create_correction_plan(critique)
            return {
                "needs_correction": True,
                "issues": critique.issues,
                "correction_plan": correction_plan
            }
        return {"needs_correction": False}
    
    def _create_correction_plan(self, critique: CritiqueSchema) -> str:
        """Generate a correction plan based on the critique."""
        plan_parts = ["The draft answer needs the following corrections:"]
        
        for i, issue in enumerate(critique.issues, 1):
            plan_parts.append(f"{i}. {issue}")
        
        plan_parts.append(f"\nReasoning: {critique.reasoning}")
        plan_parts.append("\nPlease revise the answer to address these issues.")
        
        return "\n".join(plan_parts)