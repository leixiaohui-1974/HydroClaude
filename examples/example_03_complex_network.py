import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from topology.network_graph import NetworkTopology, Node, Edge, NodeType
from solvers.coupled_solver import CoupledNetworkSolver

def run_example():
    print("\n" + "="*60)
    print("示例3: 复杂水网 (Complex Network)")
    print("="*60)
    
    topology = NetworkTopology()
    
    # 创建多源多汇网络
    topology.add_node(Node("源1", NodeType.SOURCE, supply=15, elevation=100))
    topology.add_node(Node("源2", NodeType.SOURCE, supply=10, elevation=95))
    topology.add_node(Node("汇1", NodeType.SINK, demand=12, elevation=50))
    topology.add_node(Node("汇2", NodeType.SINK, demand=8, elevation=45))
    topology.add_node(Node("汇3", NodeType.SINK, demand=5, elevation=40))
    
    topology.add_node(Node("节点1", NodeType.JUNCTION, elevation=90))
    topology.add_node(Node("节点2", NodeType.JUNCTION, elevation=85))
    topology.add_node(Node("节点3", NodeType.BRANCH, elevation=80))
    
    topology.add_edge(Edge("E1", "源1", "节点1", None, 2000))
    topology.add_edge(Edge("E2", "源2", "节点2", None, 1500))
    topology.add_edge(Edge("E3", "节点1", "节点3", None, 3000))
    topology.add_edge(Edge("E4", "节点2", "节点3", None, 2500))
    topology.add_edge(Edge("E5", "节点3", "汇1", None, 2000))
    topology.add_edge(Edge("E6", "节点3", "汇2", None, 1800))
    topology.add_edge(Edge("E7", "节点3", "汇3", None, 1500))
    
    info = topology.analyze_topology()
    
    solver = CoupledNetworkSolver(topology)
    results = solver.solve_timestep(dt=60)
    
    print("\n求解结果:")
    print("节点水头:")
    for node_id, head in list(results['nodes'].items())[:5]:
        print(f"  {node_id}: {head:.2f} m")
    print("\n管段流量:")
    for edge_id, flow in list(results['edges'].items())[:5]:
        print(f"  {edge_id}: {flow:.2f} m³/s")

if __name__ == "__main__":
    run_example()
