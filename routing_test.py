from fuzzywuzzy import process
import json
import heapq

lines = json.load(open('subway.json'))
stations = lines['stations']
edges = json.load(open('routing_graph.json'))['edges']

station_ids_by_name = {station['name'].lower(): id for (id, station) in stations.items()}
station_names = list(station_ids_by_name.keys())

def station_from_name(name):
    name, score = process.extractOne(name, station_names)
    print(name)
    return station_ids_by_name[name]

def astar(edges, start_node, end_node):
    seen = set()
    heap = []
    heapq.heappush(heap, (0, (start_node,)))
    while len(heap):
        (cost, path) = heapq.heappop(heap)
        seen.add(path[-1])
        for edge in edges.get(path[-1], []):
            to_node = edge['to_node']
            if to_node not in seen:
                new_path = path + (to_node,)
                new_cost = cost + edge['time']
                if to_node == end_node:
                    return (new_path, new_cost)
                else:
                    heapq.heappush(heap, (new_cost, new_path))
    return None

def pretty_print_path(path):
    for node in path:
        splitter = None
        if '+' in node: splitter = '+'
        if '-' in node: splitter = '-'
        if splitter:
            station_id, line = node.split(splitter)
            print("({}) {}".format(stations[station_id]['name'], line))
        else:
            print(stations[node]['name'])

while True:
    from_id = station_from_name(input('from: '))
    to_id = station_from_name(input('to: '))
    print(' {} -> {}'.format(from_id, to_id))
    path, cost = astar(edges, from_id, to_id)
    print(int(cost / 60), 'minutes')
    pretty_print_path(path)
