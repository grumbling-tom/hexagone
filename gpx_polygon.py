import gpxpy
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Polygon, MultiPolygon
from shapely.ops import polygonize
from math import cos, radians
from pyproj import Geod
from geopy.distance import geodesic  # Import geodesic for distance calculation
import h3  # Import h3 library


def polygons_to_h3_ids(shapely_geometry, h3_resolution=10):
    """
    Converts a Shapely Polygon or MultiPolygon into a list of H3 cell IDs
    that cover the geometry at a specified resolution.

    Args:
        shapely_geometry (shapely.geometry.Polygon or shapely.geometry.MultiPolygon):
            The input polygon(s) to convert.
        h3_resolution (int): The H3 resolution (0-15) for the cells.

    Returns:
        list: A list of H3 cell IDs (strings).
    """
    print(f"DEBUG: Entering polygons_to_h3_ids function for geometry type: {type(shapely_geometry)}")
    h3_module_api = None
    if hasattr(h3, '__version__'):
        print(f"DEBUG: H3 module version: {h3.__version__}")
    else:
        print("DEBUG: H3 module has no __version__ attribute.")

    h3_ids = []

    # Handle single Polygon case
    if isinstance(shapely_geometry, Polygon):
        # The polygon should already be valid by this point from get_gpx_enclosed_polygons
        if not shapely_geometry.is_valid:
            print(f"WARNING: Polygon is invalid (not fixed by upstream). {shapely_geometry.is_valid}. Skipping H3 polyfill.")
            return []
        shapely_geometry_is_empty = shapely_geometry.is_empty
        if shapely_geometry_is_empty:
            print("DEBUG: Polygon is empty. Skipping H3 polyfill.")
            return []

        # Convert Shapely Polygon to H3Shape
        h3_shape = h3.geo_to_h3shape(shapely_geometry.__geo_interface__)
        current_poly_h3_ids = list(h3.h3shape_to_cells(h3_shape, h3_resolution))
        h3_ids.extend(current_poly_h3_ids)
        print(f"DEBUG: h3shape_to_cells generate {len(current_poly_h3_ids)} H3 IDs for this single Polygon.")

    elif isinstance(shapely_geometry, MultiPolygon):
        print(f"DEBUG: Geometry is a MultiPolygon with {len(shapely_geometry.geoms)} geometries.")
        for i, poly in enumerate(shapely_geometry.geoms):
            if isinstance(poly, Polygon) and poly.is_valid and not poly.is_empty:
                # Recursive call for each individual polygon within the MultiPolygon
                h3_ids.extend(polygons_to_h3_ids(poly, h3_resolution))

    return h3_ids


