import csv
import networkx as nx
import xml.dom.minidom as minidom

from utils import pairs


def import_csv_graph(file):
    """
    Example:

    import_csv_graph(open("test.csv", "rb"))

    Does not handle multigraphs yet (more than 1 edge between the same 2 nodes).

    Each row must have the following (in this order):

    * Start node ID
    * End node ID
    * Length in meters
    * Edge name or ID
    * Start longitude, for example 18.4167
    * Start latitude, for example -33.9167
    * End longitude
    * End latitude
    """
    reader = csv.reader(file)
    graph = nx.Graph()
    for row_number, row in enumerate(reader):
        try:
            start_node = row[0]
            end_node = row[1]
            length = int(row[2])
            id = row[3]
            start_lon, start_lat, end_lon, end_lat = map(float, row[4:8])
            graph.add_edge(start_node, end_node, weight=length, id=id, label=id)

            # We keep the GPS coordinates as strings
            graph.nodes[start_node]["longitude"] = start_lon
            graph.nodes[start_node]["latitude"] = start_lat
            graph.nodes[end_node]["longitude"] = end_lon
            graph.nodes[end_node]["latitude"] = end_lat
        except ValueError:
            print("Skipping input row %d" % (row_number + 1))

    return graph


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


def as_gpx(graph, track, name=None):
    """
    Convert a list of tracks to GPX format
    Example:

    >>> g = nx.Graph()
    >>> g.add_node(1, latitude="31.1", longitude="-18.1")
    >>> g.add_node(2, latitude="31.2", longitude="-18.2")
    >>> g.add_node(3, latitude="31.3", longitude="-18.3")
    >>> print(as_gpx(g, [{'points': [1,2,3]}]))
    <?xml version="1.0" ?><gpx version="1.0"><trk><name>Track 1</name><number>1</number><trkseg><trkpt lat="31.1" lon="-18.1"><ele>1</ele></trkpt><trkpt lat="31.2" lon="-18.2"><ele>2</ele></trkpt><trkpt lat="31.3" lon="-18.3"><ele>3</ele></trkpt></trkseg></trk></gpx>
    """
    doc = minidom.Document()

    root = doc.createElement("gpx")
    root.setAttribute("version", "1.0")
    doc.appendChild(root)

    if name:
        gpx_name = doc.createElement("name")
        gpx_name.appendChild(doc.createTextNode(name))
        root.appendChild(gpx_name)


    track_name = "Track"
    trk = doc.createElement("trk")
    trk_name = doc.createElement("name")
    trk_name.appendChild(doc.createTextNode(track_name))
    trk.appendChild(trk_name)
    trkseg = doc.createElement("trkseg")

    for u in track:
        longitude = graph.nodes[u].get("longitude")
        latitude = graph.nodes[u].get("latitude")
        trkpt = doc.createElement("trkpt")
        trkpt.setAttribute("lat", str(latitude))
        trkpt.setAttribute("lon", str(longitude))
        trkseg.appendChild(trkpt)

    trk.appendChild(trkseg)
    root.appendChild(trk)

    return doc.toxml()


def write_csv(graph, nodes, out):
    writer = csv.writer(out)
    writer.writerow(
        [
            "Start Node",
            "End Node",
            "Segment Length",
            "Segment ID",
            "Start Longitude",
            "Start Latitude",
            "End Longitude",
            "End Latitude",
        ]
    )
    for u, v in pairs(nodes, False):
        length = graph[u][v]["weight"]
        id = graph[u][v]["id"]
        start_latitude = graph.nodes[u].get("latitude")
        start_longitude = graph.nodes[u].get("longitude")
        end_latitude = graph.nodes[v].get("latitude")
        end_longitude = graph.nodes[v].get("longitude")
        writer.writerow(
            [
                u,
                v,
                length,
                id,
                start_longitude,
                start_latitude,
                end_longitude,
                end_latitude,
            ]
        )


def edge_sum(graph):
    total = 0
    for u, v, data in graph.edges(data=True):
        total += data["weight"]
    return total


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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input CSV file", type=argparse.FileType("r"))
    parser.add_argument("source", help="Source node id")
    parser.add_argument("destination", help="Destination node id")
    parser.add_argument("--gpx", help="GPX output file", type=argparse.FileType("w"))
    parser.add_argument("--csv", help="CSV output file", type=argparse.FileType("w"))

    args = parser.parse_args()

    graph = import_csv_graph(args.input)
    if graph.degree[args.source] != 1:
        raise RuntimeError("Source must be vertex with degree 1")
    if graph.degree[args.destination] != 1:
        raise RuntimeError("Destination must be vertex with degree 1")
    components = graph_components(graph)
    if len(components) == 0:
        raise ValueError("No graph components found; check input file")

    # Only use the largest component
    component = components[0]

    paths = chinese_postman_paths(component, args.source, args.destination, n=1)

    for eulerian_graph, nodes in paths:

        in_length = edge_sum(graph) / 1000.0
        path_length = edge_sum(eulerian_graph) / 1000.0
        duplicate_length = path_length - in_length

        print("Total length of roads: %.3f km" % in_length)
        print("Total length of path: %.3f km" % path_length)
        print("Length of sections visited twice: %.3f km" % duplicate_length)
        print("Node sequence:", nodes)
        print()

    eulerian_graph, nodes = paths[0]  # The best one

    if args.gpx:
        args.gpx.write(as_gpx(graph, nodes))

    if args.csv:
        write_csv(graph, nodes, args.csv)

