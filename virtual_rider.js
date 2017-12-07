
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
		this.states = states; // states are strings
		this.time = time;
		this.state = states.length ? states[states.length-1] : null;
	}
	byAdding(state, finalTime) {
		return new Rider([...this.states, state], finalTime);
	}
}

let _computeTravelTimes = (startStationId, endStationIds, transfers, events, startTime) => {
	let stateMap = new StateMap();
	
	let emptyPath = new Rider([], startTime);
	stateMap.addRiderAndTransfersByAppendingStop(emptyPath, startStationId, startTime, transfers);
	// console.log(stateMap);
	
	for (let {time, trip_id, stop_id, route_name} of events) {
		// model exiting the train:
		let riderOnTrain = stateMap.earliestRidersAtStates[onTripState(trip_id)];
		if (riderOnTrain && riderOnTrain.time <= time) {
			stateMap.addRiderAndTransfersByAppendingStop(riderOnTrain, stop_id, time, transfers);
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
		travelTimes[stationId] = rider ? rider.time - startTime : 400 * 60;
	}
	return travelTimes;
}

let scheduleCache = {};
let getSchedule = (name, callback) => {
	if (scheduleCache[name]) {
		callback(scheduleCache[name]);
	} else {
		d3.json('/schedules/' + name + '.json', (schedule) => {
			scheduleCache[name] = schedule;
			callback(schedule);
		})
	}
}
let computeTravelTimes = (startStationId, scheduleName, callback) => {
	getSchedule(scheduleName, (schedule) => {
		callback(_computeTravelTimes(startStationId, Object.keys(subway.stations), gtfs_transfers, schedule.events, schedule.start_time));
	});
};

// let HOURS = 60 * 60;
// console.log(computeTravelTimes('127', Object.keys(subway.stations), 8*HOURS, gtfs_json, 'weekdays'));
