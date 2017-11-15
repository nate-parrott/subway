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

class TrainRun(object):
    def __init__(self, trip_id, stop_times):
        stop_times = list(sorted(stop_times, key=lambda x: x['order']))
        self.trip = trips_by_id[trip_id]
        self.stop_times = stop_times
        self.station_sequence = [stop_time['station_id'] for stop_time in stop_times]
        self.midpoint_time = stop_times[int(len(stop_times) / 2)]['time']
        self.route = routes_by_id[self.trip['route_id']]
        self.line = self.route['route_short_name']

def select_best_run(runs, time=9*60*60):
    return min(runs, key=lambda run: abs(run.midpoint_time - time))

runs_by_trip_id = {id: TrainRun(id, times) for id, times in stop_times_by_trip_id.items()}
runs_by_line = defaultdict(list)
for run in runs_by_trip_id.values():
    runs_by_line[run.line].append(run)

runs_by_line = {line: select_best_run(runs) for line, runs in runs_by_line.items()}
# print(runs_by_line.keys())

# run = runs_by_line['N']
# print('LINE:', run.line)
# print('Midpoint time:', run.midpoint_time)
# for station_id in run.station_sequence:
#     print(stations_by_id[station_id]['name'])
#

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
