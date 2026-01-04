
import dspy
# dspy.teleprompt might be deprecated in 3.0, accessing top-level if available
try:
    from dspy.teleprompt import BootstrapFewShot
except ImportError:
    from dspy import BootstrapFewShot

from dspy.evaluate import Evaluate
import os
from dotenv import load_dotenv

# 1. Setup & Configuration
# Load environment variables (mostly for OPENAI_API_KEY)
# Assuming running from project root, or fixing path relative to this file
import pathlib
script_dir = pathlib.Path(__file__).parent.absolute()
project_root = script_dir.parent
env_path = project_root / "orchestrator" / ".env"
load_dotenv(env_path)

# Configure DSPy to use OpenAI (using DSPy 3.0+ syntax)
# We assume OPENAI_API_KEY is in your .env
# dspy.LM replaces dspy.OpenAI
turbo = dspy.LM('openai/gpt-4o-mini', max_tokens=1000)
dspy.configure(lm=turbo)

print("✅ DSPy Configured with OpenAI gpt-4o-mini (DSPy 3.0)")

# 2. Define the Task (Signature)
# This is the "Interface" of what we want the agent to do.
class FinanceQASignature(dspy.Signature):
    """Answer questions about basic finance and investing principles."""
    question = dspy.InputField(desc="The user's financial question")
    answer = dspy.OutputField(desc="A concise, helpful answer based on common financial wisdom")

# 3. Define the Agent (Module)
# This is where we implement the logic.
class FinancialAdvisorBot(dspy.Module):
    def __init__(self):
        super().__init__()
        # ChainOfThought allows the model to "think" before answering
        self.prog = dspy.ChainOfThought(FinanceQASignature)
    
    def forward(self, question):
        return self.prog(question=question)

# 4. Data for Optimization
# To "compile" (optimize) the agent, we need a few examples of "Good Behavior".
# These act as the training set for the optimizer.
train_examples = [
    dspy.Example(question="What is an asset?", answer="An asset is something that puts money in your pocket, like stocks, bonds, or real estate that generates income.").with_inputs("question"),
    dspy.Example(question="What is a liability?", answer="A liability is something that takes money out of your pocket, such as credit card debt, a car loan, or a house mortgage that you pay for.").with_inputs("question"),
    dspy.Example(question="Why is cash flow important?", answer="Cash flow is important because it represents the actual money moving in and out of your business or personal finances, determining your ability to pay bills and invest.").with_inputs("question"),
    dspy.Example(question="What is compound interest?", answer="Compound interest is the interest on a loan or deposit calculated based on both the initial principal and the accumulated interest from previous periods.").with_inputs("question"),
    dspy.Example(question="What is diversification?", answer="Diversification is a risk management strategy that mixes a wide variety of investments within a portfolio to lower the risk of losing money.").with_inputs("question"),
]

# Development set for evaluation
dev_examples = [
    dspy.Example(question="Is my house an asset?", answer="Traditionally yes, but if it doesn't generate income and costs money to maintain/pay off, some definitions (like Kiyosaki's) classify it as a liability.").with_inputs("question"),
    dspy.Example(question="What is ROI?", answer="ROI stands for Return on Investment, a performance measure used to evaluate the efficiency or profitability of an investment.").with_inputs("question"),
]

# 5. Define a Metric
# How do we know if the answer is good? (Simple string match or LLM judge).
# For this demo, we use a simple semantic similarity check (using LLM to judge).
class Assess(dspy.Signature):
    """Assess the quality of the answer closer to the target."""
    question = dspy.InputField()
    target_answer = dspy.InputField()
    predicted_answer = dspy.InputField()
    score = dspy.OutputField(desc="A score between 0 and 1", prefix="Score:")

def llm_metric(gold, pred, trace=None):
    question = gold.question
    target = gold.answer
    predicted = pred.answer
    
    # Ask GPT to grade it
    scorer = dspy.Predict(Assess)
    score_str = scorer(question=question, target_answer=target, predicted_answer=predicted).score
    try:
        return float(score_str)
    except:
        return 0.5 # Fallback

# 6. Optimization Loop
print("\n🚀 Starting Optimization (Compiling the Agent)...")

# We use BootstrapFewShot which finds the best examples to include in the prompt
teleprompter = BootstrapFewShot(metric=llm_metric, max_bootstrapped_demos=4, max_labeled_demos=4)

# Compile!
compiled_agent = teleprompter.compile(FinancialAdvisorBot(), trainset=train_examples)

print("✅ Optimization Complete!")

# 7. Test and Compare
print("\n🧪 Testing the Optimized Agent:")

test_q = "Should I buy a new car on credit?"
print(f"\nQuestion: {test_q}")

# Run Unoptimized (Zero-shot, just the class definition)
unoptimized = FinancialAdvisorBot()
print("\n--- Unoptimized Response ---")
res_unopt = unoptimized(test_q)
print(f"Raw Response Object: {res_unopt}")
# Try to get rationale or reasoning
rationale = getattr(res_unopt, 'rationale', getattr(res_unopt, 'reasoning', "No rationale found"))
print(f"Reasoning: {rationale}")
print(f"Answer: {res_unopt.answer}")

# Run Optimized (Compiled)
print("\n--- Optimized (DSPy Compiled) Response ---")
res_opt = compiled_agent(test_q)
# Try to get rationale or reasoning
rationale_opt = getattr(res_opt, 'rationale', getattr(res_opt, 'reasoning', "No rationale found"))
print(f"Reasoning: {rationale_opt}")
print(f"Answer: {res_opt.answer}")

print("\n✨ Notice how the optimized agent might adopt the style/conciseness of the training examples.")

# 8. Inspect the "Prompt"
# DSPy hides the prompt, but we can inspect what it built
print("\n🔍 Inspecting the Compiled Prompt (Last History):")
turbo.inspect_history(n=1)
