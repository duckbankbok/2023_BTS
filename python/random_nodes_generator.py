import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

hjd = gpd.read_file('data/ulsan/ULSAN_HJD.shp', encoding='utf-8')

## code reference : https://www.matecdev.com/posts/random-points-in-polygon.html
def Random_Points_in_Polygon(polygon, number):
    points = []
    minx, miny, maxx, maxy = polygon.bounds
    while len(points) < number:
        pnt = Point(np.random.uniform(minx, maxx), np.random.uniform(miny, maxy))
        if polygon.contains(pnt):
            points.append(pnt)
    return points

def generate_random_customers():
    demands = []
    total_points = []
    for idx in range(len(hjd)):
        polygon = hjd.iloc[idx].geometry
        number = np.random.randint(10, 101)
        points = Random_Points_in_Polygon(polygon, number)
        demands += list(np.random.randint(1, 21, size=number))
        total_points += points
    data = {'demand': demands}
    gdf = gpd.GeoDataFrame(data, geometry=total_points)
    return gdf

def save_customer_nodes(gdf):
    gdf.to_file('data/customer/customer.shp', driver='ESRI Shapefile')