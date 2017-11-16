import csv
import json
from collections import defaultdict

# https://developers.google.com/transit/gtfs/reference

stations_by_id = {}
station_ids_by_stop_id = {}

def time_str_to_float(t):
    parts = t.split(':')
    hours, mins, secs = map(float, parts)
    return hours * 60 * 60 + mins * 60 + secs
assert time_str_to_float('01:23:00') == 1 * 60 * 60 + 23 * 60

for stop in csv.DictReader(open('google_transit/stops.txt')):
    if stop['parent_station']:
        station_ids_by_stop_id[stop['stop_id']] = stop['parent_station']
    else:
        stations_by_id[stop['stop_id']] = {
            'name': stop['stop_name'],
            'lat': float(stop['stop_lat']),
            'lon': float(stop['stop_lon'])
        }

routes_by_id = {}
for route in csv.DictReader(open('google_transit/routes.txt')):
    routes_by_id[route['route_id']] = route

weekday_service_ids = set(['A20171105WKD', 'B20171105WKD', 'R20171105WKD'])
trips_by_id = {}

for trip in csv.DictReader(open('google_transit/trips.txt')):
    if trip['service_id'] in weekday_service_ids:
        trips_by_id[trip['trip_id']] = trip

stop_times_by_line_and_station = defaultdict(list)

stop_times_by_trip_id = defaultdict(list)
for stop_time in csv.DictReader(open('google_transit/stop_times.txt')):
    trip_id = stop_time['trip_id']
    if trip_id in trips_by_id:
        stop_id = stop_time['stop_id']
        station_id = station_ids_by_stop_id.get(stop_id, stop_id)
        d = {
            "order": int(stop_time['stop_sequence']),
            "station_id": station_id,
            "time": time_str_to_float(stop_time['departure_time'])
        }
        stop_times_by_trip_id[trip_id].append(d)
        
        trip = trips_by_id[trip_id]
        line = routes_by_id[trip['route_id']]['route_short_name']
        stop_name = stations_by_id[station_id]['name']
        stop_times_by_line_and_station[(line, station_id)].append(d['time'])

class TrainRun(object):
    def __init__(self, trip_id, stop_times):
        stop_times = list(sorted(stop_times, key=lambda x: x['order']))
        self.trip = trips_by_id[trip_id]
        self.stop_times = stop_times
        self.station_sequence = [stop_time['station_id'] for stop_time in stop_times]
        self.times_for_stations = {stop_time['station_id']: stop_time['time'] for stop_time in stop_times}
        self.midpoint_time = stop_times[int(len(stop_times) / 2)]['time']
        self.route = routes_by_id[self.trip['route_id']]
        self.line = self.route['route_short_name']
    
    def times_between_stops(self):
        times = {}
        for prev_station, next_station in zip(self.station_sequence[:-1], self.station_sequence[1:]):
            prev_time = self.times_for_stations[prev_station]
            next_time = self.times_for_stations[next_station]
            duration = next_time - prev_time
            times[(prev_station, next_station)] = duration
            times[(next_station, prev_station)] = duration
            # prev_name = stations_by_id[prev_station]['name']
            # next_name = stations_by_id[next_station]['name']
            # print("Time between {} and {}: {} mins".format(prev_name, next_name, duration / 60))
        return times

def select_best_run(runs, time=9*60*60):
    return min(runs, key=lambda run: abs(run.midpoint_time - time))

runs_by_trip_id = {id: TrainRun(id, times) for id, times in stop_times_by_trip_id.items()}
runs_by_line = defaultdict(list)
for run in runs_by_trip_id.values():
    runs_by_line[run.line].append(run)

runs_by_line = {line: select_best_run(runs) for line, runs in runs_by_line.items()}    

# compute the frequency of train arrivals between 8am and 8pm at each station, in terms of avg seconds between trains:
def compute_frequency(times):
    min_time = 8 * 60 * 60
    max_time = 20 * 60 * 60
    times = [t for t in times if t >= min_time and t <= max_time]
    if len(times) == 0: return None
    return (max_time - min_time) / len(times)

def is_terminus(line, station_id):
    run = runs_by_line[line]
    return station_id in (run.station_sequence[0], run.station_sequence[-1])

arrival_frequencies = defaultdict(dict)
for (line, station_id), times in stop_times_by_line_and_station.items():
    freq = compute_frequency(times)
    if freq is None: continue
    
    stop_name = stations_by_id[station_id]['name']
    if not is_terminus(line, station_id):
        freq *= 2 # b/c trains are going in two directions
    
    arrival_frequencies[station_id][line] = freq
#     print("{} ({}): every {} seconds".format(stop_name, line, compute_frequency(times)))

lines = {line: 
            {
                "stations": run.station_sequence, 
                "color": '#' + run.route['route_color']
            }
        for line, run in runs_by_line.items()}
subway_json = {
    "lines": lines,
    "stations": stations_by_id
}

open('subway.json', 'w').write(json.dumps(subway_json))


# compute a routing graph:
# the node for being at a station is represented by a station_id
# the node for being on a train at a station in a given direction is referenced by "station_id+LINE" or "station_id-LINE", depending on direction 
edges = defaultdict(list) # keys are the source nodes; values are a list of ({to_node: node id, time: time in seconds})
for line, run in runs_by_line.items():
    times_between_stops = run.times_between_stops()
    
    for (station_seq, direction) in [(run.station_sequence, '+'), (list(reversed(run.station_sequence)), '-')]:
        # add edges for boarding and exiting the train:
        for station_id in station_seq:
            if station_id in arrival_frequencies and line in arrival_frequencies[station_id]:
                # boarding:
                from_node = station_id
                to_node = station_id + direction + line
                time = arrival_frequencies[station_id][line] / 2 # on average, it'll take half the 'time between trains' to board one or transfer
                edges[from_node].append({"to_node": to_node, "time": time})
                # leaving is free:
                edges[to_node].append({"to_node": from_node, "time": 0})
            
        # add edges for moving between stations:
        for prev_station, next_station in zip(station_seq[:-1], station_seq[1:]):
            time_between = times_between_stops[(prev_station, next_station)]
            from_node = prev_station + direction + line
            to_node = next_station + direction + line
            edges[from_node].append({"to_node": to_node, "time": time})

# add edges for transfers:
for xfer in csv.DictReader(open('google_transit/transfers.txt')):
    from_id = xfer['from_stop_id']
    to_id = xfer['to_stop_id']
    time = float(xfer['min_transfer_time'])
    for (a, b) in [(from_id, to_id), (to_id, from_id)]:
        edges[a].append({"to_node": b, "time": time})

open('routing_graph.json', 'w').write(json.dumps({"edges": edges}))

