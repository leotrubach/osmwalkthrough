import argparse
from typing import Dict

import networkx as nx

from osm import parse_osm, Way, Node
from cpp import chinese_postman_paths, graph_components, edge_sum, as_gpx
from utils import pairs


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("osmfile", type=argparse.FileType("r"))
    parser.add_argument("gpxfile", type=argparse.FileType("w"))
    parser.add_argument("--interpolate", type=int, default=5)
    return parser.parse_args()


def fill_metadata(graph, node):
    graph.nodes[node.id]["node_obj"] = node


def build_graph(ways: Dict[int, Way]):
    graph = nx.Graph()
    for way_id, way in ways.items():
        for start_node, end_node in pairs(way.nodes):
            graph.add_edge(
                start_node.id,
                end_node.id,
                weight=start_node.distance_to(end_node),
                id=way_id
            )
            graph.nodes[start_node.id]["node_obj"] = start_node
            graph.nodes[end_node.id]["node_obj"] = end_node
    return graph


def main():
    args = parse_args()
    ways, start_id, end_id = parse_osm(args.osmfile)
    graph = build_graph(ways)
    graph.add_edge("start", start_id, weight=0)
    graph.add_edge("end", end_id, weight=0)
    components = graph_components(graph)
    if len(components) != 1:
        raise ValueError("Number of components of the graph must be exactly 1")
    component = components[0]
    path = chinese_postman_paths(component, "start", "end", n=1)[0]
    eulerian_graph, nodes = path
    eulerian_graph.remove_nodes_from(["start", "end"])
    nodes = [n for n in nodes if n not in ("start", "end")]
    in_length = edge_sum(graph) / 1000.0
    path_length = edge_sum(eulerian_graph) / 1000.0
    duplicate_length = path_length - in_length
    print("Total length of roads: %.3f km" % in_length)
    print("Total length of path: %.3f km" % path_length)
    print("Length of sections visited twice: %.3f km" % duplicate_length)
    args.gpxfile.write(as_gpx(graph, nodes, interpolate_meters=args.interpolate))


if __name__ == "__main__":
    main()