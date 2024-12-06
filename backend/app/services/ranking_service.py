from .. import database

def simulate_position(points: int):
    if points > database.data_manager.max_point:
        return {
            "error": "Your points exceed the max in our dataset. No higher position available."
        }
    position, additional = database.data_manager.get_position_by_points(points)
    if position is None:
        return {
            "error": "No matching position found. Please contact support."
        }
    return {
        "position": position,
        "additional_points_needed": additional
    }
