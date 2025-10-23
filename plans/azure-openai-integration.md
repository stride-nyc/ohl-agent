# Azure OpenAI Integration - Implementation Plan

## Goal
Add Azure OpenAI as a supported LLM provider to ohl-agent, enabling users to configure and use Azure-hosted OpenAI models through the existing provider abstraction.

## Analysis Summary
- **Current Architecture**: Provider-based routing via `load_chat_model()` in `utils.py`
- **Pattern**: `provider/model-name` (e.g., `anthropic/claude-3-5-sonnet-20241022`)
- **Abstraction Quality**: Excellent - single point of control, clean separation
- **LangChain Support**: `AzureChatOpenAI` class available in `langchain-openai` (already installed)

## Integration Strategy

### End-to-End Data Flow
```
1. User sets .env variables:
   - AZURE_OPENAI_API_KEY
   - AZURE_OPENAI_ENDPOINT
   - AZURE_OPENAI_API_VERSION
   - LLM_MODEL=azure/deployment-name

2. Configuration.from_runnable_config() or load_from_langgraph_json()
   ↓ Loads azure_* fields from env

3. graph.py calls load_chat_model(model_name, config)
   ↓ Passes Azure config

4. utils.py:load_chat_model() parses "azure/deployment-name"
   ↓ Routes to Azure provider case

5. AzureChatOpenAI instantiated with:
   - azure_endpoint
   - api_key
   - api_version
   - azure_deployment (from model_name)
   ↓

6. Model.bind_tools(TOOLS) - same as other providers
   ↓

7. model.ainvoke() - standard LangChain interface
```

### Touch Points
1. **`src/react_agent/utils.py`** - Add Azure provider case
2. **`src/react_agent/configuration.py`** - Add Azure config fields
3. **`src/react_agent/graph.py`** - Pass Azure config to load_chat_model (minor change)
4. **`.env.example`** - Add Azure environment variable examples
5. **`README.md`** (optional) - Document Azure support

### Backward Compatibility
- ✅ No breaking changes - additive only
- ✅ Existing providers (anthropic, openai, openrouter) unchanged
- ✅ Existing env vars unchanged
- ✅ Default behavior unchanged (still uses LLM_MODEL env var)

### File Organization Consistency
- Follow existing patterns in utils.py (elif chain)
- Follow existing patterns in configuration.py (field with metadata)
- Follow existing naming conventions (snake_case, descriptive)

---

## Implementation Steps (TDD Approach)

### Step 1: Add Azure Configuration Fields
**File**: `src/react_agent/configuration.py`

**Test Strategy**:
- Write test for Configuration dataclass with Azure fields
- Test default values from environment variables
- Test field metadata descriptions

**Implementation**:
- Add `azure_endpoint` field (default from `AZURE_OPENAI_ENDPOINT` env var)
- Add `azure_api_version` field (default from `AZURE_OPENAI_API_VERSION` env var, fallback to `"2024-02-15-preview"`)
- Add `azure_deployment` field (optional, default from `AZURE_OPENAI_DEPLOYMENT` env var)

**Acceptance Criteria**:
- [ ] Configuration dataclass has 3 new Azure fields
- [ ] Each field has descriptive metadata
- [ ] Environment variable fallbacks work correctly
- [ ] Tests pass for config loading with/without Azure env vars

**Definition of Done**:
- Tests written and passing
- Code follows existing field pattern in configuration.py
- No changes to existing fields

**Complexity**: LOW - Simple dataclass field additions

---

### Step 2: Add Azure Provider to Model Loader
**File**: `src/react_agent/utils.py`

**Test Strategy**:
- Write test for `load_chat_model("azure/gpt-4", azure_config)`
- Test that AzureChatOpenAI is instantiated with correct parameters
- Test error handling when Azure config is missing
- Test logging output for Azure provider

**Implementation**:
- Import `AzureChatOpenAI` from `langchain_openai`
- Add `elif provider == "azure":` case after openrouter
- Extract deployment name from model string
- Retrieve Azure API key from environment
- Instantiate AzureChatOpenAI with:
  - `azure_endpoint`
  - `azure_deployment` (from model name or config)
  - `api_key`
  - `api_version`
