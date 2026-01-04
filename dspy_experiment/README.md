# DSPy Experiment

This folder contains a simple proof-of-concept for using **DSPy** to optimize a Financial Advisor agent.

## Files
- `dspy_demo.py`: A self-contained script that:
    1.  Defines a `FinancialAdvisorBot` (Chain-of-Thought).
    2.  Defines a training set of 5 examples.
    3.  Compiles (optimizes) the bot using `BootstrapFewShot`.
    4.  Compares the unoptimized vs. optimized output.

## How to Run

1.  **Install DSPy**:
    ```bash
    pip install dspy-ai
    ```
    *(Note: The main `requirements.txt` in `orchestrator/` has also been updated)*

2.  **Run the Demo**:
    ```bash
    python dspy_experiment/dspy_demo.py
    ```

## What to Expect
You will see the "Unoptimized" agent giving a standard zero-shot answer.
Then, you will see the "Optimized" agent which has "learned" from the few-shot examples to provide answers that match the style and logic of the training data (e.g., specific definitions of assets/liabilities).