def get_gpx_enclosed_polygons(gpx_file_path, closure_tolerance_meters=8, simplify_to_meters=8, check_step=8):
    """
    Reads a GPX file, simplifies the route, and finds a closed loop based on a distance tolerance
    between points, returning the resulting Shapely Polygon or MultiPolygon.

    Args:
        gpx_file_path (str): The path to the GPX file.
        closure_tolerance_meters (float): The maximum distance between two points to consider them a closure.
        simplify_to_meters (float): The target distance between points after simplification, in meters.
        check_stop_limit (int): The minimum number of points to skip before checking for closure.

    Returns:
        shapely.geometry.Polygon or shapely.geometry.MultiPolygon or None: The found polygon(s).
    """
    try:
        with open(gpx_file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
    except FileNotFoundError:
        print(f"Error: GPX file not found at {gpx_file_path}")
        return None, None
    except Exception as e:
        print(f"Error parsing GPX file: {e}")
        return None, None

    # Store track points as (latitude, longitude) for gpxpy
    original_points_latlon = []

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                original_points_latlon.append((point.latitude, point.longitude))

    if not original_points_latlon:
        print("No track points found in GPX file path")
        return None, None

    print(f"Original number of points: {len(original_points_latlon)}")

    # --- Simplify the LineString ---
    # Simplification is in the original points (lon, lat) for shapely simplification
    original_line_shapely = LineString([(p[1], p[0]) for p in original_points_latlon])

    min_lat = min(p[0] for p in original_points_latlon)
    max_lat = max(p[0] for p in original_points_latlon)
    avg_lat = (min_lat + max_lat) / 2

    # Approximate degrees per meter at average latitude
    degrees_per_meter_lat = 1 / 111320.0
    degrees_per_meter_lon = 1 / (111320.0 * abs(cos(radians(avg_lat))))

    target_simplification_degrees = max(degrees_per_meter_lat, degrees_per_meter_lon) * simplify_to_meters
    simplified_line_shapely = original_line_shapely.simplify(target_simplification_degrees, preserve_topology=True)

    # Convert simplified coordinates back to (lat, lon)
    points_latlon = [(p[1], p[0]) for p in simplified_line_shapely.coords]

    print(f"Number of points after simplification: {len(points_latlon)}")

    # --- Estimate distance between consecutive points (on simplified route) ---
    consecutive_distances = []
    for i in range(len(points_latlon) - 1):
        dist = geodesic(points_latlon[i], points_latlon[i + 1]).meters
        consecutive_distances.append(dist)
    avg_consecutive_distance = sum(consecutive_distances) / len(consecutive_distances) if consecutive_distances else 0
    print(f"Avg distance between consecutive points (after simplification): {avg_consecutive_distance:.2f} meters.")

    # --- Find the Closing Point(s) ---
    found_index = -1
    start_enclosed_index = -1
    found = False

    for i in range(check_step, len(points_latlon)):
        for j in range(i - check_step + 1):
            distance = geodesic(points_latlon[i], points_latlon[j]).meters
            if distance < closure_tolerance_meters:
                start_enclosed_index = j
                found_index = i
                print(f"DEBUG found closure: Point {i} is distance {distance:.2f}m from Point {j} (index {j})")
                found = True
                break
        if found:
            break

    # --- Extract and Form the Polygon ---
    enclosed_polygon = None
    if found:
        loop_points_latlon = points_latlon[start_enclosed_index:found_index + 1]

        shapely_points = [(p[1], p[0]) for p in loop_points_latlon]

        if len(shapely_points) >= 3:
            potential_polygon = Polygon(shapely_points)
            if not potential_polygon.is_valid:
                print("WARNING: Created polygon is not valid. Attempting to make it valid with buffer(0).")
                potential_polygon = potential_polygon.buffer(0)

            if not potential_polygon.is_empty:
                if isinstance(potential_polygon, Polygon):
                    enclosed_polygon = potential_polygon
                    print(f"Polygon created successfully from near-closure. Vertices: {len(enclosed_polygon.exterior.coords)} total vertices.")
                elif isinstance(potential_polygon, MultiPolygon):
                    enclosed_polygon = potential_polygon
                    total_vertices = sum(len(p.exterior.coords) for p in enclosed_polygon.geoms)
                    print(f"Polygon created successfully from near-closure. Contains {len(enclosed_polygon.geoms)} polygons with {total_vertices} total vertices.")
        else:
            print(f"Not enough points ({len(shapely_points)}) to form a polygon.")
    else:
        print(f"No near-closure found within the {closure_tolerance_meters}m tolerance with check_step({check_step})")

    return enclosed_polygon, points_latlon


def plot_gpx_enclosed_polygons(gpx_file_path, closure_tolerance_meters=8, simplify_to_meters=8, check_step=8, output_image_path='distance_polygon_route_path.png'):
    """
    Reads a GPX file, simplifies the route, finds a closed loop based on a distance tolerance
    between points, and plots the original route and the found polygon.

    Args:
        gpx_file_path (str): The path to the GPX file.
        closure_tolerance_meters (float): The maximum distance between two points to consider them a closure.
        simplify_to_meters (float): The target distance between points after simplification, in meters.
        check_step (int): The minimum number of points to skip before checking for closure.
        output_image_path (str): Path to save the output plot image.
    """
    # Get the enclosed polygon(s) and simplified route
    enclosed_polygon, simplified_points_latlon = get_gpx_enclosed_polygons(gpx_file_path, closure_tolerance_meters, simplify_to_meters, check_step)

    # Re-read original GPX for plotting (original points are not simplified)
    with open(gpx_file_path, 'r') as gpx_file_handle:
        try:
            gpx = gpxpy.parse(gpx_file_handle)
        except Exception as e:
            print(f"Error reparsing GPX file for plotting: {e}")
            return

    original_points_latlon_for_plot = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                original_points_latlon_for_plot.append((point.latitude, point.longitude))

    if not original_points_latlon_for_plot:
        return

    # Extract lons/lats for plotting
    original_lons_for_plot = [p[1] for p in original_points_latlon_for_plot]
    original_lats_for_plot = [p[0] for p in original_points_latlon_for_plot]

    simplified_lons_for_plot = [p[1] for p in simplified_points_latlon]
    simplified_lats_for_plot = [p[0] for p in simplified_points_latlon]

    plt.figure(figsize=(12, 10))

    plt.plot(original_lons_for_plot, original_lats_for_plot, '-', linewidth=1, color='blue', label='GPX Route (Original)')
    plt.plot(simplified_lons_for_plot, simplified_lats_for_plot, '--', linewidth=1, color='green', label='GPX Route (Simplified)')

    if enclosed_polygon:
        if isinstance(enclosed_polygon, Polygon):
            x, y = enclosed_polygon.exterior.xy
            plt.fill(x, y, alpha=0.3, fc='yellow', label='Enclosed Polygon')
            plt.plot(x, y, 'r-', linewidth=2)
        elif isinstance(enclosed_polygon, MultiPolygon):
            for i, poly in enumerate(enclosed_polygon.geoms):
                x, y = poly.exterior.xy
                plt.fill(x, y, alpha=0.3, label=f'Enclosed Polygon ({i + 1})')
                plt.plot(x, y, 'r-', linewidth=2)

    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title(f"Route (Simplified to {simplify_to_meters}m) and Enclosed Polygon from {gpx_file_path} (Closure Tolerance {closure_tolerance_meters}m)")
    plt.legend()
    plt.grid(True)
    plt.savefig(output_image_path)
    plt.show()
    print(f"Plot saved to {output_image_path}")


def convert_gpx_to_h3_ids(gpx_file_path, h3_resolution=10, closure_tolerance_meters=8, simplify_to_meters=8, check_step=8):
    """
    Converts a GPX route into a list of H3 cell IDs by first simplifying the route,
    finding a closed loop, and converting the enclosed polygon to H3 IDs.

    Args:
        gpx_file_path (str): The path to the GPX file.
        h3_resolution (int): The H3 resolution (0-15) for the cells.
        closure_tolerance_meters (float): The maximum distance between two points to consider them a closure.
        simplify_to_meters (float): The target distance between points after simplification, in meters.
        check_step (int): The minimum number of points to skip before checking for closure.
    """
    enclosed_polygon, _ = get_gpx_enclosed_polygons(gpx_file_path, closure_tolerance_meters, simplify_to_meters, check_step)

    all_h3_ids = []

    if enclosed_polygon is None:
        print("No enclosed polygon found, so no H3 IDs to generate.")
        return all_h3_ids

    all_h3_ids = polygons_to_h3_ids(enclosed_polygon, h3_resolution)

    print(f"Total H3 IDs: {len(all_h3_ids)} (H3 resolution: {h3_resolution}) (covering the enclosed polygon)")

    return all_h3_ids

if __name__ == "__main__":
    h3_output_ids = convert_gpx_to_h3_ids(
        'Morning_Run.gpx',
        closure_tolerance_meters=10,
        simplify_to_meters=10, #Target 10m between points
        check_step=50,
        h3_resolution=10
    )
    if h3_output_ids:
        print(f"Sample H3 IDs:")
        for h3_id in h3_output_ids[:100]:
            print(h3_id)
        print(f"Total H3 IDs generated: {len(h3_output_ids)}")