- Add validation for required Azure parameters
- Add appropriate logging statements

**Acceptance Criteria**:
- [ ] `load_chat_model("azure/deployment-name")` returns AzureChatOpenAI instance
- [ ] All Azure parameters properly passed to constructor
- [ ] Error raised if azure_endpoint is missing
- [ ] Error raised if AZURE_OPENAI_API_KEY is missing
- [ ] Logging shows Azure provider selection
- [ ] Tests pass with mocked AzureChatOpenAI

**Definition of Done**:
- Tests written and passing
- Code follows existing provider pattern (anthropic, openai, openrouter)
- Error messages are clear and actionable
- Logging is consistent with other providers

**Complexity**: MEDIUM - Integration with existing provider abstraction

---

### Step 3: Update Model Loading Call in Graph
**File**: `src/react_agent/graph.py`

**Test Strategy**:
- Write test for call_model node with Azure configuration
- Test that Azure config fields are passed to load_chat_model
- Test integration with existing graph flow

**Implementation**:
- Update `load_chat_model()` call at line 42-45
- Add azure_endpoint, azure_api_version, azure_deployment as parameters
- Extract from configuration object

**Current Code** (lines 42-45):
```python
model = load_chat_model(
    configuration.model,
    configuration.openrouter_base_url
).bind_tools(TOOLS)
```

**Updated Code**:
```python
model = load_chat_model(
    configuration.model,
    openrouter_base_url=configuration.openrouter_base_url,
    azure_endpoint=configuration.azure_endpoint,
    azure_api_version=configuration.azure_api_version,
    azure_deployment=configuration.azure_deployment
).bind_tools(TOOLS)
```

**Acceptance Criteria**:
- [ ] Azure config parameters passed to load_chat_model
- [ ] Backward compatibility maintained for existing providers
- [ ] Tests pass for all providers (anthropic, openai, openrouter, azure)
- [ ] No breaking changes to graph behavior

**Definition of Done**:
- Tests written and passing
- Graph still works with non-Azure providers
- Code is readable and maintainable

**Complexity**: LOW - Simple parameter passing

---

### Step 4: Update load_chat_model Signature
**File**: `src/react_agent/utils.py`

**Test Strategy**:
- Test function signature accepts new Azure parameters
- Test backward compatibility with existing calls
- Test optional parameter defaults

**Implementation**:
- Update function signature (line 14):

**Current**:
```python
def load_chat_model(model_name: str, openrouter_base_url: str | None = None) -> Any:
```

**Updated**:
```python
def load_chat_model(
    model_name: str,
    openrouter_base_url: str | None = None,
    azure_endpoint: str | None = None,
    azure_api_version: str | None = None,
    azure_deployment: str | None = None
) -> Any:
```

- Update docstring to document new parameters

**Acceptance Criteria**:
- [ ] Function accepts Azure parameters
- [ ] All parameters are optional (default None)
- [ ] Docstring updated with parameter descriptions
- [ ] Type hints are correct
- [ ] Backward compatibility maintained

**Definition of Done**:
- Tests pass with old and new signatures
- Docstring is comprehensive
- Type checking passes

**Complexity**: LOW - Signature update only

---

### Step 5: Update Environment Variable Template
**File**: `.env.example`

**Test Strategy**:
- Manual verification that example values are clear
- Verify format matches existing entries

**Implementation**:
- Add Azure OpenAI section after existing provider configs
- Add 4 new environment variables with example values and comments

**New Content**:
```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4  # Optional: default deployment name
```

**Acceptance Criteria**:
- [ ] All 4 Azure env vars documented
- [ ] Example values are realistic
- [ ] Comments explain purpose
- [ ] Format matches existing entries
- [ ] Placement is logical (after other LLM configs)

**Definition of Done**:
- File updated with clear examples
- Comments are helpful
- No other changes to .env.example

**Complexity**: TRIVIAL - Documentation only

---

### Step 6: Integration Testing with Real Azure Endpoint
**File**: Manual testing / integration test script

**Test Strategy**:
- Create test .env with real Azure credentials (not committed)
- Test with actual Azure OpenAI deployment
- Verify end-to-end flow from config to API call
- Test error cases (wrong endpoint, invalid key, etc.)

