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
        
        if not critique["pass"]:
            # Generate specific instructions for correction
            correction_plan = self._create_correction_plan(critique)
            return {
                "needs_correction": True,
                "issues": critique["issues"],
                "correction_plan": correction_plan
            }
        return {"needs_correction": False}