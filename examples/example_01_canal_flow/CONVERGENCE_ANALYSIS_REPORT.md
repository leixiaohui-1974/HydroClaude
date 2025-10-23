# Canal Flow Examples - Convergence and Stability Analysis Report

**Date:** 2025-10-23
**Analyst:** Claude
**Purpose:** Comprehensive analysis of all scripts for convergence, stability, and physical reasonableness

---

## Executive Summary

Analyzed 14 scripts (01-12) for numerical convergence and physical accuracy. Found:
- ✅ **8 scripts** performing excellently (01-06, 09, 11)
- ⚠️ **1 script** with slow convergence (07)
- ❌ **3 scripts** with serious convergence/stability issues (08, 10, 12)

---

## Detailed Analysis by Script

### ✅ Script 01: Basic Simulation
**Status:** EXCELLENT
**Convergence:** All methods (EXPLICIT, PREISSMANN, HLL) achieve perfect convergence
- Stability score: 100/100 for all methods
- Mass conservation error: 0.00%
- CV (coefficient of variation): < 0.000001%
- **Recommendation:** Use as benchmark for numerical methods

---

### ✅ Script 02: Methods Comparison
**Status:** EXCELLENT
**Convergence:** All three methods show outstanding performance
- Water depth CV: ~0.000003%
- Flow rate CV: ~0.000003%
- Error < 0.00001% for all methods
- **Recommendation:** Demonstrates method equivalence for simple scenarios

---

### ✅ Script 03: IDZ Parameter Identification
**Status:** GOOD
**Convergence:** Transfer function identification successful
- Primary transfer functions: R² > 0.97
- Some weak transfer paths show low R² (e.g., Q→Q: R²=-0.27), which is expected
- Main upstream flow and downstream depth paths well-identified
- **Recommendation:** Use for control system design with caution on weak transfer paths

---

### ✅ Script 04: Boundary Conditions
**Status:** EXCELLENT
**Convergence:** Perfect convergence with excellent mass conservation
- High water level (backwater): error = 0.067%, CV < 0.0001%
- Uniform flow: error = 0.000%, CV < 0.0001%
- Low water level (pump station): error = 0.039%, CV < 0.0001%
- **Note:** Font warnings for Chinese characters are cosmetic only

---

### ✅ Script 05: Step Response
**Status:** EXCELLENT
**Convergence:** All methods converge smoothly to new equilibrium
- EXPLICIT: Final Q_up = 9.9942 m³/s (target: 10.0)
- PREISSMANN: Final Q_up = 9.9728 m³/s
- HLL: Final Q_up = 9.9983 m³/s
- **Recommendation:** HLL shows best final accuracy

---

### ✅ Script 06: Animation
**Status:** EXCELLENT
**Convergence:** Perfect steady state with zero error
- All methods: error = 0.000%
- Water depth: 0.8065 ± 0.000000 m
- Flow rate: 8.0000 ± 0.000000 m³/s
- **Recommendation:** Use for visualization demonstrations

---

### ⚠️ Script 07: Sluice Gate Flow Dynamics
**Status:** ACCEPTABLE with concerns
**Physical Analysis:**

1. **Water depth increase before gate:** ✅ PHYSICALLY REASONABLE
   - Classic backwater effect (M1 curve)
   - Sluice gate acts as flow constriction
   - In subcritical flow, disturbances propagate upstream
   - Water accumulates due to hydraulic resistance
   - **This is fundamental open channel hydraulics**

2. **Flow rate decrease before gate (transient):** ⚠️ PARTIALLY REASONABLE
   - During transient: physically expected due to limited gate capacity
   - Excess inflow accumulates upstream while gate capacity gradually increases
   - **CONCERN:** After 16,000s simulation:
     - Inlet: 14.99 m³/s
     - Gate upstream: 14.5 m³/s
     - Gate downstream: 14.0 m³/s
     - Outlet: 13.96 m³/s
   - Persistent flow gradient suggests very slow convergence or numerical issues

3. **Steady state issues:**
   - Initial steady state shows flow oscillations (should be constant)
   - Flow conservation error: 0.5489% (acceptable but not ideal)
   - Flow rate varies from 10.15 to 9.6 m³/s along canal despite steady conditions

**Recommendation:**
- Increase simulation time to check for full equilibration
- Consider tighter convergence criteria for steady state
- Investigate numerical damping parameters

---

### ❌ Script 08: Optimized Steady Solving
**Status:** MAJOR CONVERGENCE FAILURE
**Critical Issue:** Method 3 completely fails to converge

