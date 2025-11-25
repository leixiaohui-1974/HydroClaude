#!/usr/bin/env python3
import requests
import time

BACKEND_URL = 'http://localhost:8001'

# Generate 100 test cases
cases = []
for L in [200, 500, 1000, 2000]:
    for W in [5, 10, 20]:
        for S in [0.0005, 0.001, 0.002]:
            for Q in [20, 50, 100]:
                h = max(1.5, Q / (W * 5))
                cases.append({'L': L, 'W': W, 'S': S, 'Q': Q, 'h': h})
                if len(cases) >= 100:
                    break
            if len(cases) >= 100: break
        if len(cases) >= 100: break
    if len(cases) >= 100: break

print(f'Generated {len(cases)} test cases')
print('Running batch test...\n')

passed = 0
failed = 0
start_all = time.time()

for i, tc in enumerate(cases, 1):
    try:
        resp = requests.post(
            f'{BACKEND_URL}/api/structures/simulate-canal-with-structure',
            json={
                'simulation_type': 'steady',
                'canal': {'length': tc['L'], 'width': tc['W'], 'slope': tc['S'], 
                         'manning_n': 0.015, 'grid_nx': min(tc['L']//5, 100)},
                'structure_type': 'none',
                'structure': {'position': 0, 'parameters': {}},
                'boundaries': {
                    'upstream': {'type': 'Q', 'value': tc['Q']},
                    'downstream': {'type': 'h', 'value': tc['h']}
                },
                'metadata': {'title': f'Case{i}'}
            },
            timeout=60
        )
        
        if resp.status_code == 200:
            data = resp.json()
            results = data.get('results', data)
            if results.get('status') == 'completed' and results.get('metrics', {}).get('converged'):
                passed += 1
                status = 'OK'
            else:
                failed += 1
                status = 'FAIL'
        else:
            failed += 1
            status = 'ERR'
    except Exception as e:
        failed += 1
        status = 'ERR'
    
    pct = i / len(cases) * 100
    bar = '#' * int(pct/2) + '-' * (50 - int(pct/2))
    print(f'\r[{bar}] {pct:5.1f}% {i}/{len(cases)} {status}', end='', flush=True)

total_time = time.time() - start_all
print(f'\n\n=== Test Complete ===')
print(f'Passed: {passed}/{len(cases)} ({passed/len(cases)*100:.1f}%)')
print(f'Failed: {failed}')
print(f'Time: {total_time:.1f}s ({total_time/60:.1f} min)')
print(f'Avg: {total_time/len(cases):.2f}s/case')

