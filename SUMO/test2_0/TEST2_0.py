import heapq
import random
import math
import os
import sys
import yaml
import Tanks
import time
import Event
import Packet
import traci
import datetime
import datetime


class test:

    def __init__(self, config):

        self.packet_counter = 0
        self.current_time = 0
        self.tanks = {}
        self.config = config
        self.event_que = []
        self.sim_time = 0
        self.log_level = ['DEBUG', 'INFO', 'WARN', 'ERROR'].index(config.get('log_level', 'INFO'))
        self.log_sumo_file = config['log_sumo_path']  # if sumo cannot launch check this log
        self.log_running_file = config['log_running_path']  # this log for storing running statistic

    def schedule_event(self, delay, Type, data=None, priority=10):
        event_time = self.sim_time + delay
        if event_time < self.config['simulation_duration']:
            self.log('INFO', f"Scheduled {Type} event at time {event_time}", path=self.log_running_file)
            heapq.heappush(self.event_que, Event.Event(event_time, Type, data, priority))
        else:
            self.log('INFO', f"Event {Type} skipped as it exceeds simulation duration", path=self.log_running_file)

    def log(self, level, message, path):
        level = level.upper()
        try:
            level_idx = ['DEBUG', 'INFO', 'WARN', 'ERROR'].index(level)
        except ValueError:
            level_idx = 1  # 默认 INFO
            level = "INFO"
            message = f"Invalid log level provided, auto-corrected: {message}"

        if level_idx >= self.log_level:
            sim_time_str = f"{self.sim_time:.3f}"
            timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"{timestamp_str} | {sim_time_str} [{level}]: {message}"
            print(f"{sim_time_str} [{level}]: {message}")
            with open(path, "a") as f:
                f.write(log_line + "\n")

    def start_sumo(self):
        import traci
        sumo_binary = "sumo-gui" if self.config.get("sumo_gui", False) else "sumo"

        # check SUMO_HOME add tools path
        if "SUMO_HOME" in os.environ:
            tools_path = os.path.join(os.environ["SUMO_HOME"], "tools")
            if tools_path not in sys.path:
                sys.path.append(tools_path)
            sumo_path = os.path.join(os.environ["SUMO_HOME"], "bin", sumo_binary)
            if os.path.exists(sumo_path):
                sumo_binary = sumo_path
            else:
                self.log("WARN", f"{sumo_binary} binary not found at {sumo_path}, using system PATH.",
                         path=self.log_sumo_file)
        else:
            self.log("WARN", "SUMO_HOME environment variable not set. Assuming SUMO is in system PATH.",
                     path=self.log_sumo_file)

        # check config file is exsit or not
        sumo_cfg_file = self.config.get("sumo_cfg_file")
        if not sumo_cfg_file or not os.path.exists(sumo_cfg_file):
            self.log("ERROR", f"SUMO config file not found: {sumo_cfg_file}", path=self.log_sumo_file)
            sys.exit(1)

        # stat commend
        sumo_cmd = [
            sumo_binary,
            "-c", sumo_cfg_file,
            "--step-length", str(self.config.get("step_length", 0.1)),
            "--time-to-teleport", "-1",
            "--quit-on-end",
            # "--log-file", self.config.get("sumo_log_file", "sumo_log.txt"),
            "--seed", str(self.config.get("random_seed", 42)),
        ]

        traci_port = self.config.get("traci_port", 8813)

        self.log("INFO", f"Starting SUMO with command: {' '.join(sumo_cmd)}", path=self.log_sumo_file)

        try:
            # launch and connect TraCI
            time.sleep(1)
            traci.start(sumo_cmd, port=traci_port, label="default")
            self.log("INFO", f"SUMO started successfully on port {traci_port} and TraCI connected.",
                     path=self.log_sumo_file)
        except Exception as e:
            self.log("ERROR", f"Failed to start SUMO or connect to TraCI: {e}", path=self.log_sumo_file)
            sys.exit(1)

    # interact with sumo
    def Get_position_from_sumo(self):
        if not traci.isLoaded():
            self.log('ERROR', "FBI warning Traci is die.", path=self.log_sumo_file)
            self.event_que = []
            return
        try:
            running_tanks = set(traci.vehicle.getIDList())  # 当前在 SUMO 中运行的车辆
        except traci.TraCIException:
            self.log('ERROR', "Failed to retrieve vehicle ID list from TraCI.", path=self.log_sumo_file)
            return
        current_sim_tanks = set(self.tanks.keys())  # 模拟中记录的车辆集合
        sumo_total_tank = running_tanks

        for tank_id in sumo_total_tank - current_sim_tanks:  # new coming tank
            try:
                pos = traci.vehicle.getPosition(tank_id)
                self.tanks[tank_id] = Tanks.Tanks(tank_id, pos[0], pos[1], self.config)
                self.log('INFO', f"New tank detected: {tank_id} at position {pos}", path=self.log_running_file)

                if self.config['First_t_id'] is None:
                    self.config['First_t_id'] = tank_id
                    self.schedule_event(self.config['event_trigger_time'], 'GENERATE_EVENT_MESSAGE',
                                        {'tank_id': tank_id})
                    self.log('INFO', f"Set tank {tank_id} as source_t_id", path=self.log_running_file)
                # Do a Beacon
                self.schedule_event(random.uniform(0.01, 0.1), 'BEACON_GENERATION', {'tank_id': tank_id})
            except traci.TraCIException:
                self.log('WARN', f"Enemy tank {tank_id} position lost", path=self.log_running_file)

        for tank_id in sumo_total_tank.intersection(current_sim_tanks):
            try:
                pos = traci.vehicle.getPosition(tank_id)
                if tank_id in self.tanks:
                    self.tanks[tank_id].update_position(pos[0], pos[1])
            except traci.TraCIException:
                self.log('WARN', f"Tank {tank_id} was bombed, cannot update", path=self.log_running_file)
                if tank_id in self.tanks:
                    del self.tanks[tank_id]
        # delete the departed tanks
        for tank_id in current_sim_tanks - sumo_total_tank:
            self.log('INFO', f"Tank {tank_id} departed simulation.", path=self.log_running_file)
            if tank_id in self.tanks:
                del self.tanks[tank_id]

    # update the simulation state
    def sim_state_update(self, data):
        try:
            sim_time_now = traci.simulation.getTime()
            if sim_time_now >= self.config['simulation_duration']:
                self.log('INFO', "Simulation finished.", path=self.log_sumo_file)
                return
            # excute simulation update tank info(position)
            traci.simulationStep()
            self.Get_position_from_sumo()
            # scheduling next event after an interval
            interval = self.config.get('step_length', 0.1)
            self.schedule_event(interval, 'SIM_STATE_UPDATE', priority=1)
        except traci.TraCIException as traci_err:
            self.log('ERROR', f"TraCI error encountered: {traci_err}")
            self.event_que.clear()
        except Exception as ex:
            self.log('ERROR', f"Unexpected error during simulation update: {ex}", path=self.log_sumo_file)
            self.event_que.clear()

    # * communication model *#
    def calculate_Distance(self, tank1, tank2):
        return math.hypot(tank1.x - tank2.x, tank1.y - tank2.y)

    # Calculate loss two different models to propagation, select from config.yaml
    def calculate_received_power(self, distance):
        if distance <= 0:
            return float('-inf')
        model = self.config['propagation_model']
        if model == 'LogDistance':
            exponent = self.config['log_distance_exponent']
            ref_loss = self.config['path_loss_at_reference']
            ref_dist = self.config['reference_distance']
            if distance < ref_dist:
                path_loss_db = ref_loss
            else:
                path_loss_db = ref_loss + 10 * exponent * math.log10(distance / ref_dist)
            return self.config['tx_power_dbm'] - path_loss_db

        elif model == 'Friis':
            frequency_ghz = self.config['channel_frequency_ghz']  # GHz
            tx_gain = self.config.get('tx_antenna_gain_dbm', 0)  # dBi
            rx_gain = self.config.get('rx_antenna_gain_dbm', 0)  # dBi
            # Friis model: using distance in meters
            wavelength_m = 3e8 / (frequency_ghz * 1e9)  # Convert GHz to Hz
            if distance == 0:
                return float('-inf')
            # Free-space path loss (FSPL) in dB
            path_loss_db = 20 * math.log10(4 * math.pi * distance / wavelength_m)
            received_power = self.config['tx_power_dbm'] + tx_gain + rx_gain - path_loss_db
            return received_power
        else:
            # Fallback: simple free-space loss approximation
            path_loss_db = 20 * math.log10(distance) + 30
            return self.config['tx_power_dbm'] - path_loss_db

    def calculate_total_delay(self):
        # === Load CSMA/CA and PHY parameters from configuration ===
        SLOT_TIME = self.config['slot_time']  # Time for one backoff slot (e.g., 13μs)
        SIFS = self.config['sifs']  # Short Interframe Space (e.g., 32μs)
        DIFS = self.config['difs']  # DCF Interframe Space (SIFS + 2 × Slot)
        PHY_OVERHEAD = self.config['phy_overhead_time']  # Time for PHY preamble and header
        CWmin = self.config['cw_min']  # Minimum contention window size
        CWmax = self.config['cw_max']  # Maximum contention window size
        ACK_SIZE = self.config['ack_size_bytes']  # Size of ACK frame (typically 14 bytes)
        COLLfISION_PROB = self.config['collision_probability']  # Probability of collision per attempt
        MAX_RETX = self.config['max_retransmissions']  # Maximum number of retransmission attempts
        data_rate_bps = self.config['data_rate_mbps'] * 1e6  # Data rate in bits per second

        # === Calculate time to transmit data and ACK frames ===
        packet_bits = self.config['Beacon_packet_size'] * 8  # Convert payload size to bits
        tx_time = packet_bits / data_rate_bps  # Time to transmit the data
        ack_time = (ACK_SIZE * 8) / data_rate_bps  # Time to transmit the ACK

        total_delay = 0  # Accumulate total delay over attempts
        cw = CWmin  # Initial contention window

        # === Attempt  smission up to MAX_RETX times ===
        for attempt in range(MAX_RETX + 1):
            # Random backoff time within current contention window
            backoff_slots = random.randint(0, cw)
            backoff_time = backoff_slots * SLOT_TIME

            # Total delay for this attempt
            attempt_delay = DIFS + backoff_time + PHY_OVERHEAD + tx_time + SIFS + ack_time

            total_delay += attempt_delay

            # Simulate whether a collision occurred
            if random.random() >= COLLfISION_PROB:
                # Transmission succeeded
                return total_delay
            else:
                # Collision occurred, expand contention window (binary exponential backoff)
                cw = min((cw + 1) * 2 - 1, CWmax)
                print(cw)

        # === All attempts failed: return infinite delay (could also raise an error or log failure) ===
        return float('inf')

    # Communication
    # Generate BEACON
    def beacon_generation(self, data):
        tank_id = data['tank_id']
        if tank_id not in self.tanks:
            self.log('INFO', f"Vehicle {tank_id} not in tanks.", path=self.log_running_file)  # Debug log
            return
        sender = self.tanks[tank_id]
        self.packet_counter += 1
        beacon_packet = Packet.Packet(
            packet_id=self.packet_counter,
            source_id=sender.id,
            destination_id='BROADCAST',
            packet_size=self.config['Beacon_packet_size'],
            creation_time=self.sim_time,
            type='BEACON',
            data={'sender_x': sender.x, 'sender_y': sender.y}
        )
        self.schedule_event(0.00001, 'TX_BEACON', {'packet': beacon_packet}, priority=3)
        # DO ANOATHER BEACON GENERATION
        next_beacon_delay = self.config['beacon_slot']
        jitter = random.uniform(-next_beacon_delay * 0.05, next_beacon_delay * 0.05)
        final_delay = max(0.001, next_beacon_delay + jitter)
        self.schedule_event(final_delay, 'BEACON_GENERATION', {'tank_id': tank_id})

    # tx beacon
    def tx_beacon(self, data):
        self.log('INFO', "TX_BEACON triggered!", path=self.log_running_file)
        packet = data['packet']
        sender_id = packet.source_id
        if sender_id not in self.tanks:
            self.log('INFO', f"Sender tank {sender_id} not in tanks, skipping transmission.",
                     path=self.log_running_file)
            return
        sender = self.tanks[sender_id]
        for receiver_id, receiver in self.tanks.items():
            if sender.id == receiver.id:
                continue
            distance = self.calculate_Distance(sender, receiver)
            rx_power_dbm = self.calculate_received_power(distance)
            self.log('INFO', f"distance{distance} and power{rx_power_dbm}", path=self.log_running_file)
            # only transmit in given range
            if distance < self.config['tx_range'] and rx_power_dbm >= self.config['sensitivity_dbm']:
                Total_delay = self.calculate_total_delay()
                self.schedule_event(Total_delay, 'RECEIVE_BEACON',
                                    {'receiver_id': receiver.id, 'packet': packet}, priority=1)
            else:
                self.log('INFO', f"OUT OF COMMUNICATION", path=self.log_running_file)

    # receive beacon
    def receive_beacon(self, data):
        sender_id = data['packet'].source_id
        receiver_id = data['receiver_id']
        self.log('INFO', f"Vehicle {receiver_id} received beacon from {sender_id}", path=self.log_running_file)
        return

    def initialize_simulation(self):
        self.log('INFO', "Initializing simulation try to start sumo...", path=self.log_sumo_file)
        self.start_sumo()
        self.schedule_event(0.0, 'SIM_STATE_UPDATE', priority=1)

    def run(self):
        if self.initialize_simulation():
            self.log("INFO", "Simulation starting...", path=self.log_sumo_file)
        max_sim_time = self.config.get("simulation_duration", 200)
        # if schedule event is the type in the fuction_map it will excute the function
        function_map = {
            'SIM_STATE_UPDATE': self.sim_state_update,
            'BEACON_GENERATION': self.beacon_generation,
            'TX_BEACON': self.tx_beacon,
            'RECEIVE_BEACON': self.receive_beacon
        }

        while self.sim_time < max_sim_time and self.event_que:
            event = heapq.heappop(self.event_que)
            self.sim_time = event.time
            Boss = function_map.get(event.type)
            if Boss:
                Boss(event.data)
            else:
                self.log("ERROR", f"Unknown event type: {event.type}", path=self.log_running_file)

        traci.close()


with open("/home/dante/code/SDN/SUMO/Test2_0/configs.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)
simulator = test(CONFIG)
simulator.run()
