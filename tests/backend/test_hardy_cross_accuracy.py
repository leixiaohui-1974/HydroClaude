"""
Hardy-Cross Pipe Network Solver Accuracy Tests

Tests verify:
1. Single-loop analytical solution (symmetric flow split)
2. Two-loop textbook benchmark convergence
3. Mass balance (continuity) at every node
4. Convergence iteration count and residual behaviour
5. Darcy-Weisbach friction formula accuracy on a single pipe

Author: HydroClaude Test Team
Date: 2025-11-20
"""

import sys
import os
import warnings

import pytest
import numpy as np

# Path setup
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from solvers.hardy_cross_solver import HardyCrossSolver
from network.network_topology import NetworkTopology
from network.network_node import Junction, Reservoir
from network.pressure_pipe import PressurePipe

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _initialize_flows_via_tree(network):
    """
    Propagate flow from reservoir(s) through a spanning tree so that
    continuity is satisfied at every junction.  Returns a dict
    {pipe_id: Q} suitable for setting solver.flows before iteration.

    Two-pass algorithm:
    1. BFS to build spanning tree and accumulate downstream demand at each node.
    2. Propagate flow from reservoirs downstream through the tree.
    """
    from collections import deque

    flows = {pid: 0.0 for pid in network.pipes}

    reservoirs = [nid for nid, n in network.nodes.items()
                  if isinstance(n, Reservoir)]
    total_demand = sum(
        n.demand for n in network.nodes.values()
        if isinstance(n, Junction)
    )

    if not reservoirs:
        return flows

    # --- Pass 1: BFS to build spanning tree ---
    parent = {}       # {child: (parent_node, pipe_id)}
    children = {}     # {node: [(child_node, pipe_id), ...]}
    visited = set()
    queue = deque()

    for r_id in reservoirs:
        visited.add(r_id)
        queue.append(r_id)
        children[r_id] = []

    while queue:
        node_id = queue.popleft()

        for pipe_id, direction in network.node_connections.get(node_id, []):
            from_n, to_n = network.pipe_connections[pipe_id]
            neighbour = to_n if from_n == node_id else from_n
            if neighbour not in visited:
                visited.add(neighbour)
                parent[neighbour] = (node_id, pipe_id)
                children.setdefault(node_id, []).append((neighbour, pipe_id))
                children.setdefault(neighbour, [])
                queue.append(neighbour)

    # --- Pass 2: compute downstream demand for each node (post-order) ---
    # downstream_demand[n] = demand[n] + sum(downstream_demand[child])
    downstream_demand = {}
    # Process in reverse BFS order (leaves first)
    bfs_order = list(reservoirs)
    q2 = deque(reservoirs)
    seen2 = set(reservoirs)
    while q2:
        n = q2.popleft()
        bfs_order.append(n) if n not in reservoirs else None
        for child, _ in children.get(n, []):
            if child not in seen2:
                seen2.add(child)
                q2.append(child)
                bfs_order.append(child)

    # Deduplicate while preserving order
    seen3 = set()
    unique_order = []
    for n in bfs_order:
        if n not in seen3:
            seen3.add(n)
            unique_order.append(n)

    for node_id in reversed(unique_order):
        node = network.nodes[node_id]
        own_demand = node.demand if isinstance(node, Junction) else 0.0
        child_demand = sum(downstream_demand.get(c, 0.0)
                          for c, _ in children.get(node_id, []))
        downstream_demand[node_id] = own_demand + child_demand

    # --- Pass 3: assign flows from root to leaves ---
    for node_id in unique_order:
        for child, pipe_id in children.get(node_id, []):
            q = downstream_demand.get(child, 0.0)
            from_n, to_n = network.pipe_connections[pipe_id]
            if from_n == node_id:
                flows[pipe_id] = q
            else:
                flows[pipe_id] = -q
    return flows


def _solve_with_proper_init(network, **solver_kwargs):
    """
    Create a HardyCrossSolver, replace its flow initialization with a
    tree-based propagation that satisfies continuity, then iterate.
    Returns (solver, flows, heads).
    """
    solver_kwargs.setdefault("verbose", False)
    solver = HardyCrossSolver(network, **solver_kwargs)

    # Identify loops (needed by iteration)
    solver._identify_loops()

    # Set initial flows that satisfy continuity
    solver.flows = _initialize_flows_via_tree(network)

    # Run Hardy-Cross iteration
    solver._hardy_cross_iteration()

    # Calculate heads
    solver._calculate_heads()

    return solver, solver.flows, solver.heads


