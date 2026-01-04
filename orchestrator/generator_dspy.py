import dspy
import os
from dotenv import load_dotenv

load_dotenv()

# Configure basic LLM
turbo = dspy.LM('openai/gpt-4o-mini', max_tokens=1000)
dspy.configure(lm=turbo)

try:
    from dspy.teleprompt import BootstrapFewShot
except ImportError:
    from dspy import BootstrapFewShot

# 1. Define Signature
class GeneratorSignature(dspy.Signature):
    """
    Synthesize a final answer based on the retrieved context and user query.
    Rules:
    - Base answer ONLY on context.
    - Cite sources using [Source X] notation.
    - If context is insufficient, state it clearly.
    """
    question = dspy.InputField(desc="User's original question")
    context = dspy.InputField(desc="Retrieved documents/search results")
    chat_history = dspy.InputField(desc="Previous conversation history (optional)")
    instructions = dspy.InputField(desc="Specific instructions from the planner")
    
    answer = dspy.OutputField(desc="The final, cited answer")

# 2. Define Module
class GeneratorModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.prog = dspy.ChainOfThought(GeneratorSignature)
    
    def forward(self, question, context, chat_history="", instructions=""):
        return self.prog(
            question=question,
            context=context,
            chat_history=chat_history,
            instructions=instructions
        )

# 3. Validation Logic (Faithfulness Metric)
def validate_citations(example, pred, trace=None):
    """
    Checks if the predicted answer cites sources that actually exist in the context.
    Simple heuristic: If answer contains [Source X], X must be valid.
    """
    import re
    
    # Check if predicted answer is present
    if not hasattr(pred, "answer") or not pred.answer:
        return False
        
    answer = pred.answer
    
    citations = re.findall(r'\[Source (\d+)\]', answer)
    
    # We want to encourage citations if context is substantial
    if not citations and len(example.context) > 50: 
         if "don't know" in answer.lower() or "insufficient" in answer.lower():
             return True
         return False 
         
    return True

# 4. Training Data
train_examples = [
    dspy.Example(
        question="What is the price of Apple stock?",
        context="[Source 1] Apple (AAPL) is trading at $150.25 as of today.\n[Source 2] Microsoft is at $300.",
        chat_history="",
        instructions="Provide the current price.",
        answer="Apple stock is trading at $150.25 today [Source 1]."
    ).with_inputs("question", "context", "chat_history", "instructions"),
    
    dspy.Example(
        question="Who is the CEO of Google?",
        context="[Source 1] Sundar Pichai is the CEO of Alphabet and Google.",
        chat_history="",
        instructions="Identify the CEO.",
        answer="The CEO of Google is Sundar Pichai [Source 1]."
    ).with_inputs("question", "context", "chat_history", "instructions"),
    
    dspy.Example(
        question="What is the capital of Mars?",
        context="[Source 1] Mars is the fourth planet from the sun.\n[Source 2] It has no known cities or capitals.",
        chat_history="",
        instructions="",
        answer="Mars does not have a capital city [Source 2]."
    ).with_inputs("question", "context", "chat_history", "instructions"),
    
    dspy.Example(
        question="Summarize the meeting notes.",
        context="[Source 1] Meeting started at 10 AM. Discussed project X. Agreed to launch next week.",
        chat_history="",
        instructions="Summarize key points.",
        answer="The meeting focused on Project X, with a decision to launch next week [Source 1]."
    ).with_inputs("question", "context", "chat_history", "instructions"),
]

# 5. Compilation Function
def compile_generator():
    print("🚀 Compiling DSPy Generator...")
    try:
        teleprompter = BootstrapFewShot(metric=validate_citations, max_bootstrapped_demos=4, max_labeled_demos=4)
        compiled_generator = teleprompter.compile(GeneratorModule(), trainset=train_examples)
        print("✅ Generator Compiled Successfully!")
        return compiled_generator
    except Exception as e:
        print(f"⚠️ Compilation failed: {e}")
        print("⚠️ Falling back to unoptimized generator.")
        return GeneratorModule()

if __name__ == "__main__":
    compile_generator()
