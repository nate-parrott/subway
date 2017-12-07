import json
import csv
from collections import defaultdict
import os

HOURS = 60 * 60

def gtfs_json(gtfs_path, included_service_groups=[], min_time=0, max_time=48*HOURS):
    def read_csv(name):
        return list(csv.DictReader(open(os.path.join(gtfs_path, name + '.txt'))))
    
    parent_stops = {}
    for stop in read_csv('stops'):
        if stop['parent_station']:
            parent_stops[stop['stop_id']] = stop['parent_station']
    def resolve_stop_id(stop_id):
        return parent_stops.get(stop_id, stop_id)
    
    transfers = defaultdict(list)
    for transfer in read_csv('transfers'):
        if transfer['transfer_type'] != '3': # 3 is 'no transfers'
            from_stop_id = resolve_stop_id(transfer['from_stop_id'])
            to_stop_id = resolve_stop_id(transfer['to_stop_id'])
            transfers[from_stop_id].append({"to": to_stop_id, "time": float(transfer['min_transfer_time'] or "0")})
    
    routes_by_id = {route['route_id']: route for route in read_csv('routes')}
    trips_by_id = {trip['trip_id']: trip for trip in read_csv('trips')}
    stop_times = read_csv('stop_times')
    
    service_groups = {
        'saturday': ['A20171105SAT', 'B20171105SAT'],
        'sunday': ['A20171105SUN', 'B20171105SUN'],
        'weekdays': ['A20171105WKD', 'B20171105WKD']
    }
    
    events_by_service_group = {}
    for service_group, service_ids in service_groups.items():
        if service_group in included_service_groups:
            events = []
            for stop_time in stop_times:
                trip = trips_by_id[stop_time['trip_id']]
                route = routes_by_id[trip['route_id']]
                if trip['service_id'] in service_ids:
                    time = time_str_to_float(stop_time['departure_time'])
                    if time >= min_time and time <= max_time:
                        stop_id = resolve_stop_id(stop_time['stop_id'])
                        events.append({"time": time, "trip_id": stop_time['trip_id'], "stop_id": stop_id, "route_name": route['route_short_name']})
            events.sort(key=lambda x: x['time'])
            events_by_service_group[service_group] = events
    return {
        "transfers": transfers,
        "events_by_service_group": events_by_service_group
    }
        
def time_str_to_float(t): # in seconds
    parts = t.split(':')
    hours, mins, secs = map(float, parts)
    return hours * 60 * 60 + mins * 60 + secs
assert time_str_to_float('01:23:00') == 1 * 60 * 60 + 23 * 60

if __name__ == '__main__':
    j = gtfs_json('google_transit', ['weekdays'], 8*HOURS, 11*HOURS)
    open('gtfs_json.js', 'w').write('gtfs_json = ' + json.dumps(j))
