class Guest:
    def __init__(self, guest_id, first_name, last_name, family=None, side=None):
        self.id = guest_id
        self.first_name = first_name
        self.last_name = last_name
        self.family = family
        self.side = side

        self.table = None
        self.seat = None

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def short_name(self):
        if self.last_name:
            return f"{self.first_name} {self.last_name[0]}"
        return self.first_name

class Seat:
    def __init__(self, seat_number, table=None):
        self.number = seat_number
        self.table = table
        self.guest = None

    @property
    def id(self):
        return f"{self.table.name}:{self.number}"

class Table:
    def __init__(self, table_name, seat_count, table_type="round"):

        self.name = table_name
        self.type = table_type

        self.seats = []
        for i in range(seat_count):
            self.seats.append(Seat(i + 1, self))