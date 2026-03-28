# HydroClaude Steady-State MAE Summary

**Date**: 2026-03-28 | **Commit**: f6b0608c | **Target**: MAE < 0.15m (PASS)

## Results: 45/45 PASS (100%)

| # | Case | Profile | Q(m3/s) | XS | MAE(m) | Max(m) | Med(m) | Note |
|---|------|---------|---------|-----|--------|--------|--------|------|
| 1 | Chapter 4 Example Data | 10 yr | 2.8 | 10 | 0.050 | 0.185 | 0.007 | |
| 2 | Chapter 4 Example Data | 50 yr | 14.2 | 10 | 0.042 | 0.167 | 0.016 | |
| 3 | Chapter 4 Example Data | 100 yr | 42.5 | 10 | 0.037 | 0.103 | 0.030 | |
| 4 | ConSpan Culvert | 5 yr | 7.1 | 10 | 0.016 | 0.038 | 0.011 | |
| 5 | ConSpan Culvert | 10 yr | 11.3 | 10 | 0.013 | 0.028 | 0.010 | |
| 6 | ConSpan Culvert | 25 yr | 17.0 | 10 | 0.007 | 0.021 | 0.004 | |
| 7 | ConSpan Culvert | 50 yr | 28.3 | 10 | 0.013 | 0.043 | 0.014 | |
| 8 | Example 10 - Stream Junction | 10 yr | 31.1 | 19 | 0.066 | 0.107 | 0.090 | |
| 9 | Example 11 - Bridge Scour | PF 1 | 849.5 | 9 | 0.101 | 0.305 | 0.092 | bridge scour model missing |
| 10 | Example 12 - Inline Structure | PF#1 | 141.6 | 35 | 0.098 | 0.118 | 0.117 | |
| 11 | Example 12 - Inline Structure | PF#2 | 283.2 | 35 | 0.056 | 0.075 | 0.068 | |
| 12 | Example 12 - Inline Structure | PF#3 | 566.3 | 35 | 0.013 | 0.020 | 0.017 | |
| 13 | Example 12 - Inline Structure | PF#4 | 849.5 | 35 | 0.028 | 0.039 | 0.037 | |
| 14 | Example 12 - Inline Structure | PF#5 | 1132.7 | 35 | 0.037 | 0.071 | 0.041 | |
| 15 | Example 12 - Inline Structure | PF#6 | 1415.8 | 35 | 0.105 | 0.160 | 0.131 | gate Q overestimate 15% |
| 16 | Example 12 - Inline Structure | PF#7 | 2123.8 | 35 | 0.056 | 0.106 | 0.062 | |
| 17 | Example 13 - Singler Bridge (WSPRO) | 50 yr | 707.9 | 42 | 0.021 | 0.118 | 0.003 | |
| 18 | Example 13 - Singler Bridge (WSPRO) | 100 yr | 892.0 | 42 | 0.034 | 0.180 | 0.006 | |
| 19 | Example 14 - Ice Covered River | PF#1 | 7.4 | 22 | 0.139 | 0.218 | 0.159 | A/P geometry diff |
| 20 | Example 15 - Split Flow (Lateral Weir) | PF#1 | 42.5 | 23 | 0.030 | 0.115 | 0.012 | |
| 21 | Example 15 - Split Flow (Lateral Weir) | PF 2 | 141.6 | 23 | 0.056 | 0.233 | 0.019 | |
| 22 | Example 15 - Split Flow (Lateral Weir) | PF 3 | 424.8 | 23 | 0.134 | 0.428 | 0.124 | high-Q De Marchi limit |
| 23 | Example 16 - Channel Modification | 100 yr | 254.9 | 12 | 0.114 | 0.546 | 0.062 | mixed flow false trigger |
| 24 | Example 1 - Critical Creek | 100 yr | 254.9 | 12 | 0.088 | 0.300 | 0.026 | |
| 25 | Example 2 - Beaver Creek | 25 yr | 141.6 | 14 | 0.018 | 0.075 | 0.011 | |
| 26 | Example 2 - Beaver Creek | 100 yr | 283.2 | 14 | 0.032 | 0.127 | 0.022 | |
| 27 | Example 2 - Beaver Creek | May '74 flood | 396.4 | 14 | 0.041 | 0.103 | 0.033 | |
| 28 | Example 3 - Single Culvert | 5 yr | 7.1 | 10 | 0.010 | 0.027 | 0.013 | |
| 29 | Example 3 - Single Culvert | 10 yr | 11.3 | 10 | 0.017 | 0.047 | 0.023 | |
| 30 | Example 3 - Single Culvert | 25 yr | 17.0 | 10 | 0.071 | 0.144 | 0.068 | |
| 31 | Example 4 - Multiple Culverts | 5 yr | 7.1 | 10 | 0.004 | 0.010 | 0.005 | |
| 32 | Example 4 - Multiple Culverts | 10 yr | 11.3 | 10 | 0.005 | 0.016 | 0.005 | |
| 33 | Example 4 - Multiple Culverts | 25 yr | 17.0 | 10 | 0.010 | 0.030 | 0.013 | |
| 34 | Example 5 - Multiple Openings | 25 yr | 141.6 | 15 | 0.008 | 0.022 | 0.005 | |
| 35 | Example 5 - Multiple Openings | 100 yr | 283.2 | 15 | 0.017 | 0.065 | 0.013 | |
| 36 | Example 5 - Multiple Openings | May '74 flood | 396.4 | 15 | 0.049 | 0.164 | 0.037 | |
| 37 | Example 6 - Floodway Determination | PF#1 | 396.4 | 12 | 0.060 | 0.157 | 0.051 | |
| 38 | Example 6 - Floodway Determination | PF#2 | 396.4 | 12 | 0.147 | 0.264 | 0.168 | encroachment needed |
| 39 | Example 7 - Multiple Plans | 100 yr | 115.2 | 80 | 0.089 | 0.326 | 0.033 | |
| 40 | Example 8 - Looped Network | 10 yr | 3.7 | 26 | 0.009 | 0.038 | 0.005 | |
| 41 | Example 8 - Looped Network | 50 yr | 9.9 | 26 | 0.011 | 0.046 | 0.009 | |
| 42 | Example 8 - Looped Network | 100 yr | 12.5 | 26 | 0.011 | 0.039 | 0.010 | |
| 43 | Example 9 - Mixed Flow Analysis | 100 yr | 90.6 | 20 | 0.057 | 0.315 | 0.041 | |
| 44 | Mixed Flow Regime Channel | PF 1 | 14.2 | 19 | 0.001 | 0.001 | 0.000 | |
| 45 | Mixed Flow Regime Channel | PF 2 | 28.3 | 19 | 0.001 | 0.002 | 0.001 | |

