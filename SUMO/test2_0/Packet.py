class Packet:
    def __init__(self, creation_time, packet_id, source_id, destination_id, packet_size, type='BEACON', data=None,
                 hop_count=0, original_source_id=None, dest_area=None):
        self.creation_time = creation_time  # packet created time
        self.id = packet_id
        self.source_id = source_id  # source vehicle ID
        self.destination_id = destination_id  # destination vehicle ID
        self.packet_size = packet_size
        self.type = type  # BEACON, EVENT
        self.data = data if data is not None else {}
        # For forwarding
        self.hop_count = hop_count
        self.original_source_id = original_source_id if original_source_id else source_id
        self.dest_area = dest_area  # Store destination area info for EVENT packets
