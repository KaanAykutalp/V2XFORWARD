class Tanks:
    def __init__(self, tank_id, x, y, config):
        """
        初始化车辆对象
        :param vehicle_id: 车辆唯一 ID（字符串或整数）
        :param x: 初始 x 坐标
        :param y: 初始 y 坐标
        :param config: 配置参数字典（来自主仿真类）
        """
        self.id = tank_id
        self.x = x
        self.y = y
        self.config = config

        # 可选属性：可扩展的状态数据
        self.last_beacon_time = 0.0  # 上次发送 BEACON 的时间
        self.packet_queue = []       # 存储等待发送的数据包
        self.location_table = {}     # 位置表：用于存储其他车辆位置
        self.received_packets = set()  # 用于记录接收过的 packet ID 防止重复处理

    def update_position(self, new_x, new_y):
        """
        update position
        """
        self.x = new_x
        self.y = new_y

    def __repr__(self):
        return f"Vehicle(id={self.id}, x={self.x:.1f}, y={self.y:.1f})"