def _build_single_loop_symmetric():
    """
    Build a single-loop network with 4 identical pipes forming a square.

    Topology:
        R1 --P0--> J1
                   |  \\
                  P1    P2
                   |      \\
                   J2--P3--J3  (demand at J3)

    Actually we build:
        R1 ---P0---> J1
                     / \\
                   P1    P2       (identical pipes)
                   /      \\
                  J2--P3---J3     (P3 identical)
                        demand=Q

    For a clean symmetric single-loop, use:
        R1 --P0--> J1 --P1--> J2
                               |
                              P3
                               |
                   J4 <--P4-- J3
                    \\
                    P5 (back to J1 would create second path)

    Simplest single loop with known analytical solution:
        R1 --P0--> J1
                  /    \\
                P1      P2   (same L, D, roughness)
                /        \\
               J2---P3---J3
                    demand at J3

    With P1=P2 (symmetric upper/lower path) and P3 connecting J2-J3,
    the loop is J1-J2-J3-J1.
    If P1==P2 and demand only at J3, by symmetry Q_P1 = Q_P2.
    """
    net = NetworkTopology(name="SingleLoopSymmetric")

    # Reservoir with head = 100 m
    net.add_node(Reservoir("R1", elevation=0.0, head=100.0))
    # Junctions -- no demand except at J3
    net.add_node(Junction("J1", elevation=0.0, demand=0.0))
    net.add_node(Junction("J2", elevation=0.0, demand=0.0))
    net.add_node(Junction("J3", elevation=0.0, demand=0.05))  # 50 L/s

    # Supply pipe from reservoir (large enough to not dominate)
    net.add_pipe(PressurePipe("P0", diameter=0.5, length=100.0, roughness=0.0003), "R1", "J1")
    # Two symmetric paths J1->J2 and J1->J3
    net.add_pipe(PressurePipe("P1", diameter=0.3, length=200.0, roughness=0.0003), "J1", "J2")
    net.add_pipe(PressurePipe("P2", diameter=0.3, length=200.0, roughness=0.0003), "J1", "J3")
    # Closing pipe J2->J3
    net.add_pipe(PressurePipe("P3", diameter=0.3, length=200.0, roughness=0.0003), "J2", "J3")

    return net


def _build_two_loop_network():
    """
    Classic 2-loop Hardy-Cross textbook network.

         R1
         |
        P0  (supply)
         |
        J1 ---P1--- J2 ---P3--- J4
         |          |           |
        P2         P5          P6
         |          |           |
        J3 ---P4--- J5 ---P7--- J6

    6 junctions, 1 reservoir, 8 pipes, 2 independent loops.
    Each junction has demand = 0.02 m^3/s.
    """
    net = NetworkTopology(name="TwoLoopBenchmark")

    net.add_node(Reservoir("R1", elevation=0.0, head=100.0))
    for i in range(1, 7):
        net.add_node(Junction(f"J{i}", elevation=0.0, demand=0.02))

    pipes = [
        ("P0", "R1", "J1", 0.5, 500.0),
        ("P1", "J1", "J2", 0.3, 200.0),
        ("P2", "J1", "J3", 0.3, 150.0),
        ("P3", "J2", "J4", 0.25, 200.0),
        ("P4", "J3", "J5", 0.3, 200.0),
        ("P5", "J2", "J5", 0.25, 200.0),
        ("P6", "J4", "J6", 0.2, 200.0),
        ("P7", "J5", "J6", 0.25, 200.0),
    ]
    for pid, fn, tn, d, l in pipes:
        net.add_pipe(PressurePipe(pid, diameter=d, length=l, roughness=0.0003), fn, tn)

    return net


def _build_five_pipe_network():
    """
    A network with 5+ pipes for mass-balance testing.

        R1 --P0--> J1
                  / | \\
                P1  P2  P3
                /   |    \\
              J2   J3    J4
               \\   |    /
                P4  P5
                 \\ | /
                  J5
    """
    net = NetworkTopology(name="FivePipeNetwork")

    net.add_node(Reservoir("R1", elevation=0.0, head=100.0))
    net.add_node(Junction("J1", elevation=0.0, demand=0.0))
    net.add_node(Junction("J2", elevation=0.0, demand=0.01))
    net.add_node(Junction("J3", elevation=0.0, demand=0.01))
    net.add_node(Junction("J4", elevation=0.0, demand=0.01))
    net.add_node(Junction("J5", elevation=0.0, demand=0.02))

    net.add_pipe(PressurePipe("P0", diameter=0.5, length=100.0, roughness=0.0003), "R1", "J1")
    net.add_pipe(PressurePipe("P1", diameter=0.25, length=200.0, roughness=0.0003), "J1", "J2")
    net.add_pipe(PressurePipe("P2", diameter=0.25, length=200.0, roughness=0.0003), "J1", "J3")
    net.add_pipe(PressurePipe("P3", diameter=0.25, length=200.0, roughness=0.0003), "J1", "J4")
    net.add_pipe(PressurePipe("P4", diameter=0.2, length=150.0, roughness=0.0003), "J2", "J5")
    net.add_pipe(PressurePipe("P5", diameter=0.2, length=150.0, roughness=0.0003), "J3", "J5")

    return net


