import argparse
import csv
import xml.etree.ElementTree
from typing import NamedTuple, List, Dict
from geopy.distance import geodesic

from utils import pairs


class Node(NamedTuple):
    id: int
    lat: float
    lon: float

    def distance_to(self, other: 'Node'):
        return geodesic((self.lat, self.lon), (other.lat, other.lon)).meters


class Way(NamedTuple):
    id: int
    nodes: List[Node]


def parse(xml_file):
    tree = xml.etree.ElementTree.fromstring(open(xml_file).read())
    nodes = {}
    ways = {}
    for child in tree:
        if child.tag == "node":
            attrs = child.attrib
            node = Node(
                id=int(attrs["id"]),
                lon=float(attrs["lon"]),
                lat=float(attrs["lat"])
            )
            nodes[node.id] = node
        if child.tag == "way":
            attrs = child.attrib
            way_nodes = []
            for child_node in child:
                way_nodes.append(nodes[int(child_node.attrib["ref"])])
                way = Way(id=int(attrs["id"]), nodes=way_nodes)
                ways[way.id] = way
    return nodes, ways


def to_csv(nodes: Dict[int, Node], ways: Dict[int, Way], csv_file_name):
    with open(csv_file_name, "w") as csv_file:
        writer = csv.writer(csv_file)
        edge_id = 1
        for way_id, way in ways.items():
            for start_node, end_node in pairs(way.nodes):
                writer.writerow([
                    start_node.id,
                    end_node.id,
                    start_node.distance_to(end_node),
                    edge_id,
                    start_node.lon,
                    start_node.lat,
                    end_node.lon,
                    end_node.lat
                ])
                edge_id += 1


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("osmfile")
    parser.add_argument("csvfile")
    return parser.parse_args()


def main():
    args = parse_args()
    nodes, ways = parse(args.osmfile)
    to_csv(nodes, ways, args.csvfile)


if __name__ == "__main__":
    main()