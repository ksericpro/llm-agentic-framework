import dspy
from typing import Dict, List, Any
from generator_dspy import compile_generator, GeneratorModule
from logger_config import setup_logger

logger = setup_logger("generator_dspy")

# Singleton for the compiled generator
_COMPILED_GENERATOR = None

def get_or_compile_generator():
    global _COMPILED_GENERATOR
    if _COMPILED_GENERATOR is None:
        logger.info("⚙️ Compiling DSPy Generator (First Run)...")
        _COMPILED_GENERATOR = compile_generator()
    return _COMPILED_GENERATOR

class GeneratorAgent:
    """
    DSPy-powered Generator Agent implementation.
    replaces the LangChain-based GeneratorAgent.
    """
    
    def __init__(self, llm):
        # We accept llm to maintain interface compatibility
        self.generator = get_or_compile_generator()
        
    def generate(self, *, question: str, instructions: str, context: List[str], chat_history: List = None, summary: str = "") -> Dict:
        """
        Main generation method.
        """
        logger.info(f"DSPy Generating answer for: {question[:50]}...")
        
        # Format context similar to original agent but simpler
        formatted_context = self._format_context(context)
        formatted_history = self._format_history(chat_history)
        
        # Run DSPy
        pred = self.generator(
            question=question, 
            context=formatted_context,
            chat_history=formatted_history + f"\nSummary: {summary}",
            instructions=instructions
        )
        
        answer = pred.answer
        citations = self._extract_citations(answer, context)
        
        return {
            "answer": answer,
            "citations": citations,
            "agent": "generator_dspy",
            "raw_response": pred
        }
    
    def handle_critique(self, draft_answer: str, critique: Dict) -> str:
        """
        Handle critique by re-running generation with explicit instructions.
        """
        logger.info("DSPy handling critique...")
        
        correction_plan = critique.get('correction_plan', 'Fix the identified issues.')
        issues = critique.get('issues', 'No specific issues.')
        
        # We treat this as a new generation task with very specific instructions
        # Note: In a full DSPy setup, we might have a specific 'Refiner' module,
        # but reusing the generator with 'Correction Instructions' works well too.
        
        instructions = f"""
        PREVIOUS ANSWER WAS REJECTED.
        Issues: {issues}
        Correction Plan: {correction_plan}
        Please REWRITE the answer to fix these issues.
        """
        
        # We pass the previous draft as context or simple history
        context = f"Previous Draft: {draft_answer}"
        
        pred = self.generator(
            question="Revise the previous answer",
            context=context,
            chat_history="",
            instructions=instructions
        )
        
        return pred.answer

    def _format_context(self, context_list: List[str]) -> str:
        """Format context for DSPy"""
        formatted = []
        for i, chunk in enumerate(context_list):
            formatted.append(f"[Source {i+1}]: {chunk}")
        return "\n\n".join(formatted)

    def _format_history(self, history: List) -> str:
        """Simple history formatter"""
        if not history:
            return ""
        return str(history)

    def _extract_citations(self, answer: str, sources: List[str]) -> List[int]:
        """Extract [Source X] citations"""
        import re
        ids = []
        matches = re.findall(r'\[Source (\d+)\]', answer)
        for m in matches:
            idx = int(m) - 1
            if 0 <= idx < len(sources):
                ids.append(idx)
        return list(set(ids))