## Statistics

| Metric | Value |
|--------|-------|
| Total profiles | 45 |
| PASS (< 0.15m) | 45/45 (100%) |
| Mean MAE | 0.0449 m |
| Median MAE | 0.0339 m |
| Std MAE | 0.0397 m |
| Best MAE | 0.0005 m (Mixed Flow PF1) |
| Worst MAE | 0.1472 m (Example 6 PF#2) |
| MAE < 0.05m | 29/45 (64%) |
| MAE < 0.10m | 39/45 (87%) |

## MAE > 0.10m Root Causes (6 cases)

| Case | MAE | Root Cause | Fixable? |
|------|-----|------------|----------|
| Ex6 PF#2 | 0.147 | Floodway encroachment not implemented (Method 4) | Medium - need iterative solver |
| Ex14 | 0.139 | A/P geometry diff (Sabaneev formula verified correct) | No - fundamental geometry |
| Ex15 PF3 | 0.134 | High-Q lateral weir De Marchi accuracy | Hard - algorithm limit |
| Ex16 | 0.114 | Mixed flow detection false trigger (steep but subcritical) | Medium - solver architecture |
| Ex12 PF#6 | 0.105 | Fully-open gate Q overestimate 15% | Medium - TRM equation detail |
| Ex11 | 0.101 | Bridge scour model missing | No - not implemented |

## Coverage

- 19 HEC-RAS example cases, 45 flow profiles
- Structure types: culverts, bridges, inline structures (gates+weirs), lateral weirs
- Flow regimes: subcritical, supercritical, mixed flow
- Network types: single reach, looped network, split flow junction
- Special features: ice cover, floodway encroachment, channel modification
