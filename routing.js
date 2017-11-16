
function djikstras(startNode, destNode, edgeFunc) {
  // edgeFunc takes a node and returns an array of `{node, cost}`
  // returns either `null` or `{path, cost}`, where `path` is a list of node ids
  let heap = new Heap((a, b) => b.time - a.time);
  heap.push({path: [startNode], time: 0});
  let seen = {};
  while (heap.length < 10000) {
    let item = heap.pop();
    if (!item) return null; // no path found
    let {path, time} = item;
    for (let edge of edgeFunc(path[path.length-1])) {
      let toNode = edge.to_node;
      if (!seen[toNode]) {
        seen[toNode] = true;
        let newPath = [...path, toNode];
        let newCost = time + edge.time;
        if (toNode === destNode) {
          return {path: newPath, time: newCost};
        } else {
          heap.push({path: newPath, time: newCost});
        }
      }
    }
  }
}

function djikstrasAllNodes(startNode, edgeFunc) {
  // edgeFunc takes a node and returns an array of `{node, cost}`
  // returns a dictionary mapping each node ID to the cost of reaching it
  let costs = {};
  costs[startNode] = 0;
  
  let heap = new Heap((a, b) => b.time - a.time);
  heap.push({path: [startNode], time: 0});
  let seen = {};
  while (heap.length > 0) {
    let item = heap.pop();
    let {path, time} = item;
    for (let edge of edgeFunc(path[path.length-1])) {
      let toNode = edge.to_node;
      if (costs[toNode] === undefined) {
        let newPath = [...path, toNode];
        let newCost = time + edge.time;
        costs[toNode] = newCost;
        heap.push({path: newPath, time: newCost});
      }
    }
  }
  return costs;
}


function travelTime(fromId, toId) {
  return djikstras(fromId, toId, (node) => routing_graph.edges[node] || []).time;
}

function travelTimesToAllStations(fromStationId) {
  let timesByNode = djikstrasAllNodes(fromStationId, (node) => routing_graph.edges[node] || []);
  let timesByStation = {};
  for (let id of Object.keys(subway.stations)) {
    timesByStation[id] = timesByNode[id];
    console.log('time to ', subway.stations[id], ':', timesByStation[id] / 60, 'minutes');
  }
  return timesByStation;
}

// console.log(travelTime('725', 'F20') / 60);
// travelTimesToAllStations('F20'); // bergen st (F)

