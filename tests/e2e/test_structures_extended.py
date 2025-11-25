#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extended Water Structures Testing
Test various configurations for gates, pumps, and weirs
"""

import requests
import time
from datetime import datetime

BACKEND_URL = "http://localhost:8002"

def run_simulation(name, config):
    """Run a simulation and return result"""
    try:
        start = time.time()
        resp = requests.post(
            f"{BACKEND_URL}/api/structures/simulate-canal-with-structure",
            json=config, timeout=120
        )
        duration = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", data)
            if results.get("status") == "completed":
                return "OK", duration, results.get("metrics", {})
            return "FAIL", duration, None
        return "ERR", 0, None
    except Exception as e:
        return "ERR", 0, str(e)[:30]

def make_canal_config(L=1000, W=10, S=0.001, n=0.015, nx=100):
    return {"length": L, "width": W, "slope": S, "manning_n": n, "grid_nx": nx}

def make_boundaries(up_type="Q", up_val=50, down_type="h", down_val=3):
    return {
        "upstream": {"type": up_type, "value": up_val},
        "downstream": {"type": down_type, "value": down_val}
    }

def test_gate_variations():
    """Test various gate configurations"""
    print("\n" + "="*60)
    print("  Gate Variations Testing")
    print("="*60)
    
    cases = [
        # (name, opening, width, upstream_h, downstream_h)
        ("Small opening", 0.5, 5, 6, 2),
        ("Medium opening", 2.0, 8, 6, 3),
        ("Large opening", 4.0, 10, 8, 4),
        ("Wide gate", 2.0, 15, 6, 3),
        ("Narrow gate", 1.0, 3, 5, 2),
        ("High head diff", 2.0, 8, 10, 2),
        ("Low head diff", 2.0, 8, 5, 4),
    ]
    
    results = []
    for name, opening, width, h_up, h_down in cases:
        config = {
            "simulation_type": "steady",
            "canal": make_canal_config(),
            "structure_type": "gate",
            "structure": {
                "position": 500,
                "parameters": {
                    "type": "sluice",
                    "width": width,
                    "opening": opening,
                    "discharge_coeff": 0.6
                }
            },
            "boundaries": make_boundaries("h", h_up, "h", h_down),
            "metadata": {"title": name}
        }
        
        status, dur, metrics = run_simulation(name, config)
        results.append((name, status, dur))
        
        icon = "+" if status == "OK" else "-"
        print(f"  [{icon}] {name}: {status} ({dur:.1f}s)")
    
    passed = sum(1 for _, s, _ in results if s == "OK")
    print(f"\n  Gate tests: {passed}/{len(results)} passed")
    return results

def test_pump_variations():
    """Test various pump configurations"""
    print("\n" + "="*60)
    print("  Pump Variations Testing")
    print("="*60)
    
    cases = [
        # (name, flow_rate, head, position)
        ("Small pump", 5, 10, 500),
        ("Medium pump", 15, 20, 500),
        ("Large pump", 50, 30, 500),
        ("Upstream pump", 10, 15, 200),
        ("Downstream pump", 10, 15, 800),
        ("High head", 10, 50, 500),
        ("Low head", 10, 5, 500),
    ]
    
    results = []
    for name, flow, head, pos in cases:
        config = {
            "simulation_type": "steady",
            "canal": make_canal_config(),
            "structure_type": "pump",
            "structure": {
                "position": pos,
                "parameters": {
                    "flow_rate": flow,
                    "head": head,
                    "name": f"Pump-{name}"
                }
            },
            "boundaries": make_boundaries("h", 5, "h", 4),
            "metadata": {"title": name}
        }
        
        status, dur, metrics = run_simulation(name, config)
        results.append((name, status, dur))
        
        icon = "+" if status == "OK" else "-"
        print(f"  [{icon}] {name}: {status} ({dur:.1f}s)")
    
    passed = sum(1 for _, s, _ in results if s == "OK")
    print(f"\n  Pump tests: {passed}/{len(results)} passed")
    return results

def test_weir_variations():
    """Test various weir configurations"""
    print("\n" + "="*60)
    print("  Weir Variations Testing")
    print("="*60)
    
    cases = [
        # (name, crest_height, width, Q_upstream)
        ("Low weir", 0.5, 10, 30),
        ("Medium weir", 1.5, 10, 50),
        ("High weir", 3.0, 10, 80),
        ("Wide weir", 1.5, 20, 100),
        ("Narrow weir", 1.5, 5, 30),
        ("High flow", 1.5, 10, 150),
        ("Low flow", 1.5, 10, 20),
    ]
    
    results = []
    for name, crest, width, Q in cases:
        config = {
            "simulation_type": "steady",
            "canal": make_canal_config(W=max(width+2, 10)),
            "structure_type": "weir",
            "structure": {
                "position": 500,
                "parameters": {
                    "type": "broad_crested",
                    "crest_height": crest,
                    "width": width,
                    "discharge_coeff": 1.7
                }
            },
            "boundaries": make_boundaries("Q", Q, "h", 3),
            "metadata": {"title": name}
        }
        
        status, dur, metrics = run_simulation(name, config)
        results.append((name, status, dur))
        
        icon = "+" if status == "OK" else "-"
        print(f"  [{icon}] {name}: {status} ({dur:.1f}s)")
    
    passed = sum(1 for _, s, _ in results if s == "OK")
    print(f"\n  Weir tests: {passed}/{len(results)} passed")
    return results

def test_boundary_variations():
    """Test various boundary condition combinations"""
    print("\n" + "="*60)
    print("  Boundary Conditions Testing")
    print("="*60)
    
    cases = [
        # (name, up_type, up_val, down_type, down_val)
        ("Q-h standard", "Q", 50, "h", 3),
        ("h-h same", "h", 5, "h", 5),
        ("h-h diff", "h", 8, "h", 4),
        ("Q low", "Q", 10, "h", 2),
        ("Q high", "Q", 200, "h", 5),
        ("h high upstream", "h", 10, "h", 3),
        ("h low downstream", "Q", 50, "h", 1.5),
    ]
    
    results = []
    for name, up_t, up_v, down_t, down_v in cases:
        config = {
            "simulation_type": "steady",
            "canal": make_canal_config(),
            "structure_type": "none",
            "structure": {"position": 0, "parameters": {}},
            "boundaries": make_boundaries(up_t, up_v, down_t, down_v),
            "metadata": {"title": name}
        }
        
        status, dur, metrics = run_simulation(name, config)
        results.append((name, status, dur))
        
        icon = "+" if status == "OK" else "-"
        print(f"  [{icon}] {name}: {status} ({dur:.1f}s)")
    
    passed = sum(1 for _, s, _ in results if s == "OK")
    print(f"\n  Boundary tests: {passed}/{len(results)} passed")
    return results

def main():
    print("\n" + "="*70)
    print("  HydroClaude Extended Structures E2E Test")
    print("  Testing various configurations")
    print("="*70)
    
    start_time = time.time()
    
    all_results = []
    
    # Run all tests
    all_results.extend(test_gate_variations())
    all_results.extend(test_pump_variations())
    all_results.extend(test_weir_variations())
    all_results.extend(test_boundary_variations())
    
    # Summary
    total_time = time.time() - start_time
    passed = sum(1 for _, s, _ in all_results if s == "OK")
    total = len(all_results)
    
    print("\n" + "="*70)
    print("  Final Summary")
    print("="*70)
    print(f"  Total tests: {total}")
    print(f"  Passed: {passed} ({passed/total*100:.0f}%)")
    print(f"  Failed: {total - passed}")
    print(f"  Total time: {total_time:.0f}s ({total_time/60:.1f} min)")
    print("="*70)

if __name__ == "__main__":
    main()

