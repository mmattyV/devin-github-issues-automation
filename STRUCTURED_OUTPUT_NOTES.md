# Structured Output - Key Learnings

## Critical Finding from Devin Documentation

> **"Structured output is like Devin's notepad - it updates its notes as it works, and you can check these notes anytime. Currently, you can't force Devin to update its notes, but you can request to see what it has written so far."**

Source: https://docs.devin.ai/api-reference/structured-output

### What This Means

1. **Devin updates on its own schedule** - we cannot force it to populate `structured_output`
2. **It may remain `null` for a while** - even after completing analysis
3. **We can only poll and request to see what's written** - no control over when it updates

## Correct Implementation

### ✅ What We Fixed

1. **Correct Endpoint**: `/v1/sessions/{session_id}` (not `/v1/session/{session_id}`)

2. **Prompt Format**: Matched documentation examples
   - Use natural language: "provide updates in this format"
   - Include update triggers: "Please update the structured output immediately whenever you..."
   - Embed JSON schema directly with `json.dumps(schema)`
   - Keep instructions concise

3. **Example Format**:
```python
schema = {"field": "value", ...}

prompt = f"""Your task...

Provide updates in this format. Please update the structured output immediately whenever [trigger events]:
{json.dumps(schema)}

Additional instructions...
"""
```

### Best Practices from Documentation

- Include schema definition in initial prompt ✅
- Define expected update frequency ✅  
- Use clear, descriptive field names ✅
- Include example values in schema ✅
- Poll with 10-30 second intervals ✅
- Stop polling when session completes ✅

## Reality Check

**Structured output may not always populate**, even with correct implementation. This is a known limitation where:
- Devin decides when to update its "notepad"
- The field can remain `null` even after task completion
- We rely on Devin's messages for guaranteed information

## Fallback Strategy

When `structured_output` is `null`, extract information from Devin's messages:
- Messages contain the analysis ("Medium risk, 13 hours estimated, 0.70 confidence")
- Parse messages as a backup data source
- Consider implementing message parsing for reliability

