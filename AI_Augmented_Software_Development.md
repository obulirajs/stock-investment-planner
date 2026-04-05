## AI-augmented software engineering workflow 🚀
   - (Spec Driven Development Using Agents and LLM)

# 🔥 Prompt 1:
Compare this implementation with the spec.

Check:
1. Does the code fully implement the spec?
2. Any missing functionality?
3. Any incorrect logic?
4. Any performance issues?
5. Any design improvements?

Give output in 3 sections:
- Aligned
- Missing
- Improvements

# 🔍 Prompt 2 (logic validation)
Verify if all indicators computed in the code match the spec.
List any missing indicators or mismatches.

# 🔍 Prompt 3 (incremental loginc)
Check if incremental processing is correctly implemented.
Does it avoid recomputation?

# 🔍 Prompt 4 (data correctness)
Validate if the computed indicators are mathematically correct.
Highlight any incorrect formulas or edge cases.

🧠 How YOU should evaluate responses

Don’t blindly accept.

👉 Check:

Is suggestion practical?
Does it match your architecture?
Does it break anything?

## 🚀 Step 5: Apply SMALL changes only

👉 Never do:

“Rewrite entire file”

👉 Always do:

“Fix specific issue”

## 🧭 Hybrid Workflow (BEST PRACTICE)

Use BOTH:

🟢 ChatGPT (here)
architecture
planning
decisions
🟢 VS Code Agent
code-level execution
quick iteration

## 🔥 Development Loop
1. Write spec (ChatGPT)
2. Open code (VS Code)
3. Ask agent → compare spec vs code
4. Apply fixes
5. Validate
6. Repeat