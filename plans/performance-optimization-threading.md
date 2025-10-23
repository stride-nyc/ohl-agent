# Implementation Plan: ohl-agent Performance Optimization

## Goal
Reduce agent response time from 36.82s to <10s by:
1. Adding stateful checkpointer for cross-request efficiency
2. Constraining response length to reduce output token generation
3. Enabling proper thread API usage in client (deferred to last)

## Problem Analysis

### Root Causes Identified

**Issue #1: No Checkpointer** (graph.py:126-133)
- State NOT persisted between requests
- Thread endpoint called but no checkpointer configured
- Result: State lost after each run

**Issue #2: Thread API Misuse** (human-moderated-chat-prototype)
- Thread endpoint used but thread_id not in config.configurable
- Should be: `configurable: {thread_id: threadId}`
- Result: LangGraph creates NEW thread every time

**Issue #3: System Prompt Repetition** (Within-Run)
- 7,863 tokens sent on EVERY call_model iteration
- Evidence: Loop 1: 8,049 → Loop 2: 8,535 → Loop 3: 9,542 tokens
- Result: 23,589 wasted tokens (90% of input)

**Issue #4: Overly Verbose Responses**
- 34.55 seconds to generate 2,819 output tokens
- At ~12 tokens/sec = 2,100+ words
- Expected: 150-300 tokens (100-200 words)

## Token Breakdown (Baseline)

From LangSmith trace 019a12c5-718a-7595-b76f-6daf44ff47a7:

| Iteration | Input Tokens | Output Tokens | Duration | Operation |
|-----------|--------------|---------------|----------|-----------|
| 1 | 8,049 | 20 | 1.57s | Initial reasoning → retrieve_context |
| 2 | 8,535 | 2,819 | 34.55s | Generate response (BOTTLENECK) |
| 3 | 9,542 | 7 | 0.66s | Final confirmation |
| **Total** | **26,126** | **2,846** | **36.82s** | **3 iterations** |

System Prompt Overhead: 7,863 × 3 = 23,589 tokens (90% of input!)

## CRITICAL DISCOVERY

**LangGraph API (`langgraph dev`) provides persistence automatically!**

From the LangGraph platform error:
> "With LangGraph API, persistence is handled automatically by the platform, so providing a custom checkpointer here isn't necessary"

This means:
- ✅ **NO CODE CHANGES NEEDED** for checkpointer in ohl-agent
- ✅ Thread API already works with built-in persistence
- ✅ Just need to fix client to pass `thread_id` correctly
- ✅ Focus on response length constraints for immediate performance gains

## Implementation Steps

### Phase 1: Verify Platform-Provided Persistence (DONE)

#### Step 1: Remove custom checkpointer (COMPLETED)
**File**: `src/react_agent/graph.py`

**Status**: Removed MemorySaver import and checkpointer parameter
**Result**: Graph now uses platform-provided persistence

#### Step 2: Document platform persistence
**File**: `src/react_agent/graph.py`

**Status**: Added comment explaining platform handles persistence
**Result**: Code is cleaner and follows LangGraph best practices

### Phase 2: Response Length Constraint

#### Step 4: Add conciseness constraint to system prompt
**File**: `src/react_agent/prompts.py`

**Test**: Verify prompt includes length constraint
**Implementation**: Add "Maximum 150-200 words" guidance

#### Step 5: Test response length with real request
**Test**: Integration test measuring output tokens

Expected Results:
- Output tokens: 150-400 (vs 2,819 baseline)
- Response duration: 3-5s (vs 34.55s baseline)
- Total request time: 8-10s (vs 36.82s baseline)

#### Step 6: Update README with checkpointer documentation
**File**: `README.md`

Update sections:
- Execution Flow (show checkpointer init)
- Key Features (add "Stateful Threading")
- Troubleshooting (checkpoint issues)

### Phase 3: Validation & Measurement

#### Step 7: End-to-end performance test

Success Criteria:
- ✅ First request: <10s (vs 36.82s) = 73% improvement
- ✅ Output tokens: <500 (vs 2,846) = 82% reduction
- ✅ Second request: <5s
- ✅ Input tokens (second): <8,000 = 69% reduction

### Phase 4: human-moderated-chat-prototype Integration (DEFERRED)

#### Step 8: Fix thread_id in client configuration
**File**: `src/services/ohlAgentClient.ts`

Add `thread_id: threadId` to config.configurable

#### Step 9: Update client tests
**File**: `src/services/__tests__/ohlAgentClient.test.ts`

Verify thread_id in request body

#### Step 10: End-to-end validation in UI

Manual testing in Dashboard

## Expected Performance

### Before
- Total duration: 36.82s
- Input tokens: 26,126
- Output tokens: 2,846

### After
- First request: 8-10s (73% improvement)
- Output tokens: 300 (89% reduction)
- Subsequent requests: 3-5s (85% improvement)

## Rollback Approach

### Checkpointer Issues
1. Remove `checkpointer=checkpointer` from compile()
2. Restart LangGraph dev server

### Response Quality Degradation
1. Revert prompt changes in prompts.py
2. Restart LangGraph dev server

### Client Breaks
1. Revert ohlAgentClient.ts changes
2. Rebuild React app
