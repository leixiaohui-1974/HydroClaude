# Example 08: Load Acceptance Transient Analysis

## Overview

This example demonstrates the behavior of a hydropower plant during **load acceptance** (sudden load increase), which is the opposite scenario of load rejection.

## Scenario

- **Initial condition**: Light load (10 MW)
- **Event at t=5s**: Load suddenly increases to 100 MW
- **System response**: Governor opens guide vanes, speed drops initially, then recovers

## Key Phenomena

### 1. Speed Response
- **Frequency dip**: When load increases, generator speed decreases
- **Governor action**: PID controller detects speed drop and increases guide vane opening
- **Recovery**: Speed gradually returns to rated value (250 rpm)

### 2. Guide Vane Opening
- **Initial**: ~15% opening for 10 MW
- **Transient**: Rapid opening to increase water flow
- **Final**: ~60% opening for 100 MW

### 3. Surge Tank Level
- **Initial**: 480 m
- **Response**: Water level drops as turbine draws more water
- **Recovery**: Level stabilizes at new equilibrium

## Comparison with Load Rejection

| Aspect | Load Rejection (100→0 MW) | Load Acceptance (10→100 MW) |
|--------|---------------------------|------------------------------|
| Speed change | **Overshoot** (↑) | **Undershoot** (↓) |
| Guide vane | Closes rapidly | Opens rapidly |
| Surge tank | Level rises | Level drops |
| Critical risk | Over-speed damage | Under-frequency, stall risk |
| Control challenge | Prevent runaway | Maintain stability |

## System Components

1. **Francis Turbine**: 100 MW, 150 m head, 250 rpm
2. **PID Governor**: Kp=10, Ki=1.0, Kd=0.5, faster rate limit (15%/s)
3. **Surge Tank**: Ø12m simple cylindrical tank
4. **Generator**: GD²=8 MN·m² (high inertia)

## Performance Metrics

- **Speed undershoot**: Should be < 10% (frequency dip tolerance)
- **Recovery time**: Typically 30-60 seconds
- **Final speed deviation**: < 1% at steady state
- **Surge tank**: Level drop should stay within design limits

## Usage

```bash
cd examples/example_08_load_acceptance
PYTHONPATH=../.. python example_08_load_acceptance.py
```

## Output

- Console: Detailed analysis and performance metrics
- Plot: `load_acceptance_transient.png` showing:
  - Speed response
  - Guide vane opening
  - Power output
  - Surge tank level

## Notes

This example demonstrates the importance of:
1. **Adequate spinning reserve**: System must have capacity to accept load
2. **Fast governor response**: Quick guide vane opening prevents excessive frequency dip
3. **Surge tank sizing**: Must handle increased water draw
4. **Grid frequency stability**: Load acceptance affects system frequency

Load acceptance is a critical operating scenario for hydropower plants participating in grid frequency regulation and providing spinning reserve.

## See Also

- **Example 05**: Load rejection transient
- **Example 07**: Multi-unit AGC for coordinated load response
