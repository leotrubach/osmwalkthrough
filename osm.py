import xml.etree.ElementTree
from typing import NamedTuple, List
from geopy.distance import geodesic


class Node(NamedTuple):
    id: int
    lat: float
    lon: float
    start: bool = False
    end: bool = False

    def distance_to(self, other: "Node"):
        return geodesic((self.lat, self.lon), (other.lat, other.lon)).meters


class Way(NamedTuple):
    id: int
    nodes: List[Node]


def parse_node(node_element):
    attrs = node_element.attrib
    node_attrs = {
        "id": int(attrs["id"]),
        "lon": float(attrs["lon"]),
        "lat": float(attrs["lat"]),
    }
    for tag_element in node_element:
        tag_attrs = tag_element.attrib
        if tag_attrs["k"] == "end" and tag_attrs["v"] == "yes":
            node_attrs["end"] = True
        elif tag_attrs["k"] == "start" and tag_attrs["v"] == "yes":
            node_attrs["start"] = True
    node = Node(**node_attrs)
    return node


def parse_osm(xml_file):
    tree = xml.etree.ElementTree.fromstring(xml_file.read())
    nodes = {}
    ways = {}
    for child in tree:
        if child.tag == "node":
            node = parse_node(child)
            nodes[node.id] = node
        if child.tag == "way":
            attrs = child.attrib
            way_nodes = []
            for child_node in child:
                way_nodes.append(nodes[int(child_node.attrib["ref"])])
                way = Way(id=int(attrs["id"]), nodes=way_nodes)
                ways[way.id] = way
    start_nodes = [node for node in nodes.values() if node.start]
    end_nodes = [node for node in nodes.values() if node.end]
    if len(start_nodes) > 1:
        raise RuntimeError("There should be exactly one node with tag start=yes")
    if len(end_nodes) != 1:
        raise RuntimeError("There should be exactly one node with tag end=yes")
    start_node = start_nodes[0]
    end_node = end_nodes[0]
    return ways, start_node.id, end_node.id