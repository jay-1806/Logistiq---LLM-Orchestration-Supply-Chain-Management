# Clean to Ship (CTS) Standard Operating Procedures

## 1. Overview

The Clean to Ship (CTS) process ensures that all manufactured units meet quality, 
functional, and cosmetic standards before being shipped to customers. Every unit must 
pass through the CTS workflow before it can be marked as "shippable."

## 2. CTS Inspection Stages

### Stage 1: Functional Testing
- Run the full burn-in test suite (minimum 24 hours for enterprise drives)
- Verify firmware version matches the approved release for the product SKU
- Check SMART health indicators are within acceptable thresholds
- Log all test results in the Quality Management System (QMS)

### Stage 2: Cosmetic Inspection
- Visual inspection of unit casing for scratches, dents, or discoloration
- Verify labeling accuracy (serial number, model number, capacity, regulatory marks)
- Minor cosmetic defects (scratches < 2mm) are acceptable — document and proceed
- Major cosmetic defects require hold and supervisor review

### Stage 3: Packaging Verification
- Confirm anti-static packaging is intact and properly sealed
- Verify packing list matches order specification (quantity, model, accessories)
- Apply shipping label and verify barcode scans correctly

## 3. CTS Hold Procedures

When a unit fails any CTS stage, it is placed on **Quality Hold**:

### Minor Hold (Severity: Minor)
- Examples: labeling error, minor cosmetic scratch within tolerance
- Resolution: Re-inspect, correct label, document and release
- SLA: Resolve within 24 hours

### Major Hold (Severity: Major)
- Examples: firmware mismatch, packaging damage, wrong model in batch
- Resolution: Escalate to engineering team, re-flash firmware or repackage
- SLA: Resolve within 48 hours

### Critical Hold (Severity: Critical)
- Examples: failed burn-in test, ESD damage, data corruption during testing
- Resolution: Full failure analysis required; unit may be scrapped
- SLA: Begin analysis within 4 hours; resolve or scrap decision within 72 hours

## 4. Re-Test Procedures

After a quality hold is resolved, the unit must go through the re-test workflow:

1. Update the hold record with resolution notes
2. Re-run the specific failed test (not full burn-in unless critical)
3. If pass → mark hold as "resolved" → unit returns to shippable inventory
4. If fail again → escalate to next severity level
5. All re-test results must be logged with the original hold ID for traceability

## 5. Metrics and Reporting

| Metric | Target | Frequency |
|--------|--------|-----------|
| First-Pass Yield | > 98% | Daily |
| Average Hold Resolution Time | < 36 hours | Weekly |
| Scrap Rate | < 0.5% | Monthly |
| CTS Throughput | Track actual vs planned | Daily |
