# Requirements: Fix Thread API Usage in human-moderated-chat-prototype

## Problem Statement

The React application (`human-moderated-chat-prototype`) currently creates threads via the LangGraph Thread API but **does not pass the thread_id correctly in subsequent requests**. This causes LangGraph to create a NEW thread on every request instead of reusing the existing thread, defeating the purpose of stateful conversations.

**Impact:**
- State is not persisted between requests within a conversation
- Each request starts fresh, wasting tokens resending conversation history
- Platform-provided persistence is not being utilized
- Performance optimization from ohl-agent (73% faster responses) is not realized

## Root Cause

**File:** `src/services/ohlAgentClient.ts` (line ~253)

**Current Implementation:**
```typescript
config: {
  tags: [],
  recursion_limit: 50,
  configurable: {},  // ❌ PROBLEM: Empty object - thread_id not included
},
```

**Expected by LangGraph:**
```typescript
config: {
  tags: [],
  recursion_limit: 50,
  configurable: {
    thread_id: threadId  // ✅ REQUIRED: Must include thread_id
  },
},
```

## LangGraph Thread API Contract

When using the Thread API, LangGraph expects requests to follow this pattern:

### 1. Create Thread (One-Time)
```http
POST http://localhost:2024/threads
Content-Type: application/json

{}
```

**Response:**
```json
{
  "thread_id": "abc-123-def-456",
  "created_at": "2025-01-23T10:00:00Z",
  "metadata": {}
}
```

### 2. Use Thread in Subsequent Requests
```http
POST http://localhost:2024/threads/{thread_id}/runs/stream
Content-Type: application/json

{
  "input": { ... },
  "config": {
    "configurable": {
      "thread_id": "abc-123-def-456"  // ← CRITICAL: Must match thread from step 1
    }
  }
}
```

**Key Point:** The `thread_id` must appear in BOTH:
- The URL path: `/threads/{thread_id}/runs/stream`
- The request body: `config.configurable.thread_id`

## Required Changes

### File: `src/services/ohlAgentClient.ts`

**Location:** Function `fetchProposedResponseWithThread()` at approximately line 240-280

**Current Code (Incorrect):**
```typescript
export async function fetchProposedResponseWithThread(
  threadId: string,
  newMessages: Message[],
  escalation: EscalationContext,
  onProgress?: (message: string) => void
): Promise<ProposedResponse> {
  const apiUrl = getOhlAgentUrl();
  const url = `${apiUrl}/threads/${threadId}/runs/stream`;  // ✅ thread_id in URL

  // Convert Message[] to ConversationMessage[]
  const conversationMessages: ConversationMessage[] = newMessages.map(msg => ({
    role: msg.role as 'member' | 'system',
    content: msg.content,
    timestamp: msg.timestamp
  }));

  const requestBody = {
    input: {
      messages: [{
        content: "Please analyze this escalated conversation and provide guidance for the human agent.",
        type: "human"
      }],
      conversation_history: conversationMessages,
      escalation_context: escalation
    },
    config: {
      tags: [],
      recursion_limit: 50,
      configurable: {},  // ❌ MISSING: thread_id not included
    },
    // ... rest of config
  };

  // ... fetch and SSE parsing logic
}
```

**Required Change (Correct):**
```typescript
export async function fetchProposedResponseWithThread(
  threadId: string,
  newMessages: Message[],
  escalation: EscalationContext,
  onProgress?: (message: string) => void
): Promise<ProposedResponse> {
  const apiUrl = getOhlAgentUrl();
  const url = `${apiUrl}/threads/${threadId}/runs/stream`;  // ✅ thread_id in URL

  // Convert Message[] to ConversationMessage[]
  const conversationMessages: ConversationMessage[] = newMessages.map(msg => ({
    role: msg.role as 'member' | 'system',
    content: msg.content,
    timestamp: msg.timestamp
  }));

  const requestBody = {
    input: {
      messages: [{
        content: "Please analyze this escalated conversation and provide guidance for the human agent.",
        type: "human"
      }],
      conversation_history: conversationMessages,
      escalation_context: escalation
    },
    config: {
      tags: [],
      recursion_limit: 50,
      configurable: {
        thread_id: threadId  // ✅ ADD THIS: Must match thread_id in URL
      },
    },
    // ... rest of config
  };

  // ... fetch and SSE parsing logic
}
```

