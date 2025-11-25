#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HydroClaude Water Structures E2E Test
Test Gate, Pump, Weir and combined simulations
"""

import requests
import time
import json
from datetime import datetime
from pathlib import Path

BACKEND_URL = "http://localhost:8001"
OUTPUT_DIR = Path(__file__).parent / "structures_test_output"
OUTPUT_DIR.mkdir(exist_ok=True)

def log(msg, status="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {"INFO": "[i]", "OK": "[+]", "FAIL": "[-]", "STEP": "[>]"}
    print(f"[{ts}] {icons.get(status, '[?]')} {msg}")

def test_gate_simulation():
    """Test sluice gate simulation"""
    log("Testing Gate Simulation", "STEP")
    
    request = {
        "simulation_type": "steady",
        "canal": {
            "length": 1000,
            "width": 10,
            "slope": 0.001,
            "manning_n": 0.015,
            "grid_nx": 100
        },
        "structure_type": "gate",
        "structure": {
            "position": 500,
            "parameters": {
                "type": "sluice",
                "width": 8.0,
                "opening": 2.0,
                "discharge_coeff": 0.6
            }
        },
        "boundaries": {
            "upstream": {"type": "h", "value": 6.0},
            "downstream": {"type": "h", "value": 3.0}
        },
        "metadata": {"title": "Gate Test"}
    }
    
    try:
        start = time.time()
        resp = requests.post(f"{BACKEND_URL}/api/structures/simulate-canal-with-structure", 
                            json=request, timeout=120)
        duration = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", data)
            metrics = results.get("metrics", {})
            
            if results.get("status") == "completed":
                log(f"Gate: PASSED ({duration:.1f}s)", "OK")
                log(f"  Max depth: {metrics.get('max_depth', 'N/A'):.2f}m")
                log(f"  Gate type: {metrics.get('gate_type', 'N/A')}")
                return True, metrics
            else:
                log(f"Gate: FAILED - {results.get('error', 'Unknown')}", "FAIL")
                return False, None
        else:
            log(f"Gate: HTTP {resp.status_code}", "FAIL")
            return False, None
    except Exception as e:
        log(f"Gate: ERROR - {str(e)[:50]}", "FAIL")
        return False, None

def test_pump_simulation():
    """Test pump station simulation"""
    log("Testing Pump Simulation", "STEP")
    
    request = {
        "simulation_type": "steady",
        "canal": {
            "length": 1000,
            "width": 10,
            "slope": 0.001,
            "manning_n": 0.015,
            "grid_nx": 100
        },
        "structure_type": "pump",
        "structure": {
            "position": 500,
            "parameters": {
                "flow_rate": 10.0,
                "head": 15.0,
                "name": "Pump-01"
            }
        },
        "boundaries": {
            "upstream": {"type": "h", "value": 5.0},
            "downstream": {"type": "h", "value": 4.0}
        },
        "metadata": {"title": "Pump Test"}
    }
    
    try:
        start = time.time()
        resp = requests.post(f"{BACKEND_URL}/api/structures/simulate-canal-with-structure", 
                            json=request, timeout=120)
        duration = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", data)
            metrics = results.get("metrics", {})
            
            if results.get("status") == "completed":
                log(f"Pump: PASSED ({duration:.1f}s)", "OK")
                log(f"  Max depth: {metrics.get('max_depth', 'N/A'):.2f}m")
                log(f"  System type: {metrics.get('system_type', 'N/A')}")
                return True, metrics
            else:
                log(f"Pump: FAILED - {results.get('error', 'Unknown')}", "FAIL")
                return False, None
        else:
            log(f"Pump: HTTP {resp.status_code}", "FAIL")
            return False, None
    except Exception as e:
        log(f"Pump: ERROR - {str(e)[:50]}", "FAIL")
        return False, None

def test_weir_simulation():
    """Test weir simulation"""
    log("Testing Weir Simulation", "STEP")
    
    request = {
        "simulation_type": "steady",
        "canal": {
            "length": 1000,
            "width": 10,
            "slope": 0.001,
            "manning_n": 0.015,
            "grid_nx": 100
        },
        "structure_type": "weir",
        "structure": {
            "position": 500,
            "parameters": {
                "type": "broad_crested",
                "crest_height": 1.5,
                "width": 8.0,
                "discharge_coeff": 1.7
            }
        },
        "boundaries": {
            "upstream": {"type": "Q", "value": 50.0},
            "downstream": {"type": "h", "value": 3.0}
        },
        "metadata": {"title": "Weir Test"}
    }
    
    try:
        start = time.time()
        resp = requests.post(f"{BACKEND_URL}/api/structures/simulate-canal-with-structure", 
                            json=request, timeout=120)
        duration = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", data)
            metrics = results.get("metrics", {})
            
            if results.get("status") == "completed":
                log(f"Weir: PASSED ({duration:.1f}s)", "OK")
                log(f"  Max depth: {metrics.get('max_depth', 'N/A'):.2f}m")
                return True, metrics
            else:
                log(f"Weir: FAILED - {results.get('error', 'Unknown')}", "FAIL")
                return False, None
        else:
            log(f"Weir: HTTP {resp.status_code}", "FAIL")
            return False, None
    except Exception as e:
        log(f"Weir: ERROR - {str(e)[:50]}", "FAIL")
        return False, None

def test_plain_canal():
    """Test plain canal without structures"""
    log("Testing Plain Canal", "STEP")
    
    request = {
        "simulation_type": "steady",
        "canal": {
            "length": 1000,
            "width": 10,
            "slope": 0.001,
            "manning_n": 0.015,
            "grid_nx": 100
        },
        "structure_type": "none",
        "structure": {"position": 0, "parameters": {}},
        "boundaries": {
            "upstream": {"type": "Q", "value": 50.0},
            "downstream": {"type": "h", "value": 3.0}
        },
        "metadata": {"title": "Plain Canal Test"}
    }
    
    try:
        start = time.time()
        resp = requests.post(f"{BACKEND_URL}/api/structures/simulate-canal-with-structure", 
                            json=request, timeout=120)
        duration = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", data)
            metrics = results.get("metrics", {})
            
            if results.get("status") == "completed" and metrics.get("converged"):
                log(f"Plain Canal: PASSED ({duration:.1f}s)", "OK")
                log(f"  Max depth: {metrics.get('max_depth', 0):.2f}m")
                log(f"  Min depth: {metrics.get('min_depth', 0):.2f}m")
                log(f"  Max velocity: {metrics.get('max_velocity', 0):.2f}m/s")
                return True, metrics
            else:
                log(f"Plain Canal: FAILED", "FAIL")
                return False, None
        else:
            log(f"Plain Canal: HTTP {resp.status_code}", "FAIL")
            return False, None
    except Exception as e:
        log(f"Plain Canal: ERROR - {str(e)[:50]}", "FAIL")
        return False, None

def test_individual_structures():
    """Test individual structure calculations"""
    log("Testing Individual Structure APIs", "STEP")
    
    results = {}
    
    # Test pump calculation
    try:
        resp = requests.post(f"{BACKEND_URL}/api/structures/pump", json={
            "pump": {"flow_rate": 10.0, "head": 15.0, "efficiency": 0.8},
            "upstream_level": 5.0,
            "downstream_level": 20.0
        }, timeout=30)
        if resp.status_code == 200:
            log("Individual Pump API: OK", "OK")
            results["pump"] = True
        else:
            log(f"Individual Pump API: HTTP {resp.status_code}", "FAIL")
            results["pump"] = False
    except Exception as e:
        log(f"Individual Pump API: {str(e)[:30]}", "FAIL")
        results["pump"] = False
    
    # Test gate calculation
    try:
        resp = requests.post(f"{BACKEND_URL}/api/structures/gate", json={
            "gate": {"type": "sluice", "width": 5.0, "opening": 2.0, "discharge_coeff": 0.6},
            "upstream_depth": 6.0,
            "downstream_depth": 3.0
        }, timeout=30)
        if resp.status_code == 200:
            log("Individual Gate API: OK", "OK")
            results["gate"] = True
        else:
            log(f"Individual Gate API: HTTP {resp.status_code}", "FAIL")
            results["gate"] = False
    except Exception as e:
        log(f"Individual Gate API: {str(e)[:30]}", "FAIL")
        results["gate"] = False
    
    # Test weir calculation
    try:
        resp = requests.post(f"{BACKEND_URL}/api/structures/weir", json={
            "weir": {"type": "broad_crested", "width": 10.0, "crest_height": 1.5, "discharge_coeff": 1.7},
            "upstream_depth": 4.0
        }, timeout=30)
        if resp.status_code == 200:
            log("Individual Weir API: OK", "OK")
            results["weir"] = True
        else:
            log(f"Individual Weir API: HTTP {resp.status_code}", "FAIL")
            results["weir"] = False
    except Exception as e:
        log(f"Individual Weir API: {str(e)[:30]}", "FAIL")
        results["weir"] = False
    
    return results

def main():
    print("\n" + "="*60)
    print("  HydroClaude Water Structures E2E Test")
    print("="*60 + "\n")
    
    results = {
        "plain_canal": False,
        "gate": False,
        "pump": False,
        "weir": False,
        "individual_apis": {}
    }
    
    # Wait for server
    log("Waiting for server...", "INFO")
    time.sleep(3)
    
    # Test plain canal first
    results["plain_canal"], _ = test_plain_canal()
    print()
    
    # Test structures
    results["gate"], _ = test_gate_simulation()
    print()
    
    results["pump"], _ = test_pump_simulation()
    print()
    
    results["weir"], _ = test_weir_simulation()
    print()
    
    # Test individual APIs
    results["individual_apis"] = test_individual_structures()
    
    # Summary
    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    
    tests = [
        ("Plain Canal", results["plain_canal"]),
        ("Gate Simulation", results["gate"]),
        ("Pump Simulation", results["pump"]),
        ("Weir Simulation", results["weir"]),
        ("Pump API", results["individual_apis"].get("pump", False)),
        ("Gate API", results["individual_apis"].get("gate", False)),
        ("Weir API", results["individual_apis"].get("weir", False)),
    ]
    
    passed = sum(1 for _, v in tests if v)
    total = len(tests)
    
    for name, status in tests:
        icon = "[OK]" if status else "[X]"
        print(f"  {icon} {name}")
    
    print(f"\n  Result: {passed}/{total} ({passed/total*100:.0f}%)")
    print("="*60)
    
    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "passed": passed,
        "total": total,
        "pass_rate": f"{passed/total*100:.0f}%"
    }
    
    report_file = OUTPUT_DIR / f"structures_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nReport: {report_file}")

if __name__ == "__main__":
    main()

