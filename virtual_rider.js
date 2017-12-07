
let atStopState = (id) => "at_stop:" + id;
let onTripState = (id) => "on_trip:" + id;

class StateMap {
	constructor() {
		this.earliestRidersAtStates = {};
	}
	addRider(rider) {
		let existing = this.earliestRidersAtStates[rider.state];
		if (!existing || rider.time < existing.time) {
			this.earliestRidersAtStates[rider.state] = rider;
			return true;
		}
		return false;
	}
	addRiderAndTransfersByAppendingStop(oldRider, stopId, time, allTransfers) {
		let direct = oldRider.byAdding(atStopState(stopId), time);
		if (this.addRider(direct)) {
			// add all transfers:
			for (let transfer of allTransfers[stopId] || []) {
				this.addRiderAndTransfersByAppendingStop(direct, transfer['to'], time + transfer.time, allTransfers);
			}
		}
	}
}

class Rider {
	constructor(states, time) {
		this.states = states; // parts are strings
		this.time = time;
		this.state = states.length ? states[states.length-1] : null;
	}
	byAdding(state, finalTime) {
		return new Rider([...this.states, state], finalTime);
	}
}

let computeTravelTimes = (startStationId, endStationIds, gtfs_json, startTime, serviceGroup) => {
	let stateMap = new StateMap();
	
	let emptyPath = new Rider([], startTime);
	stateMap.addRiderAndTransfersByAppendingStop(emptyPath, startStationId, startTime, gtfs_json.transfers);
	// console.log(stateMap);
	
	for (let {time, trip_id, stop_id, route_name} of gtfs_json.events_by_service_group[serviceGroup]) {
		// model exiting the train:
		let riderOnTrain = stateMap.earliestRidersAtStates[onTripState(trip_id)];
		if (riderOnTrain && riderOnTrain.time <= time) {
			stateMap.addRiderAndTransfersByAppendingStop(riderOnTrain, stop_id, time, gtfs_json.transfers);
		}
		// model boarding the train:
		let riderOnPlatform = stateMap.earliestRidersAtStates[atStopState(stop_id)];
		if (riderOnPlatform && riderOnPlatform.time <= time) {
			let riderOnTrain = riderOnPlatform.byAdding(onTripState(trip_id), time);
			stateMap.addRider(riderOnTrain);
		}
	}
	
	let travelTimes = {};
	for (let stationId of endStationIds) {
		let rider = stateMap.earliestRidersAtStates[atStopState(stationId)];
		travelTimes[stationId] = rider ? rider.time - startTime : null;
	}
	return travelTimes;
}

// let HOURS = 60 * 60;
// console.log(computeTravelTimes('127', Object.keys(subway.stations), 8*HOURS, gtfs_json, 'weekdays'));
