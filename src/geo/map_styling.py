"""
GIS Map Styling Module

This module handles the styling of GIS map markers based on ownership and service type.
Rules are defined in `docs/gis_map_styling.md` and `docs/gis_icon_map.csv`.
"""
import pandas as pd

class MapStyler:
    """
    Handles the styling of GIS map markers.
    """

    def __init__(self, ownership_path: str, icon_map_path: str):
        """
        Initialize the MapStyler with ownership and icon mapping data.

        Args:
            ownership_path (str): Path to the ownership_by_type.csv file.
            icon_map_path (str): Path to the gis_icon_map.csv file.
        """
        self.ownership_df = pd.read_csv(ownership_path)
        self.icon_map_df = pd.read_csv(icon_map_path)

    def get_marker_style(self, facility_type: str) -> dict:
        """
        Get the marker style (color, shape, icon) for a given facility type.

        Args:
            facility_type (str): The type of the facility.

        Returns:
            dict: A dictionary containing 'color', 'shape', and 'icon' keys.
        """
        # Get ownership class and color
        ownership_info = self.ownership_df[self.ownership_df['facility_type'] == facility_type]
        if ownership_info.empty:
            return {
                "color": "#6B7280",  # Grey for unknown types
                "shape": "circle",
                "icon": "question"
            }

        # Get icon and shape
        icon_info = self.icon_map_df[self.icon_map_df['facility_type'] == facility_type]
        if icon_info.empty:
            return {
                "color": ownership_info['colour_hex'].values[0],
                "shape": "circle",
                "icon": "question"
            }

        return {
            "color": ownership_info['colour_hex'].values[0],
            "shape": icon_info['marker_shape'].values[0],
            "icon": icon_info['suggested_icon_name'].values[0]
        }