**Summary of Change:**
```diff
  config: {
    tags: [],
    recursion_limit: 50,
-   configurable: {},
+   configurable: {
+     thread_id: threadId
+   },
  },
```

## Verification Steps

### 1. Code Review
- [ ] Verify `config.configurable.thread_id` is set to the `threadId` parameter
- [ ] Verify `threadId` in URL matches `config.configurable.thread_id`
- [ ] Confirm no other places in the code override `configurable`

### 2. Runtime Testing

**Test Scenario: Multi-Turn Conversation**

1. **Start Dashboard** and load a conversation
2. **First Request:** Agent responds with initial guidance
   - Check browser DevTools → Network → Request payload
   - Verify `config.configurable.thread_id` is present
3. **Add CSR Message:** Post a message from the CSR
4. **Second Request:** Agent responds to new message
   - Check Network → Request payload again
   - Verify SAME thread_id is being used
   - Expected behavior: Agent should have context from first request

**Success Criteria:**
- ✅ `config.configurable.thread_id` appears in request body
- ✅ Same thread_id used across multiple requests in same conversation
- ✅ Agent responses show awareness of previous conversation turns
- ✅ Response time improves on subsequent requests (state cached)

### 3. LangSmith Trace Verification

If LangSmith tracing is enabled:

1. Open LangSmith project for ohl-agent
2. Find trace for the second request in a conversation
3. Check the trace input:
   - Should show `configurable: {thread_id: "..."}`
   - Should show persisted state from previous request
4. Verify input token count is lower than baseline (state not re-sent)

**Expected Performance:**
- First request: 8-10s (with new response length optimization)
- Second request: 3-5s (state persisted, less to process)

## Testing Strategy

### Unit Tests

**File:** `src/services/__tests__/ohlAgentClient.test.ts`

Add test to verify thread_id in request body:

```typescript
describe('fetchProposedResponseWithThread', () => {
  it('should include thread_id in config.configurable', async () => {
    const mockThreadId = 'test-thread-123';
    const mockMessages: Message[] = [
      { role: 'member', content: 'Hello', timestamp: '2025-01-23T10:00:00Z' }
    ];
    const mockEscalation: EscalationContext = {
      reason: 'test',
      urgency: 'medium',
      member_sentiment: 'neutral'
    };

    // Mock fetch
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        body: mockReadableStream(),
      } as Response)
    );

    await fetchProposedResponseWithThread(
      mockThreadId,
      mockMessages,
      mockEscalation
    );

    // Verify fetch was called with correct body
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/threads/${mockThreadId}/runs/stream`),
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining(`"thread_id":"${mockThreadId}"`)
      })
    );
  });
});
```

### Integration Test

**Manual Test via Dashboard:**

1. **Setup:**
   - Ensure ohl-agent LangGraph server is running (`langgraph dev`)
   - Ensure human-moderated-chat-prototype is running (`npm start`)
   - Open browser DevTools → Network tab

2. **Test Flow:**
   - Load conversation (e.g., `/dashboard/sample_frustrated_member`)
   - Wait for initial agent response
   - Post a CSR message: "I understand your frustration."
   - Wait for patient simulator response
   - Wait for agent's second response

3. **Verify in DevTools:**
   - Filter Network tab for "runs/stream"
   - Click first request → Payload tab
   - Verify: `config.configurable.thread_id` present
   - Click second request → Payload tab
   - Verify: SAME `thread_id` value

4. **Verify Performance:**
   - First request: ~8-10 seconds
   - Second request: ~3-5 seconds (should be faster)

## Edge Cases to Consider

### 1. Thread Creation Failure
**Current Code:** `Dashboard.tsx:121-146`

The app already handles thread creation failure gracefully:
```typescript
try {
  const newThreadId = await createThread();
  setThreadId(newThreadId);
} catch (error) {
  console.error('Failed to create thread:', error);
  // Continue without thread support (non-fatal error)
}
```

**Expected Behavior:** If thread creation fails, `threadId` will be `null` and the app falls back to non-threaded requests.

**Question:** Should we update `fetchProposedResponseWithThread()` to handle `null` threadId?

**Option A (Recommended):** Add guard clause:
```typescript
export async function fetchProposedResponseWithThread(
  threadId: string | null,  // Allow null
  newMessages: Message[],
  escalation: EscalationContext,
  onProgress?: (message: string) => void
): Promise<ProposedResponse> {
  // If no thread, fall back to non-threaded endpoint
  if (!threadId) {
    return fetchProposedResponse(newMessages, escalation, onProgress);
  }

  // ... threaded logic with thread_id in configurable
}
```

**Option B:** Keep current behavior (caller must ensure threadId is non-null).

### 2. Thread Cleanup
**Current Code:** `Dashboard.tsx:137-145`

App already deletes thread on unmount:
```typescript
return () => {
  if (createdThreadId) {
    deleteThread(createdThreadId).catch((error) => {
      console.error('Failed to delete thread on unmount:', error);
      // Non-fatal - thread will expire naturally
    });
  }
};
```

**No changes needed** - this is correct.

### 3. Multiple Concurrent Requests
**Question:** What happens if user triggers multiple requests before first completes?

**Current Behavior:** `Dashboard.tsx:277-309` uses `isLoading` state to disable buttons during requests.

**No changes needed** - UI already prevents concurrent requests.

## Rollback Strategy

If thread_id in configurable causes issues:

### Quick Rollback
```typescript
// Revert to empty configurable
config: {
  tags: [],
  recursion_limit: 50,
  configurable: {},  // Reverted - no thread_id
},
```

**Impact:** App will work but without thread persistence benefits.

### Alternative: Feature Flag
Add environment variable to toggle thread support:
```typescript
// .env.local
REACT_APP_ENABLE_THREADS=true

