# Decision 3.1: Multiple File Upload Strategy

## Context

Bug 1.8 describes a situation where the backend rejects requests when multiple input types are provided (e.g., both audio and image files). The current implementation has:

**Backend Validation** (agentv5.py lines 1717-1720):
```python
input_count = sum([bool(audio), bool(image), bool(text)])
if input_count > 1:
    raise HTTPException(status_code=400, detail="Please provide only one input type (audio, image, or text)")
```

**Frontend Behavior** (app.js lines 25-41):
- Allows users to select both letter and audio files
- Disables the generate button when both are selected
- Shows error message: "Error: Please select only one input type (letter OR audio, not both)"

## Problem Statement

The current UX is poor: users can select multiple files, but then see an error message and a disabled button. This creates confusion and frustration. The backend also enforces single-input restriction, but the question is whether this restriction should exist at all.

## Options Analysis

### Option A: Remove Backend Validation (Allow Multiple Inputs)

**Implementation:**
- Remove lines 1717-1720 from agentv5.py
- Remove similar validation from api/routes/fir_routes.py (lines 61-65)
- Update processing logic to handle multiple input types simultaneously
- Remove frontend error checking for multiple files

**Pros:**
- Enables richer FIR generation from multiple evidence sources
- Better user experience - users can provide all available evidence
- More flexible system that matches real-world use cases (users often have both written complaints and audio recordings)
- Aligns with the goal of comprehensive FIR documentation

**Cons:**
- Requires significant backend changes to process multiple input types
- Increases complexity in the processing pipeline
- May require changes to the AI model prompts and processing logic
- Potential for increased processing time and resource usage
- Risk of introducing new bugs in the multi-input processing logic
- Unknown behavior of the FIR generation model with multiple inputs

**Complexity:** HIGH
- Backend processing logic needs updates
- Model inference may need adjustments
- Session state management becomes more complex
- Testing surface area increases significantly

### Option B: Improve Frontend UX (Keep Single-Input Restriction)

**Implementation:**
- Update app.js to disable the second file input when one is already selected
- Remove error message logic (prevent the error state from occurring)
- Add visual indication (grayed out/disabled state) for unavailable inputs
- Keep backend validation as-is for security/consistency

**Pros:**
- Minimal code changes (frontend only)
- Preserves existing backend logic and processing pipeline
- Low risk of introducing new bugs
- Clear, predictable user experience
- Maintains simplicity in the system
- Backend validation acts as a security layer

**Cons:**
- Limits user flexibility - cannot provide multiple evidence types
- May not match all real-world use cases
- Users with both audio and written evidence must make multiple submissions

**Complexity:** LOW
- Only frontend changes required
- No backend processing changes
- Minimal testing required
- Clear implementation path

## Decision Criteria

1. **User Experience Impact**: Which option provides better UX?
2. **Implementation Complexity**: Which option is simpler and lower risk?
3. **Business Requirements**: What does the application actually need?
4. **Maintenance Burden**: Which option is easier to maintain long-term?
5. **Risk Assessment**: Which option has lower risk of introducing bugs?

## Analysis

### User Experience
- **Option A**: Better long-term UX if implemented correctly - users can provide all evidence at once
- **Option B**: Better immediate UX - prevents confusion by making restrictions clear upfront

### Implementation Complexity
- **Option A**: High complexity - requires backend refactoring, model adjustments, extensive testing
- **Option B**: Low complexity - simple frontend changes, no backend modifications

### Business Requirements
Based on the bugfix document, the system is designed for FIR (First Information Report) generation. Real-world scenarios may include:
- Written complaint letter (image/PDF)
- Audio recording of complaint
- Text description

However, the current system architecture appears designed for single-input processing. There's no evidence in the codebase that the backend is prepared to handle multiple inputs simultaneously.

### Risk Assessment
- **Option A**: HIGH RISK - touching core processing logic, unknown model behavior with multiple inputs
- **Option B**: LOW RISK - isolated frontend changes, backend remains unchanged

### Current State Analysis
The frontend already has logic to detect multiple file selection (bothFilesSelected), indicating this was a known issue. The current "solution" of showing an error is a band-aid, not a proper fix.

## Recommendation: Option B

**Rationale:**

1. **Surgical Fix Philosophy**: The bugfix spec emphasizes "surgical and minimal" fixes. Option B aligns with this philosophy.

2. **Risk Mitigation**: Option A requires changes to core processing logic with unknown implications. The backend processing pipeline may not be designed for multiple inputs, and changing it could introduce cascading bugs.

3. **Scope Appropriateness**: This is a bugfix spec, not a feature enhancement spec. Adding multi-input support is a feature enhancement that should be designed and tested separately.

4. **Immediate Value**: Option B immediately fixes the poor UX without introducing risk. Users will have a clear, predictable experience.

5. **Future Flexibility**: Choosing Option B now doesn't prevent Option A later. If multi-input support is needed, it can be added as a separate feature with proper design and testing.

6. **Preservation Requirements**: The spec emphasizes preserving existing functionality. Option B preserves all existing processing logic, while Option A risks breaking it.

## Implementation Plan (Option B)

### Frontend Changes (app.js)

1. **Disable file inputs when one is selected:**
```javascript
function updateFilesState() {
  hasFiles = !!(letterFile || audioFile);
  
  const generateBtn = document.getElementById('generate-btn');
  const letterInput = document.getElementById('letter-upload');
  const audioInput = document.getElementById('audio-upload');
  const statusReady = document.getElementById('status-ready');
  
  // Disable the other input when one file is selected
  if (letterInput && audioInput) {
    letterInput.disabled = !!audioFile;
    audioInput.disabled = !!letterFile;
  }
  
  // Enable generate button when exactly one file is selected
  if (generateBtn) {
    generateBtn.disabled = !hasFiles;
    generateBtn.setAttribute('aria-disabled', !hasFiles ? 'true' : 'false');
  }
  
  // Update status message
  if (statusReady) {
    if (hasFiles) {
      statusReady.textContent = 'Ready to generate FIR';
      statusReady.style.color = 'green';
    } else {
      statusReady.textContent = 'Please upload a letter image or audio file';
      statusReady.style.color = '';
    }
  }
}
```

2. **Remove bothFilesSelected logic** - no longer needed since we prevent the state

3. **Add visual styling for disabled inputs** (CSS)

### Backend Changes

**NONE** - Keep existing validation as a security layer

## Success Criteria

After implementing Option B:
1. Users can select one file type (letter OR audio)
2. When one file is selected, the other input is visually disabled
3. No error messages are shown (the error state is prevented)
4. Generate button is enabled when exactly one file is selected
5. Backend validation remains as a safety net
6. All existing single-file upload functionality continues to work

## Future Considerations

If multi-input support is needed in the future:
1. Create a separate feature spec with proper requirements and design
2. Analyze backend processing pipeline for multi-input support
3. Test model behavior with multiple input types
4. Design proper session state management for multiple inputs
5. Implement comprehensive testing strategy
6. Consider UI/UX for multi-input scenarios (progress tracking, error handling)

## Conclusion

**Decision: Implement Option B - Improve Frontend UX to prevent multiple file selection**

This decision prioritizes:
- Low risk and surgical fixes (aligned with bugfix spec philosophy)
- Immediate UX improvement without backend changes
- Preservation of existing functionality
- Clear path forward for future enhancements if needed

The decision is documented and ready for implementation in task 3.2.
