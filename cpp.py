from typing import Optional

import networkx as nx
import xml.dom.minidom as minidom

from structs import Solution, Node
from utils import pairs


def graph_components(graph):
    # The graph may contain multiple components, but we can only handle one connected component. If the graph contains
    # more than one connected component, we only use the largest one.
    components = list(graph.subgraph(c) for c in nx.connected_components(graph))
    components.sort(key=lambda c: c.size(), reverse=True)
    return components


def odd_graph(graph, source, destination):
    """
    Given a graph G, construct a graph containing only the vertices with odd degree from G. The resulting graph is
    fully connected, with each weight being the shortest path between the nodes in G.

    Complexity: O(V'*(E + V log(V)) )
    """
    result = nx.Graph()
    odd_nodes = [n for n in graph.nodes() if graph.degree(n) % 2 == 1 if n not in (source, destination)]
    for odd_node in odd_nodes:
        # We calculate the shortest paths twice here, but the overall performance hit is low
        paths = nx.shortest_path(graph, source=odd_node, weight="weight")
        lengths = nx.shortest_path_length(graph, source=odd_node, weight="weight")
        for other_odd_node in odd_nodes:
            if odd_node <= other_odd_node:
                # We only add each edge once
                continue
            # The edge weights are negative for the purpose of max_weight_matching (we want the minimum weight)
            result.add_edge(odd_node, other_odd_node, weight=-lengths[other_odd_node], path=paths[other_odd_node])

    return result


def make_track_point(doc, node: Node):
    trkpt = doc.createElement("trkpt")
    trkpt.setAttribute("lat", str(node.lat))
    trkpt.setAttribute("lon", str(node.lon))
    return trkpt


def as_gpx(solution: Solution, interpolate_meters=5):
    """
    Convert a list of tracks to GPX format
    """
    doc = minidom.Document()

    root = doc.createElement("gpx")
    root.setAttribute("version", "1.0")
    doc.appendChild(root)

    track_name = "Track"
    trk = doc.createElement("trk")
    trk_name = doc.createElement("name")
    trk_name.appendChild(doc.createTextNode(track_name))
    trk.appendChild(trk_name)
    trkseg = doc.createElement("trkseg")

    prev: Optional[Node] = None
    for u in solution.nodes:
        node: Node = solution.graph.nodes[u]["node_obj"]
        if interpolate_meters and prev:
            for intermediate_node in prev.interpolate_to(node, meters=interpolate_meters):
                trkseg.appendChild(make_track_point(doc, intermediate_node))
        trkseg.appendChild(make_track_point(doc, node))
        prev = node

    trk.appendChild(trkseg)
    root.appendChild(trk)

    return doc.toxml()


def matching_cost(graph, matching):
    # Calculate the cost of the additional edges
    cost = 0
    for u, v in matching:
        data = graph[u][v]
        cost += abs(data["weight"])
    return cost


def find_matchings(graph, n=5):
    """
    Find the n best matchings for a graph. The best matching is guaranteed to be the best, but the others are only
    estimates.

    A matching is a subset of edges in which no node occurs more than once.

    The result may contain less than n matchings.

    See https://networkx.github.io/documentation/stable/reference/algorithms/generated/networkx.algorithms.matching.max_weight_matching.html
    """
    best_matching = nx.max_weight_matching(graph, True)
    matchings = [best_matching]

    for u, v in best_matching:
        smaller_graph = nx.Graph(graph)
        smaller_graph.remove_edge(u, v)
        matching = nx.max_weight_matching(smaller_graph, True)
        if len(matching) > 0:
            # We may get an empty matching if there is only one edge (that we removed).
            matchings.append(matching)

    matching_costs = [
        (matching_cost(graph, matching), matching) for matching in matchings
    ]
    matching_costs.sort(key=lambda k: k[0])

    # HACK: The above code end up giving duplicates of the same path, even though the matching is different. To prevent
    # this, we remove matchings with the same cost.
    final_matchings = []
    last_cost = None
    for cost, matching in matching_costs:
        if cost == last_cost:
            continue
        last_cost = cost
        final_matchings.append((cost, matching))

    return final_matchings


def build_eulerian_graph(graph, odd, matching):
    """
    Build an Eulerian graph from a matching. The result is a MultiGraph.
    """

    # Copy the original graph to a multigraph (so we can add more edges between the same nodes)
    eulerian_graph = nx.MultiGraph(graph)

    # For each matched pair of odd vertices, connect them with the shortest path between them
    for u, v in matching:
        edge = odd[u][v]
        path = edge[
            "path"
        ]  # The shortest path between the two nodes, calculated in odd_graph()

        # Add each segment in this path to the graph again
        for p, q in pairs(path):
            eulerian_graph.add_edge(p, q, weight=graph[p][q]["weight"])

    return eulerian_graph


def eulerian_path(graph, source=None):
    """
    Given an Eulerian graph, find one eulerian circuit. Returns the circuit as a list of nodes, with the first and
    last node being the same.
    """

    circuit = list(nx.eulerian_path(graph, source=source))
    nodes = []
    for u, v in circuit:
        nodes.append(u)
    # Append last item
    nodes.append(circuit[-1][1])
    return nodes


def chinese_postman_paths(graph, source, destination, n=20):
    """
    Given a graph, return a list of node id's forming the shortest chinese postman path.
    """

    # Find all the nodes with an odd degree, and create a graph containing only them
    odd = odd_graph(graph, source, destination)

    # Find the best matching of pairs of odd nodes
    matchings = find_matchings(odd, n)

    paths = []
    for cost, matching in matchings[:n]:
        # Copy the original graph to a multigraph (so we can add more edges between the same nodes)
        eulerian_graph = build_eulerian_graph(graph, odd, matching)

        # Now that we have an eulerian graph, we can calculate the eulerian circuit
        nodes = eulerian_path(eulerian_graph, source=source)

        paths.append((eulerian_graph, nodes))
    return paths
