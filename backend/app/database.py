import pandas as pd
from .config import DATASET_PATH

class DataManager:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.data = None
        self.max_point = None

    def load_data(self):
        self.data = pd.read_excel(self.data_path)
        self.data = self.data.sort_values(["Position", "Points"], ascending=[True, False])
        # Create a set for quick lookup of points
        self.points_set = set(self.data["Points"].unique())
        self.max_point = self.data["Points"].max()

    def get_position_by_points(self, points: int):
        # Finds the smallest number of points >= the given points that exists in the dataset
        adjusted_points = points
        while adjusted_points not in self.points_set:
            adjusted_points += 1
            if adjusted_points > self.max_point:
                return None, None
        matched = self.data.loc[self.data["Points"] == adjusted_points].iloc[0]
        position = matched["Position"]
        additional_points_needed = adjusted_points - points
        return position, additional_points_needed

# Create a global instance
data_manager = DataManager(DATASET_PATH)
