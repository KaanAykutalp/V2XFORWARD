import traci

# Start SUMO
traci.start(["sumo-gui", "-c", "map.sumo.cfg"])

# Step once to initialize
traci.simulationStep()

# Create a custom vehicle type (no need to be in XML)
traci.vehicletype.copy("DEFAULT_VEHTYPE", "car")

# Define a route (replace with valid edges from your map!)
edge_list = ["79264928#0", "79264928#1", "79264928#2"]
traci.route.add("route0", edge_list)

# Add vehicle with your dynamic type and route
traci.vehicle.add(vehID="newVehicle", routeID="route0", typeID="car")
traci.vehicle.setSpeed("newVehicle", 15)

# Run simulation
vehicle_id = "newVehicle"

for step in range(10000):
    traci.simulationStep()

    if vehicle_id in traci.vehicle.getIDList():
        pos = traci.vehicle.getPosition(vehicle_id)
        speed = traci.vehicle.getSpeed(vehicle_id)
        print(f"Step {step}: {vehicle_id} at {pos}, speed: {speed}")

# Close TraCI
traci.close()




"""
import traci
import sumolib

#launch sumo with the config file
sumoBinary = "sumo-gui"

# step-by-step simulation
for step in range(1000):
    traci.simulationStep()

    #getting infor or controlling
    vehicle_ids = traci.vehicle.getIDList()
    for vid in vehicle_ids:
        speed = traci.vehicle.getSpeed(vid)
        print(f"{vid} speed: {speed}")

traci.close()
"""