**Method Comparison:**
- **Method 1 (Standard 0.5%):** ✅ Converges, 501 iterations, error=0.4933%, time=0.85s
- **Method 2 (Relaxed 1%):** ✅ Converges, 501 iterations, error=0.4933%, time=0.85s
- **Method 3 (Optimized init):** ❌ FAILS, 10,000 iterations, error=66.3966%, time=16.94s

**Problem Analysis:**
- Method 3 attempts to use simplified solver for initialization
- Fine solver completely diverges from simplified solver result
- Error increases from reasonable initial state to 66% after 10,000 iterations
- Average flow: 16.64 m³/s when target is 10.0 m³/s

**Recommendation:**
- ❌ DO NOT USE Method 3 in its current form
- Root cause: Incompatibility between simplified and full solver
- Needs fundamental algorithm revision or different initialization strategy

---

### ✅ Script 09: Simple Canal Enhanced
**Status:** GOOD
**Convergence:** Completes successfully with reasonable results
- Initial depth: 5.049 m → Final depth: 5.429 m
- Average flow: 5.041 m³/s
- Smooth progression over 10 time steps
- **Recommendation:** Good for educational/demonstration purposes

---

### ❌ Script 10: Canal Deep Analysis
**Status:** SEVERE NUMERICAL INSTABILITY
**Critical Issues:** Unphysical behavior indicating numerical problems

**Scenario 1: Upstream flow step 5.0 → 8.0 m³/s**

| Time | Upstream Depth | Downstream Depth | Downstream Flow | Physical Reasonableness |
|------|----------------|------------------|-----------------|------------------------|
| 0s | 5.000m | 5.000m | 5.05 m³/s | ✅ Initial state |
| 100s | 4.935m | 5.000m | 9.75 m³/s | ⚠️ Depth drops when inflow increases |
| 250s | 4.063m | 5.000m | **144.55 m³/s** | ❌ EXTREME unphysical spike |
| Final | **3.118m** | 5.000m | - | ❌ Depth drops 1.88m! |

**Physical Analysis:**
- ❌ When upstream inflow INCREASES, upstream depth should INCREASE, not decrease by 1.88m
- ❌ Downstream flow spikes to 144.55 m³/s from 11.79 m³/s (12x increase!)
- ❌ This violates mass conservation and physical principles

**Scenario 2: Downstream water level step 5.0 → 6.0 m**

| Time | Upstream Depth | Downstream Depth | Downstream Flow | Physical Reasonableness |
|------|----------------|------------------|-----------------|------------------------|
| 100s | 4.935m | 6.000m | 9.75 m³/s | ⚠️ Flow increases during depth step |
| 150s | 4.905m | 6.000m | **0.00 m³/s** | ❌ Flow completely stops |
| 200s | 4.626m | 6.000m | **0.00 m³/s** | ❌ Flow still zero |
| 250s | 4.121m | 6.000m | 10.12 m³/s | ⚠️ Sudden restart |
| Final | **3.635m** | 6.000m | - | ❌ Depth drops 1.37m |

**Physical Analysis:**
- ❌ Flow becomes exactly zero at t=150-200s (unphysical for continuous canal)
- ❌ Upstream depth decreases when it should increase due to backwater effect
- ❌ Erratic flow patterns indicate numerical instability

**Root Cause Analysis:**
- Likely issues: CFL condition violation, improper boundary treatment, or solver instability
- Time step may be too large for these transients
- Boundary condition implementation may have bugs

**Recommendation:**
- ❌ DO NOT USE this script for analysis in current state
- Requires fundamental debugging of numerical scheme
- Check: time step size, CFL criterion, boundary condition implementation
- Consider using implicit scheme or smaller time steps

---

### ✅ Script 11: Advanced Structures
**Status:** GOOD
**Convergence:** Acceptable mass conservation errors
- Scenario 1 (three gates): error = 1.3476%
- Scenario 2 (mixed structures): error = 0.0274%
- Scenario 3 (time-varying): Flow reduction 10.00 → 8.84 m³/s
- **Recommendation:** Acceptable for multi-structure scenarios

---

### ❌ Script 12: Advanced Optimized
**Status:** CONVERGENCE FAILURE (Three-gate scenario)
**Issues:** Original method fails for complex scenarios

**Three-gate scenario:**
- Original method (0.5%): ❌ FAILS to converge
  - 10,000 iterations, final error=0.5651%
  - Did not reach convergence criterion
- Optimized method (1%): ✅ Converges
  - 6,501 iterations, error=0.9994%, time=10.92s

**Mixed structures scenario:**
- Original method (0.5%): ✅ Converges (2001 iter, 0.0274%)
- Optimized method (1%): ✅ Converges (1501 iter, 0.7798%, 30% faster)