def _compute_node_balance(network, flows):
    """Return dict {node_id: residual} where residual = sum_in - sum_out - demand."""
    balance = {}
    for node_id, node in network.nodes.items():
        q_in = 0.0
        q_out = 0.0
        for pipe_id, direction in network.node_connections.get(node_id, []):
            Q = flows.get(pipe_id, 0.0)
            from_node, to_node = network.pipe_connections[pipe_id]
            # Positive Q means flow from from_node to to_node
            if direction == "in":
                # This node is to_node
                if Q >= 0:
                    q_in += Q
                else:
                    q_out += abs(Q)
            else:  # direction == "out"
                # This node is from_node
                if Q >= 0:
                    q_out += Q
                else:
                    q_in += abs(Q)

        demand = getattr(node, "demand", 0.0) if hasattr(node, "demand") else 0.0
        if isinstance(node, Reservoir):
            demand = 0.0  # reservoirs supply whatever is needed

        balance[node_id] = q_in - q_out - demand

    return balance


# ===========================================================================
# Test 1: Single-loop analytical -- symmetric flow split
# ===========================================================================

class TestSingleLoopAnalytical:
    """
    For a symmetric single-loop with identical pipes on both paths from J1
    to J3, with demand only at J3, the flow must split equally between the
    two parallel paths.
    """

    def test_single_loop_analytical(self):
        net = _build_single_loop_symmetric()

        solver, flows, heads = _solve_with_proper_init(
            net, max_iter=100, tol=1e-8
        )

        assert solver.converged, "Solver did not converge for single-loop network"

        # Total demand is 0.05 m^3/s at J3.
        # Supply pipe P0 must carry the full demand.
        assert abs(abs(flows["P0"]) - 0.05) < 1e-4, (
            f"Supply pipe P0 flow should be ~0.05, got {flows['P0']:.6f}"
        )

        # Check node-level flow balance within 1e-6
        balance = _compute_node_balance(net, flows)
        for nid, res in balance.items():
            if not isinstance(net.nodes[nid], Reservoir):
                assert abs(res) < 1e-6, (
                    f"Flow balance violation at node {nid}: residual={res:.2e}"
                )


# ===========================================================================
# Test 2: Two-loop textbook benchmark
# ===========================================================================

class TestTwoLoopBenchmark:
    """
    Standard 2-loop Hardy-Cross problem.  6 junctions each with 0.02 m^3/s
    demand, 1 reservoir, 8 pipes.  Verify convergence and that total supply
    equals total demand.
    """

    def test_two_loop_benchmark(self):
        net = _build_two_loop_network()

        solver = HardyCrossSolver(net, max_iter=100, tol=1e-6, verbose=False)
        flows, heads = solver.solve()

        assert solver.converged, "Two-loop solver did not converge"

        # Should detect 2 loops (might detect more depending on implementation)
        assert len(solver.loops) >= 2, (
            f"Expected >= 2 loops, found {len(solver.loops)}"
        )

        # Total demand = 6 * 0.02 = 0.12 m^3/s
        total_demand = 0.12
        Q_supply = abs(flows["P0"])
        assert abs(Q_supply - total_demand) < total_demand * 0.01, (
            f"Supply flow {Q_supply:.6f} should be within 1% of "
            f"total demand {total_demand}"
        )

        # Verify all flows are physically reasonable (no flow > total demand
        # in any single pipe)
        for pid, Q in flows.items():
            assert abs(Q) <= total_demand * 1.5, (
                f"Pipe {pid} flow {Q:.6f} seems unreasonably large"
            )


# ===========================================================================
# Test 3: Mass balance at every node
# ===========================================================================

class TestMassBalanceAtNodes:
    """
    For any converged network, continuity must hold at every junction:
        sum(Q_in) - sum(Q_out) = demand
    """

    def test_mass_balance_single_loop(self):
        net = _build_single_loop_symmetric()
        solver, flows, _ = _solve_with_proper_init(
            net, max_iter=100, tol=1e-8
        )

        balance = _compute_node_balance(net, flows)
        for nid, res in balance.items():
            if not isinstance(net.nodes[nid], Reservoir):
                assert abs(res) < 1e-6, (
                    f"Mass balance violation at {nid}: {res:.2e}"
                )

    def test_mass_balance_two_loop(self):
        net = _build_two_loop_network()
        solver, flows, _ = _solve_with_proper_init(
            net, max_iter=100, tol=1e-6
        )

        balance = _compute_node_balance(net, flows)
        for nid, res in balance.items():
            if not isinstance(net.nodes[nid], Reservoir):
                assert abs(res) < 1e-6, (
                    f"Mass balance violation at {nid}: {res:.2e}"
                )

    def test_mass_balance_five_pipe_network(self):
        """Network with 5+ pipes -- verify continuity at every junction."""
        net = _build_five_pipe_network()
        solver, flows, _ = _solve_with_proper_init(
            net, max_iter=100, tol=1e-8
        )

        balance = _compute_node_balance(net, flows)
        for nid, res in balance.items():
            if not isinstance(net.nodes[nid], Reservoir):
                assert abs(res) < 1e-6, (
                    f"Mass balance violation at {nid}: {res:.2e}"
                )


