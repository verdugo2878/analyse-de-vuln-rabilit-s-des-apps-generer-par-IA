from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id, username, email, is_admin):
        self.id = id
        self.username = username
        self.email = email
        self.is_admin = bool(is_admin)
    
    def get_id(self):
        return str(self.id)

class Room:
    def __init__(self, id, name, description, capacity, price_per_hour, equipment, is_active):
        self.id = id
        self.name = name
        self.description = description
        self.capacity = capacity
        self.price_per_hour = price_per_hour
        self.equipment = equipment
        self.is_active = is_active

class Booking:
    def __init__(self, id, user_id, room_id, start_time, end_time, status):
        self.id = id
        self.user_id = user_id
        self.room_id = room_id
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