// ohlAgentClient.ts
config: {
  tags: [],
  recursion_limit: 50,
  configurable: process.env.REACT_APP_ENABLE_THREADS === 'true'
    ? { thread_id: threadId }
    : {},
},
```

## Related Files

Files that interact with threading but likely **don't need changes**:

- ✅ `src/services/threadManager.ts` - Creates/deletes threads (correct as-is)
- ✅ `src/pages/Dashboard.tsx` - Manages thread lifecycle (correct as-is)
- ✅ `src/types/conversation.ts` - Type definitions (no changes needed)

## Success Metrics

After implementing this fix, you should observe:

### Performance
- First request: ~8-10s (down from 36.82s baseline)
- Subsequent requests: ~3-5s (down from ~8-10s)
- **Total improvement:** 85% faster on subsequent requests

### State Persistence
- Agent remembers previous turns in conversation
- No need to resend full conversation history on every request
- Input tokens reduced by ~60-70% on subsequent requests

### User Experience
- Faster responses after initial request
- More coherent multi-turn conversations
- Agent can reference previous guidance

## References

- **LangGraph Thread API Docs:** https://langchain-ai.github.io/langgraph/cloud/reference/api/api_ref.html#tag/threads
- **ohl-agent Implementation Plan:** `plans/performance-optimization-threading.md`
- **ohl-agent Graph Setup:** `src/react_agent/graph.py:126-131` (documents platform persistence)
- **LangGraph Platform Persistence:** Automatic when using `langgraph dev` - no custom checkpointer needed

## Implementation Checklist

- [ ] Update `src/services/ohlAgentClient.ts` to include `thread_id` in `config.configurable`
- [ ] Add unit test verifying thread_id in request body
- [ ] Manual test via Dashboard to verify thread_id appears in DevTools
- [ ] Verify same thread_id used across multiple requests
- [ ] Measure response time improvement on subsequent requests
- [ ] (Optional) Check LangSmith trace to verify state persistence
- [ ] Update relevant documentation or comments in code
- [ ] Commit changes with clear message explaining the fix

## Acceptance Criteria

✅ **Definition of Done:**

1. `config.configurable.thread_id` is set to the `threadId` parameter value
2. Unit test passes verifying thread_id in request body
3. Manual testing shows same thread_id across multiple requests in a conversation
4. Response time for subsequent requests is measurably faster (3-5s vs 8-10s)
5. No console errors or warnings related to threading
6. Code is committed with descriptive commit message

---

**Estimated Effort:** 1-2 hours (mostly testing and verification)

**Priority:** High (unlocks full performance optimization benefits)

**Dependencies:** Requires ohl-agent running with `langgraph dev` (provides automatic persistence)
