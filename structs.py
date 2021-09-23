import dataclasses
from functools import cached_property
from typing import NamedTuple, List

import networkx as nx
from geopy.distance import geodesic

from utils import edge_sum


@dataclasses.dataclass(frozen=True)
class Solution:
    graph: nx.Graph
    eulerian_graph: nx.MultiGraph
    nodes: List[int]

    @cached_property
    def in_length(self):
        return edge_sum(self.graph) / 1000

    @cached_property
    def path_length(self):
        return edge_sum(self.eulerian_graph) / 1000

    @property
    def duplicate_length(self):
        return self.path_length - self.in_length

    def print_stats(self):
        print(f"Total length of roads: {self.in_length:.3f} km")
        print(f"Total length of path: {self.path_length:.3f} km")
        print(f"Length of sections visited twice: {self.duplicate_length:.3f} km")
        print(f"Efficiency: {self.in_length * 100 / self.path_length}%")


class Node(NamedTuple):
    id: int
    lat: float
    lon: float
    start: bool = False
    end: bool = False

    def distance_to(self, other: "Node"):
        return geodesic((self.lat, self.lon), (other.lat, other.lon)).meters

    def interpolate_to(self, other: "Node", meters: int):
        distance = self.distance_to(other)
        dlon = (other.lon - self.lon) * meters / distance
        dlat = (other.lat - self.lat) * meters / distance
        for i in range(int(distance / meters)):
            yield Node(0, self.lat + dlat * i, self.lon + dlon * i)


class Way(NamedTuple):
    id: int
    nodes: List[Node]
    optional: bool = False


class ParseResult(NamedTuple):
    ways: List[Way]
    start_id: int
    end_id: int