# Devin API Implementation Notes

## Based on Cognition's qa-devin Example

We reviewed the official `qa-devin` example repository from the Cognition team to ensure our implementation follows best practices.

### Key Fixes Applied

#### 1. **Correct API Endpoint** ✅
- **Wrong**: `/sessions/{session_id}`  
- **Correct**: `/session/{session_id}` (singular!)
- Sessions are created at `/sessions` (plural) but retrieved at `/session/{id}` (singular)

#### 2. **Correct Terminal States** ✅
Based on the qa-devin example, terminal states are:
- `finished` - Session completed successfully
- `blocked` - Session is blocked waiting for input
- `stopped` - Session was stopped

**Not** `expired` or `failed` as we initially assumed.

#### 3. **Use `status_enum` Field** ✅
The API returns two status fields:
- `status` - Human-readable string (e.g., "Working on your task...")
- `status_enum` - Machine-readable enum with values:
  - `working`
  - `blocked`
  - `finished`
  - `suspend_requested`
  - `resume_requested`
  - `resumed`

We now prefer `status_enum` for programmatic checks.

#### 4. **Complete Response Schema** ✅
Added missing fields to `DevinSession`:
- `status_enum` - Machine-readable status
- `title` - Session title
- `snapshot_id` - Snapshot identifier
- `playbook_id` - Playbook used
- `url` - Session URL (returned on creation)
- `is_new_session` - Whether session is new or reused (idempotent)

### Design Decisions

#### Pydantic vs TypedDict

**qa-devin uses**: `TypedDict` from typing
**We use**: Pydantic `BaseModel`

**Why we chose Pydantic:**
1. ✅ **Runtime validation** - Catches API response format changes early
2. ✅ **FastAPI integration** - Seamless request/response handling
3. ✅ **Type coercion** - Auto-parses datetime strings to datetime objects
4. ✅ **Default values** - Better handling of optional fields
5. ✅ **Documentation** - Field descriptions auto-generate API docs
6. ✅ **Flexibility** - Can mix with dict when needed (structured_output)

**Tradeoff**: Slightly more overhead, but worth it for type safety in a production system.

#### Sync vs Async

**qa-devin uses**: Async with `aiohttp`
**We use**: Sync with `httpx`

**Why we chose sync:**
1. ✅ **Simpler for CLI** - No need for `asyncio.run()` everywhere
2. ✅ **FastAPI handles async** - Orchestrator can still be async
3. ✅ **httpx supports both** - Easy to add async methods later if needed
4. ✅ **Easier testing** - No async test complexity

**Future**: Can add async methods alongside sync ones using the same httpx client.

### Polling Configuration

Following qa-devin best practices:
- **Default interval**: 15 seconds (qa-devin uses 20s)
- **Max interval**: 30 seconds with exponential backoff
- **Timeout**: 30 minutes (qa-devin example)
- **Check**: Use `status_enum` in lowercase

### Structured Output

Following [Devin API docs](https://docs.devin.ai/api-reference/structured-output):
1. ✅ Schema is **embedded in the prompt**, not passed as a parameter
2. ✅ Explicit instructions to update structured output with triggers
3. ✅ Retrieved as raw `dict` from `structured_output` field
4. ✅ Can be validated with Pydantic after retrieval

### Reference

- Official example: `qa-devin` repository by Cognition team
- API docs: https://docs.devin.ai/api-reference/
- Structured output guide: https://docs.devin.ai/api-reference/structured-output

