class Event:
    def __init__(self, time, type, data=None, priority=10):
        """
        Initialize an event object.

        :param time: The simulation time at which the event should occur.
        :param type: The type of the event (e.g., 'SEND_BEACON', 'GENERATE_EVENT_MESSAGE').
        :param data: Optional dictionary containing additional event-specific data.
        :param priority: Priority level of the event. Lower values indicate higher priority.
        """
        self.time = time
        self.type = type
        self.data = data
        self.priority = priority

    def __lt__(self, other):
        """
        Define the comparison behavior for priority queue sorting.
        Events are first compared by time; if equal, then by priority.
        """
        if self.time == other.time:
            return self.priority < other.priority
        return self.time < other.time

    def __repr__(self):
        """
        String representation of the event for debugging purposes.
        """
        return f"Packet(time={self.time:.3f}, type={self.type}, priority={self.priority})"
