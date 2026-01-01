#from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from typing import Dict, List
import logging
from logger_config import setup_logger

logger = setup_logger("generator")

class GeneratorAgent:
    """
    The 'Writer' agent. Synthesizes information into a final answer.
    """
    def __init__(self, llm):
        self.llm = llm
        # Define its specialized system prompt
        self.system_prompt = """You are a Generator Agent, an expert writer and synthesizer.
        Your ONLY task is to write the final answer to the user's question.
        
        CONTEXT & RULES:
        1. You will be given: 
           - The user's original question
           - A plan or instructions from the supervisor
           - Retrieved data (documents, web snippets, tool outputs)
        
        2. You MUST:
           - Base your answer STRICTLY on the provided context.
           - Cite specific sources using [Doc #] notation.
           - If the context is insufficient, say so. DO NOT invent facts.
           - Match the tone and detail level requested in the plan.
        
        3. Your output should be a polished, final-grade answer ready for user delivery.
        """
        
        # Create a robust prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", """
            Original User Question: {question}
            
            Supervisor's Instructions: {instructions}
            
            Retrieved Context:
            {context}
            
            Now, generate the final answer:
            """)
        ])
        
        # Create the chain
        self.chain = (
            RunnablePassthrough()  # Pass through all inputs
            | self.prompt_template
            | self.llm
        )
    
    def generate(self, *, question: str, instructions: str, context: List[str], chat_history: List = None) -> Dict:
        """
        Main generation method. Expects structured inputs.
        
        Args:
            question: Original user query
            instructions: Plan from Orchestrator/Intent agent
            context: List of context strings from retrievers/tools
            chat_history: Previous conversation (optional)
            
        Returns:
            Dictionary containing the answer and metadata
        """
        # Prepare context as a single string
        formatted_context = self._format_context(context)
        
        # Prepare inputs for the chain
        inputs = {
            "question": question,
            "instructions": instructions,
            "context": formatted_context,
            "chat_history": chat_history or []
        }
        
        # Generate the answer
        logger.info(f"Generating answer for: {question[:50]}...")
        response = self.chain.invoke(inputs)
        
        # Extract citations
        citations = self._extract_citations(response.content, context)
        
        return {
            "answer": response.content,
            "citations": citations,
            "agent": "generator",
            "raw_response": response
        }
    
    def _format_context(self, context_list: List[str]) -> str:
        """Format multiple context chunks into a readable string with clear sources."""
        formatted = []
        for i, chunk in enumerate(context_list):
            # Add source identifier
            formatted.append(f"[Source {i+1}]:\n{chunk}\n")
        return "\n---\n".join(formatted)
    
    def _extract_citations(self, answer: str, sources: List[str]) -> List[int]:
        """Extract which sources were cited in the answer."""
        cited_indices = []
        # Simple extraction of [Doc #] pattern
        import re
        matches = re.findall(r'\[(?:Doc|Source)\s*(\d+)\]', answer)
        for match in matches:
            idx = int(match) - 1  # Convert to zero-index
            if 0 <= idx < len(sources):
                cited_indices.append(idx)
        return cited_indices
    
    def handle_critique(self, draft_answer: str, critique: Dict) -> str:
        """
        Revise the answer based on critic feedback.
        This is called if the Critic Agent rejects the first draft.
        """
        revision_prompt = f"""
        You previously generated this answer:
        {draft_answer}
        
        The Critic Agent found these issues:
        {critique.get('issues', 'No specific issues provided')}
        
        Specific correction instructions:
        {critique.get('correction_plan', 'Improve the answer.')}
        
        Please generate a revised answer that fixes these issues:
        """
        
        revised = self.llm.invoke(revision_prompt)
        return revised.content

    def generate_with_format(self, format_spec: str, **kwargs):
        """Generate answers in specific formats (JSON, markdown, bullet points)."""
        format_instructions = {
            "json": "Format the answer as a valid JSON object.",
            "markdown": "Use markdown with headers, bold, and lists.",
            "executive_summary": "One paragraph, 3 bullet points, conclusion.",
            "technical": "Include code snippets and detailed specifications."
        }
        
        instructions = kwargs.get("instructions", "")
        kwargs["instructions"] = f"{instructions}\n\nOutput Format: {format_instructions.get(format_spec, '')}"
        
        return self.generate(**kwargs)

    def generate_with_confidence(self, **kwargs):
        """Generate answer with a confidence score based on source quality."""
        result = self.generate(**kwargs)
        
        # Analyze how well sources support the answer
        support_score = self._calculate_support_score(
            result["answer"],
            kwargs["context"]
        )
        
        # Check for hedging language
        certainty_score = self._analyze_certainty_language(result["answer"])
        
        result["confidence"] = (support_score + certainty_score) / 2
        result["confidence_reason"] = f"Based on source support ({support_score}/2) and certainty ({certainty_score}/2)"
        
        return result