**Test Cases**:
1. **Happy Path**: Valid Azure config, successful API call
2. **Missing API Key**: Error message is clear
3. **Invalid Endpoint**: Error message is clear
4. **Wrong Deployment Name**: Error message is clear
5. **Tool Binding**: Tools work correctly with Azure provider
6. **Async Invocation**: Async calls work correctly

**Acceptance Criteria**:
- [ ] Can successfully initialize Azure provider with real credentials
- [ ] Can make API call to Azure OpenAI
- [ ] Tools bind correctly to Azure model
- [ ] Async invocation works
- [ ] Error messages are actionable
- [ ] Logging provides useful debugging info

**Definition of Done**:
- Successful end-to-end test with real Azure endpoint
- All error cases handled gracefully
- Logging verified
- No credentials committed to repo

**Complexity**: MEDIUM - Requires real Azure setup

---

### Step 7: Documentation Update (Optional)
**File**: `README.md`

**Test Strategy**:
- Manual review for clarity
- Verify examples are correct
- Check consistency with existing docs

**Implementation**:
- Add Azure OpenAI to list of supported providers
- Add example configuration snippet
- Add troubleshooting section for common Azure issues

**Acceptance Criteria**:
- [ ] Azure listed in supported providers
- [ ] Example configuration included
- [ ] Troubleshooting section helpful
- [ ] Links to Azure OpenAI docs included

**Definition of Done**:
- README updated with Azure information
- Examples tested and verified
- Formatting consistent with existing docs

**Complexity**: TRIVIAL - Documentation only

---

## Testing Strategy Summary

### Unit Tests
- **configuration.py**: Test Azure field defaults and loading
- **utils.py**: Test load_chat_model with Azure provider
  - Test successful instantiation
  - Test parameter passing
  - Test error cases (missing config, invalid params)
  - Test logging output

### Integration Tests
- **graph.py**: Test call_model node with Azure configuration
- **End-to-End**: Test full flow from .env → config → model → API call

### Test Organization
- Add tests to existing test file structure (assuming pytest)
- Mock AzureChatOpenAI for unit tests
- Use real Azure endpoint for integration tests (manual/optional)

### Red-Green-TDD Discipline
1. **Red**: Write failing test for Azure config field
2. **Green**: Add field to Configuration dataclass
3. **Refactor**: Ensure consistent with other fields

Repeat for each step.

---

## Opportunities for Batched TDD

### Batch 1: Configuration (Steps 1 + 4)
- Write all configuration-related tests together
- Implement all config fields and function signature updates
- Single commit: "Add Azure OpenAI configuration support"

### Batch 2: Provider Implementation (Steps 2 + 3)
- Write all provider routing tests together
- Implement Azure case in utils.py
- Update graph.py to pass config
- Single commit: "Implement Azure OpenAI provider in model loader"

### Batch 3: Documentation (Steps 5 + 7)
- Update .env.example
- Update README.md
- Single commit: "Document Azure OpenAI configuration"

---

## Risk Areas & Mitigation

### Risk 1: Azure-Specific API Version Changes
**Impact**: MEDIUM - Azure API versions change frequently
**Mitigation**:
- Use stable API version as default (`2024-02-15-preview`)
- Make api_version configurable via env var
- Document where to find latest API versions

### Risk 2: Deployment Name Confusion
**Impact**: MEDIUM - Users may confuse Azure deployment names with model names
**Mitigation**:
- Clear documentation explaining Azure deployment vs model name
- Descriptive error messages when deployment not found
- Example in .env.example showing deployment name

### Risk 3: Missing Dependencies
**Impact**: LOW - AzureChatOpenAI might need additional deps
**Mitigation**:
- Verify langchain-openai includes Azure support (it does)
- Test imports before implementing
- Add dependency check in error message if needed

### Risk 4: Authentication Edge Cases
**Impact**: MEDIUM - Azure supports multiple auth methods (API key, Azure AD)
**Mitigation**:
- Start with API key auth (simplest)
- Document Azure AD support as future enhancement
- Clear error message if auth fails

### Risk 5: Backward Compatibility Break
**Impact**: HIGH - Existing users should not be affected
**Mitigation**:
- All changes are additive (no modifications to existing code paths)
- Existing function signatures remain backward compatible (new params are optional)
- Extensive testing with existing providers

