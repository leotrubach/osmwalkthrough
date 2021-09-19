import networkx as nx


def main():
    G = nx.Graph()
    G.add_edge(1, 2, weight=1)
    G.add_edge(1, 3, weight=2)
    print(G.nodes[1])
    # print(nx.is_semieulerian(G))
    #print(list(nx.eulerian_path(G)))


if __name__ == '__main__':
    main()