import xml.etree.ElementTree

from structs import Node, Way, ParseResult


def parse_node(node_element) -> Node:
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


def parse_osm(xml_file) -> ParseResult:
    tree = xml.etree.ElementTree.fromstring(xml_file.read())
    nodes = {}
    ways = []
    for child in tree:
        if child.tag == "node":
            node = parse_node(child)
            nodes[node.id] = node
        if child.tag == "way":
            attrs = child.attrib
            way_nodes = []
            optional = False
            for child_node in child:
                if child_node.tag == "nd":
                    way_nodes.append(nodes[int(child_node.attrib["ref"])])
                elif child_node.tag == "tag":
                    if child_node.attrib["k"] == "optional" and child_node.attrib["v"] == "yes":
                        optional = True
            way = Way(id=int(attrs["id"]), nodes=way_nodes, optional=optional)
            ways.append(way)
    start_nodes = [node for node in nodes.values() if node.start]
    end_nodes = [node for node in nodes.values() if node.end]
    if len(start_nodes) > 1:
        raise RuntimeError("There should be exactly one node with tag start=yes")
    if len(end_nodes) != 1:
        raise RuntimeError("There should be exactly one node with tag end=yes")
    start_node = start_nodes[0]
    end_node = end_nodes[0]
    return ParseResult(ways=ways, start_id=start_node.id, end_id=end_node.id)
