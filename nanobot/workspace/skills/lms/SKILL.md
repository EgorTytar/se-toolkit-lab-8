# LMS Skill

## MANDATORY BEHAVIOR

**User says:** "Show me the scores" / "What are the pass rates?" / "How did students do?" (without lab name)

**You MUST respond:**
"Which lab would you like to see scores for? Available labs: [LIST LABS FROM lms_labs TOOL]"

**DO NOT:** Show any scores, call lms_pass_rates, or display data tables until user specifies a lab.

**Exception:** Only show comparison across labs when user explicitly asks "which lab has the lowest/highest..."

## Tools Available

| Tool | When to use |
|------|-------------|
| lms_labs | When user needs to choose a lab, or asks "what labs exist" |
| lms_pass_rates | ONLY after user specifies which lab |
| lms_health | When asked about system status |
| lms_timeline | ONLY after user specifies which lab |
| lms_groups | ONLY after user specifies which lab |
| lms_top_learners | ONLY after user specifies which lab |
| lms_completion_rate | ONLY after user specifies which lab |

## Conversation Examples

**Example 1 - User doesn't specify lab:**
- User: "Show me the scores"
- You: "Which lab would you like to see scores for? Available labs: Lab 01, Lab 02, Lab 03... Please specify."
- User: "Lab 01"
- You: [Call lms_pass_rates with lab="lab-01" and show results]

**Example 2 - User specifies lab:**
- User: "Show me scores for Lab 06"
- You: [Call lms_pass_rates directly and show results]

**Example 3 - Comparison question (exception):**
- User: "Which lab has the lowest pass rate?"
- You: [Call lms_pass_rates for all labs and compare]
