import traci
import random
import time


TX_RANGE = 300
BROADCAST_INTERVAL = 30
CW_MIN = 2
CW_MAX = 5
SIM_STEPS = 1000


nodes = {}
messages = {}

def distance(p1, p2):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5

def sense_channel(veh_id, step):

    my_pos = traci.vehicle.getPosition(veh_id)
    for other_id, other_state in nodes.items():
        if other_id == veh_id:
            continue
        if other_state['is_transmitting']:
            if distance(my_pos, traci.vehicle.getPosition(other_id)) < TX_RANGE:
                return False
    return True

def generate_message(veh_id, step):

    msg_id = f"{veh_id}_{step}"
    messages[msg_id] = {
        'origin': veh_id,
        'ttl': 3,
        'time': step
    }
    nodes[veh_id]['msg_queue'].append(msg_id)
    print(f"[{step}] {veh_id} generated message {msg_id}")

def simulate_communication(step):

    for veh_id in traci.vehicle.getIDList():
        if veh_id not in nodes:
            nodes[veh_id] = {
                'msg_cache': set(),
                'msg_queue': [],
                'backoff': 0,
                'is_transmitting': False,
                'tx_time': -1
            }

        state = nodes[veh_id]

        # Periodic broadcast
        if step % BROADCAST_INTERVAL == 0:
            generate_message(veh_id, step)

        # Handle backoff if needed
        if state['backoff'] > 0:
            state['backoff'] -= 1
            continue

        #  send queued message
        for msg_id in state['msg_queue']:
            if msg_id in state['msg_cache']:
                continue  # Already transmitted

            if not sense_channel(veh_id, step):
                state['backoff'] = random.randint(CW_MIN, CW_MAX)
                print(f"[{step}] {veh_id} senses busy channel, backs off")
                return

            # Transmit
            print(f"[{step}] {veh_id} transmits {msg_id}")
            state['is_transmitting'] = True
            state['tx_time'] = step
            state['msg_cache'].add(msg_id)


            # Forward to neighbors
            for other_id in traci.vehicle.getIDList():
                if other_id == veh_id:
                    continue


                if other_id not in nodes:
                    nodes[other_id] = {
                        'msg_cache': set(),
                        'msg_queue': [],
                        'backoff': 0,
                        'is_transmitting': False,
                        'tx_time': -1
                    }

                if distance(traci.vehicle.getPosition(veh_id), traci.vehicle.getPosition(other_id)) < TX_RANGE:
                    if msg_id not in nodes[other_id]['msg_cache']:
                        # Forward message to neighbor
                        nodes[other_id]['msg_queue'].append(msg_id)
                        print(f"[{step}] {veh_id} → {other_id}: forward {msg_id}")

            # Transmission done
            break  # One message per step

        # Reset transmit state next step
        state['is_transmitting'] = False

# === TraCI setup ===
sumo_cmd = ["sumo-gui", "-c", "map.sumo.cfg"]
traci.start(sumo_cmd)

for step in range(SIM_STEPS):
    traci.simulationStep()
    simulate_communication(step)

traci.close()
