import argparse
from itertools import product
from typing import List, Iterator, Optional

import networkx as nx

from osm import parse_osm
from cpp import chinese_postman_paths, graph_components, as_gpx
from structs import Solution, Way
from utils import pairs


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("osmfile", type=argparse.FileType("r"))
    parser.add_argument("gpxfile", type=argparse.FileType("w"))
    parser.add_argument("--interpolate", type=int, default=5)
    return parser.parse_args()


def fill_metadata(graph, node):
    graph.nodes[node.id]["node_obj"] = node


def build_graph(ways: List[Way]):
    graph = nx.Graph()
    for way in ways:
        for start_node, end_node in pairs(way.nodes):
            graph.add_edge(
                start_node.id,
                end_node.id,
                weight=start_node.distance_to(end_node),
                id=way.id
            )
            graph.nodes[start_node.id]["node_obj"] = start_node
            graph.nodes[end_node.id]["node_obj"] = end_node
    return graph


def iterate_optinal_ways(optional_ways: List[Way]) -> Iterator[List[Way]]:
    for combination in product([False, True], repeat=len(optional_ways)):
        yield [ow for ow, flag in zip(optional_ways, combination) if flag]


def calculate(ways: List[Way], start_id, end_id) -> Solution:
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
    return Solution(graph, eulerian_graph, nodes)


def main():
    args = parse_args()
    ways, start_id, end_id = parse_osm(args.osmfile)
    all_optional_ways = [w for w in ways if w.optional]
    mandatory_ways = [w for w in ways if not w.optional]
    best_solution: Optional[Solution] = None
    for optional_ways in iterate_optinal_ways(all_optional_ways):
        ways = [*mandatory_ways, *optional_ways]
        solution = calculate(ways, start_id, end_id)
        solution.print_stats()
        if not best_solution or best_solution.path_length > solution.path_length:
            best_solution = solution
    args.gpxfile.write(as_gpx(best_solution, interpolate_meters=args.interpolate))


if __name__ == "__main__":
    main()