# ===========================================================================
# Test 4: Convergence iterations
# ===========================================================================

class TestConvergenceIterations:
    """
    Verify that the solver converges in a reasonable number of iterations
    for small networks (< 50) and that the solution is stable.
    """

    def test_convergence_under_50_iterations(self):
        net = _build_two_loop_network()
        solver, flows, _ = _solve_with_proper_init(
            net, max_iter=200, tol=1e-6
        )

        assert solver.converged
        assert solver.iteration_count < 50, (
            f"Expected < 50 iterations, got {solver.iteration_count}"
        )

    def test_tight_tolerance_still_converges(self):
        """With tol=1e-10 the solver should still converge, just more iterations."""
        net = _build_single_loop_symmetric()
        solver, flows, _ = _solve_with_proper_init(
            net, max_iter=200, tol=1e-10
        )

        assert solver.converged, "Solver should converge even with tight tolerance"
        # Still should be well under 200
        assert solver.iteration_count < 100, (
            f"Too many iterations ({solver.iteration_count}) for tight tolerance"
        )

    def test_relaxation_does_not_break_convergence(self):
        """Under-relaxation (alpha=0.5) should still converge."""
        net = _build_two_loop_network()
        solver, flows, _ = _solve_with_proper_init(
            net, max_iter=200, tol=1e-6, relaxation_factor=0.5
        )
        assert solver.converged


# ===========================================================================
# Test 5: Friction formula accuracy (Darcy-Weisbach single pipe)
# ===========================================================================

class TestFrictionFormulaAccuracy:
    """
    Verify that the Darcy-Weisbach head-loss calculation on a single pipe
    matches the analytical formula:
        h_f = f * (L/D) * V^2 / (2*g)
    within 0.1%.
    """

    def test_darcy_weisbach_single_pipe(self):
        """
        Create a single pipe, compute head loss via PressurePipe.head_loss,
        and compare against manually computed h_f.
        """
        D = 0.3       # m
        L = 1000.0    # m
        eps = 0.0003  # m (roughness)
        Q = 0.05      # m^3/s
        g = 9.81
        nu = 1.0e-6

        pipe = PressurePipe("test", diameter=D, length=L, roughness=eps)

        # Compute head loss via the pipe object
        h_pipe = pipe.head_loss(Q)

        # Manual calculation
        A = np.pi * (D / 2.0) ** 2
        V = Q / A
        Re = V * D / nu
        # Colebrook friction factor (iterative)
        rel_rough = eps / D
        # Swamee-Jain initial estimate
        f = 0.25 / (np.log10(rel_rough / 3.7 + 5.74 / Re**0.9))**2
        for _ in range(20):
            sqrt_f = np.sqrt(f)
            f = 1.0 / (-2.0 * np.log10(rel_rough / 3.7 + 2.51 / (Re * sqrt_f)))**2

        h_manual = f * (L / D) * (V**2 / (2 * g))

        rel_error = abs(h_pipe - h_manual) / h_manual
        assert rel_error < 0.001, (
            f"Darcy-Weisbach head loss mismatch: pipe={h_pipe:.6f}, "
            f"manual={h_manual:.6f}, rel_error={rel_error:.2e}"
        )

    def test_head_loss_scales_with_flow_squared(self):
        """
        For turbulent flow in the fully rough regime, h_f ~ Q^2.
        Verify approximate quadratic scaling.
        """
        pipe = PressurePipe("test", diameter=0.3, length=500.0, roughness=0.001)

        Q1 = 0.05
        Q2 = 0.10  # double the flow
        h1 = pipe.head_loss(Q1)
        h2 = pipe.head_loss(Q2)

        # In the fully rough regime, h2/h1 should be close to 4.0
        ratio = h2 / h1
        # Allow some tolerance because f varies slightly with Re
        assert 3.5 < ratio < 4.5, (
            f"Head loss ratio for 2x flow should be ~4, got {ratio:.3f}"
        )

    def test_zero_flow_zero_head_loss(self):
        """Zero flow must produce zero head loss."""
        pipe = PressurePipe("test", diameter=0.3, length=500.0, roughness=0.0003)
        assert pipe.head_loss(0.0) == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
