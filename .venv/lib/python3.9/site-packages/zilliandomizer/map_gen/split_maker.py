from collections import defaultdict
import itertools
from typing import AbstractSet, Collection, Dict, Iterable, List, Mapping, Set

from .base_maker import BaseMaker, Edge, Node


def find_cycles(nodes: Iterable[Node], dependencies: Mapping[Node, Iterable[Node]]) -> Set[Node]:
    """ returns the nodes that are part of dependency cycles """
    visited: Set[Node] = set()

    path_stack: List[Node] = []
    path_index: Dict[Node, int] = {}  # index into path_stack to avoid searching

    cycle_nodes: Set[Node] = set()

    def dfs(node: Node) -> None:
        visited.add(node)

        path_index[node] = len(path_stack)
        path_stack.append(node)

        for neighbor in dependencies[node]:
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in path_index:
                # detected a cycle
                cycle_start_index = path_index[neighbor]
                # input(f"{node=}  {neighbor=}  {path_stack=}")
                cycle_nodes.update(path_stack[cycle_start_index:])

        assert path_stack[-1] == node
        path_stack.pop()
        del path_index[node]

    for node in nodes:
        if node not in visited:
            dfs(node)

    return cycle_nodes


def find_enter_by_elevator(nodes: Iterable[Node], bm: BaseMaker, start: Node) -> Collection[Node]:
    elevator_entrances: List[Node] = []
    for node in nodes:
        path = bm.path(start, node)
        if len(path) < 2:
            elevator_entrances.append(node)
            continue
        parent = path[-2]
        if parent.y != node.y:
            elevator_entrances.append(node)
    return elevator_entrances


def choose_splits(bm: BaseMaker, no_doors: AbstractSet[Node], start: Node) -> Dict[Node, Node]:
    possible_splits = bm.get_possible_splits(start, no_doors)
    # print(bm.map_str(1, possible_splits))

    path_to_goal = bm.path(start, Node(0, 5))

    # TODO: don't exclude elevator entrances - block elevator with door like vanilla r15c6
    while True:
        elevator_entrances = find_enter_by_elevator(possible_splits, bm, start)
        if len(elevator_entrances) == 0:
            break
        for node in elevator_entrances:
            del possible_splits[node]

    while True:
        adj_candidates = [
            node
            for node in possible_splits
            if any((adj_node in possible_splits) for adj_node in bm.geo_adjs(node))
        ]
        if len(adj_candidates) == 0:
            break
        # print(f"just geo adjacents:\n{bm.map_str(1, adj_candidates)}")

        # more likely to evict if not on path to goal
        not_on_path = [node for node in adj_candidates if node not in path_to_goal]
        adj_candidates.extend(not_on_path)
        adj_candidates.extend(not_on_path)

        to_evict = bm.random.choice(adj_candidates)
        del possible_splits[to_evict]

    # print(f"no adjacents - {len(possible_splits)=}\n{bm.map_str(1, possible_splits)}")

    # now need to eliminate dependency cycles
    while True:
        dependencies: Dict[Node, List[Node]] = defaultdict(list)
        for node, dipper in possible_splits.items():
            path_to_node = bm.path(start, node)
            path_to_dipper = bm.path(start, dipper)
            for path_node in itertools.chain(path_to_node, path_to_dipper):
                if path_node in possible_splits and path_node != node:
                    dependencies[node].append(path_node)

        # from pprint import pp
        # pp(possible_splits)
        # pp(dependencies)
        # input()
        cycles = find_cycles(possible_splits, dependencies)
        # input(f"{cycles=}")
        if len(cycles) == 0:
            break

        cycle_list = list(cycles)

        # more likely to evict if not on path to goal
        not_on_path = [node for node in cycle_list if node not in path_to_goal]
        cycle_list.extend(not_on_path)
        cycle_list.extend(not_on_path)

        to_evict = bm.random.choice(cycle_list)
        del possible_splits[to_evict]

    # print(f"no cycles - {len(possible_splits)=}\n{bm.map_str(1, possible_splits, split_edges(possible_splits))}")

    return possible_splits


def split_edges(splits: Mapping[Node, Node]) -> Set[Edge]:
    """ the edges between the splits and their dippers """
    split_edges: Set[Edge] = set()
    for nodes in splits.items():
        split_edges.add(frozenset(nodes))
    return split_edges