**Analysis:**
- Three-gate scenario is at numerical stability limit for standard method
- Relaxed tolerance (1%) allows convergence but with higher error
- Trade-off between accuracy and reliability

**Recommendation:**
- For three-gate scenarios: Use optimized method with 1% tolerance
- For simpler scenarios: Original method works well
- Consider adaptive tolerance based on scenario complexity

---

## Summary Table

| Script | Name | Status | Convergence | Mass Error | Issues |
|--------|------|--------|-------------|------------|--------|
| 01 | Basic Simulation | ✅ | Perfect | 0.00% | None |
| 02 | Methods Comparison | ✅ | Excellent | <0.00001% | None |
| 03 | IDZ Identification | ✅ | Good | - | Weak transfer paths expected |
| 04 | Boundary Conditions | ✅ | Perfect | <0.07% | Font warnings only |
| 05 | Step Response | ✅ | Excellent | <0.03% | None |
| 06 | Animation | ✅ | Perfect | 0.00% | None |
| 07 | Sluice Gate | ⚠️ | Slow | 0.55% | Very slow equilibration |
| 08 | Optimized Steady | ❌ | FAIL (M3) | 66.40% | Method 3 diverges |
| 09 | Simple Canal | ✅ | Good | - | None |
| 10 | Deep Analysis | ❌ | Unstable | - | Unphysical results |
| 11 | Advanced Structures | ✅ | Good | <1.35% | Acceptable |
| 12 | Advanced Optimized | ❌ | FAIL (3-gate) | 0.57% | Standard method fails |

---

## Recommendations

### Immediate Actions Required:

1. **Script 08 - Method 3:**
   - Disable or remove Method 3 until fundamental algorithm is fixed
   - Incompatibility between simplified and full solver needs resolution

2. **Script 10 - Deep Analysis:**
   - DO NOT USE for any analysis or decision-making
   - Requires complete debugging of numerical scheme
   - Check time step size, CFL criterion, boundary conditions
   - Consider rewriting with more robust numerical method

3. **Script 12 - Three-gate scenario:**
   - Document that standard method fails for this scenario
   - Recommend using optimized method with 1% tolerance
   - Consider implementing adaptive tolerance mechanism

### Medium Priority:

4. **Script 07 - Sluice Gate:**
   - Extend simulation time to verify full equilibration
   - Tighten steady-state convergence criteria
   - Add convergence rate monitoring
   - Physical phenomena are correct; just needs better numerical handling

### Code Quality Improvements:

5. **All scripts with Chinese labels:**
   - User requested English labels to avoid font issues
   - Many scripts still have Chinese characters causing font warnings
   - Systematically convert all text to English

6. **Convergence monitoring:**
   - Add real-time convergence rate calculation
   - Implement early warning for divergence
   - Add automatic time step adjustment for stability

---

## Physical Phenomena Analysis: Sluice Gate

### Question: Is water depth increase before gate reasonable?
**Answer:** ✅ YES, completely reasonable

This is the classic **M1 backwater curve**:
- Sluice gate creates flow constriction
- Subcritical flow: disturbances propagate upstream
- Water accumulates due to hydraulic resistance
- Depth increases upstream of obstruction
- **Fundamental principle of open channel hydraulics**

### Question: Is flow rate decrease before gate reasonable?
**Answer:** ⚠️ YES during transient, but convergence is too slow

During transient (0-16,000s):
- Gate capacity limited by gate equation: Q = Cd × a × b × √(2gh)
- Upstream flow increases instantly to 15 m³/s
- Gate can only pass ~9.6 m³/s initially based on water depth
- Excess water accumulates, gradually increasing depth and gate capacity
- **This creates spatial flow gradient - physically correct**

Concern:
- After 16,000s, still shows flow gradient (Inlet: 14.99, Outlet: 13.96)
- System should eventually reach uniform flow
- **Slow convergence suggests numerical damping or very long physical time constant**

---

## Conclusion

The codebase demonstrates good numerical methods for most scenarios (scripts 01-06, 09, 11), but has serious issues in advanced scenarios:

- **Production-ready:** Scripts 01-06, 09, 11
- **Use with caution:** Script 07 (extend simulation time)
- **Do not use:** Scripts 08 (Method 3), 10, 12 (three-gate with standard method)

**Overall Assessment:**
- Core algorithms (EXPLICIT, PREISSMANN, HLL) are sound
- Problems arise in complex scenarios with structures
- Needs focused debugging on Scripts 08, 10, 12
- Script 07 needs patience (longer simulation) rather than fixes

---

**Report Generated:** 2025-10-23
**Claude Code Analysis Session**