---

## Rollback Approach

### If Azure Implementation Fails
1. **Revert Commits**: Use git revert on Azure-specific commits
2. **Remove Azure Case**: Comment out Azure provider case in utils.py
3. **Remove Config Fields**: Azure fields are optional, so removing them is safe
4. **No Impact on Existing Providers**: Anthropic, OpenAI, OpenRouter continue working

### Safe Rollback Points
- After Step 1: Config fields added but not used
- After Step 2: Azure provider added but not documented
- After Step 6: Full implementation, can disable via config

### Rollback Testing
- Verify existing providers still work after rollback
- Verify no Azure-specific errors appear in logs
- Verify .env.example still has Azure section (for future reference)

---

## Definition of Done (Overall)

### Functional Requirements
- [ ] Azure OpenAI can be configured via environment variables
- [ ] `LLM_MODEL=azure/deployment-name` pattern works
- [ ] Azure models can make successful API calls
- [ ] Tools bind correctly to Azure models
- [ ] Error messages are clear and actionable

### Testing Requirements
- [ ] Unit tests pass for all new code
- [ ] Integration tests pass (manual Azure endpoint test)
- [ ] Existing provider tests still pass (no regressions)
- [ ] Code coverage maintained or improved

### Code Quality Requirements
- [ ] Code follows existing patterns and conventions
- [ ] Type hints are complete and correct
- [ ] Logging is consistent with other providers
- [ ] Docstrings are comprehensive

### Documentation Requirements
- [ ] .env.example updated with Azure variables
- [ ] README.md updated (optional but recommended)
- [ ] Code comments explain Azure-specific logic

### Process Requirements
- [ ] TDD discipline followed (red-green-refactor)
- [ ] Each commit is atomic and reversible
- [ ] No credentials committed to repository
- [ ] Git history is clean and descriptive

---

## Process Checkpoints

### After Each Step
- [ ] Verify tests were written before implementation (Red phase)
- [ ] Verify minimal code added to pass tests (Green phase)
- [ ] Verify code was refactored for clarity (Refactor phase)
- [ ] Verify commit message is descriptive
- [ ] Verify no unintended side effects

### Complexity Verification
- [ ] If tests become complex, break step into smaller increments
- [ ] If implementation takes >3 iterations to green, simplify
- [ ] If step touches >2 files, consider splitting

### Model Selection Verification
This plan is appropriate for:
- Sonnet 4.5: Steps 1-7 (all steps)
- Haiku 3.5: Steps 5, 7 (documentation only)

---

## Estimated Effort

| Step | Description | Complexity | Est. Time |
|------|-------------|------------|-----------|
| 1 | Add Azure config fields | LOW | 15 min |
| 2 | Add Azure provider case | MEDIUM | 30 min |
| 3 | Update graph.py call | LOW | 10 min |
| 4 | Update function signature | LOW | 10 min |
| 5 | Update .env.example | TRIVIAL | 5 min |
| 6 | Integration testing | MEDIUM | 30 min |
| 7 | Update README (optional) | TRIVIAL | 15 min |

**Total Estimated Time**: 1.5 - 2 hours (including testing)

---

## Success Metrics

- [ ] Azure provider successfully added with <50 lines of new code
- [ ] Zero breaking changes to existing providers
- [ ] All tests pass (existing + new)
- [ ] Documentation is clear and comprehensive
- [ ] Code review identifies no issues
- [ ] Integration test with real Azure endpoint succeeds

---

## Next Steps

1. Review this plan for completeness
2. Gather Azure credentials (endpoint, API key, deployment name)
3. Begin Step 1: Add Azure configuration fields
4. Follow TDD discipline throughout
5. Request code review after Step 6
6. Merge to main branch after approval

---

## Notes

- This plan is verbose and optimized for AI execution
- Each step is designed to be atomic and independently testable
- Backward compatibility is maintained throughout
- Rollback is safe at any point
- The existing provider abstraction makes this implementation straightforward

---

**Plan Created**: 2025-10-22
**Framework**: Human-AI PDCA Collaboration Process
**Author**: Claude Sonnet 4.5
