# Quality Inspection Manual

## 1. Incoming Material Inspection

All raw materials and components must be inspected upon receipt:

### Visual Inspection Checklist
- [ ] Packaging is intact, no signs of damage during transit
- [ ] Quantity matches purchase order
- [ ] Part numbers match specification
- [ ] No visible defects (corrosion, discoloration, physical damage)

### Sampling Plan
- Lots < 100 units: Inspect 100%
- Lots 100-500 units: Inspect 20% (random sample)
- Lots > 500 units: Inspect 10% (random sample, minimum 50 units)
- Any sample failure → inspect entire lot

## 2. In-Process Quality Checks

### Manufacturing Line Checks
- Temperature and humidity monitoring (continuous)
- Torque verification on assembly stations (every 50 units)
- Solder joint inspection via AOI (Automated Optical Inspection) — 100%
- Electrical continuity test — 100%

### Statistical Process Control (SPC)
- Monitor Cpk for critical dimensions — target Cpk > 1.33
- Control charts updated every shift
- Out-of-control signals trigger immediate line stop and investigation

## 3. Final Quality Audit

Before a batch enters the CTS workflow:

1. Pull 5% random sample from completed batch
2. Run full functional test suite
3. Perform cosmetic inspection per CTS Stage 2 criteria
4. If any sample unit fails → hold entire batch for review
5. Batch release requires Quality Engineer sign-off

## 4. Non-Conformance Reporting (NCR)

When a defect is found at any stage:

1. **Contain**: Isolate defective units immediately
2. **Document**: Create NCR in QMS with:
   - Defect description and photos
   - Quantity affected
   - Root cause category (material, process, human, equipment)
3. **Correct**: Implement immediate corrective action
4. **Prevent**: Update work instructions or process parameters to prevent recurrence
5. **Verify**: Confirm corrective action is effective after next production run

## 5. Key Quality Metrics

| Metric | Target | Escalation Threshold |
|--------|--------|---------------------|
| Incoming Inspection Pass Rate | > 99% | < 97% → escalate to supplier |
| In-Process Defect Rate | < 200 DPPM | > 500 DPPM → line stop |
| Final Audit Pass Rate | > 99.5% | < 98% → production hold |
| Customer Return Rate | < 0.1% | > 0.3% → root cause investigation |
| MTBF (Mean Time Between Failures) | > 2M hours | < 1.5M hours → design review |
