"""
GIS数据适配器
"""
try:
    import geopandas as gpd
except ImportError:
    gpd = None
    print("Warning: geopandas not installed, GIS features disabled")

"""
GIS集成模块

本模块提供地理信息系统(GIS)数据的读写和可视化功能

支持格式：
- Shapefile (.shp)
- GeoJSON (.geojson, .json)
- GeoPackage (.gpkg)

主要功能：
- 水网空间数据的导入和导出
- 坐标系统转换
- 空间查询和分析
- 地图可视化

依赖安装：
pip install geopandas shapely fiona pyproj

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any, Union
from enum import Enum
import json

# GIS库可选导入
try:
    import geopandas as gpd
    from shapely.geometry import Point, LineString, Polygon, MultiLineString
    from shapely import geometry
    import fiona
    GIS_AVAILABLE = True
except ImportError:
    GIS_AVAILABLE = False
    print("警告: GIS库未安装。请使用 'pip install geopandas shapely fiona' 安装")


class GeometryType(Enum):
    """几何类型"""
    POINT = "Point"
    LINE = "LineString"
    POLYGON = "Polygon"
    MULTIPOINT = "MultiPoint"
    MULTILINE = "MultiLineString"
    MULTIPOLYGON = "MultiPolygon"


@dataclass
class SpatialFeature:
    """空间要素"""
    id: str
    geometry_type: GeometryType
    coordinates: Any  # 坐标数据
    properties: Dict[str, Any] = None  # 属性数据
    crs: str = "EPSG:4326"  # 坐标系统（默认WGS84）

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


class GISAdapter:
    """
    GIS适配器类

    提供HydroClaude与GIS数据的集成接口
    """

    def __init__(self, crs: str = "EPSG:4326"):
        """
        初始化GIS适配器

        参数：
            crs: 坐标参考系统（CRS），默认WGS84
        """
        if not GIS_AVAILABLE:
            raise ImportError("GIS库未安装，无法使用GIS功能")

        self.crs = crs
        self.layers: Dict[str, gpd.GeoDataFrame] = {}

    def load_shapefile(self, shapefile_path: str, layer_name: Optional[str] = None) -> gpd.GeoDataFrame:
        """
        加载Shapefile文件

        参数：
            shapefile_path: Shapefile文件路径
            layer_name: 图层名称（如果不指定，使用文件名）

        返回：
            GeoDataFrame对象
        """
        if layer_name is None:
            import os
            layer_name = os.path.splitext(os.path.basename(shapefile_path))[0]

        gdf = gpd.read_file(shapefile_path)

        # 转换坐标系统
        if gdf.crs is not None and str(gdf.crs) != self.crs:
            gdf = gdf.to_crs(self.crs)

        self.layers[layer_name] = gdf

        print(f"已加载Shapefile: {layer_name}")
        print(f"  要素数量: {len(gdf)}")
        print(f"  几何类型: {gdf.geometry.type.unique()}")
        print(f"  坐标系统: {gdf.crs}")

        return gdf

    def load_geojson(self, geojson_path: str, layer_name: Optional[str] = None) -> gpd.GeoDataFrame:
        """
        加载GeoJSON文件

        参数：
            geojson_path: GeoJSON文件路径
            layer_name: 图层名称

        返回：
            GeoDataFrame对象
        """
        if layer_name is None:
            import os
            layer_name = os.path.splitext(os.path.basename(geojson_path))[0]

        gdf = gpd.read_file(geojson_path)

        # 转换坐标系统
        if gdf.crs is not None and str(gdf.crs) != self.crs:
            gdf = gdf.to_crs(self.crs)

        self.layers[layer_name] = gdf

        print(f"已加载GeoJSON: {layer_name}")
        print(f"  要素数量: {len(gdf)}")
        print(f"  几何类型: {gdf.geometry.type.unique()}")

        return gdf

    def save_shapefile(self, layer_name: str, output_path: str):
        """
        保存图层为Shapefile

        参数：
            layer_name: 图层名称
            output_path: 输出文件路径
        """
        if layer_name not in self.layers:
            raise ValueError(f"图层 {layer_name} 不存在")

        gdf = self.layers[layer_name]
        gdf.to_file(output_path, driver='ESRI Shapefile')

        print(f"图层 {layer_name} 已保存到: {output_path}")

    def save_geojson(self, layer_name: str, output_path: str):
        """
        保存图层为GeoJSON

        参数：
            layer_name: 图层名称
            output_path: 输出文件路径
        """
        if layer_name not in self.layers:
            raise ValueError(f"图层 {layer_name} 不存在")

        gdf = self.layers[layer_name]
        gdf.to_file(output_path, driver='GeoJSON')

        print(f"图层 {layer_name} 已保存到: {output_path}")

    def create_point_layer(self, layer_name: str, points: List[Tuple[float, float]],
                          properties: Optional[List[Dict]] = None):
        """
        创建点图层

        参数：
            layer_name: 图层名称
            points: 点坐标列表 [(x, y), ...]
            properties: 属性列表
        """
        geometries = [Point(x, y) for x, y in points]

        if properties is None:
            properties = [{}] * len(points)

        gdf = gpd.GeoDataFrame(properties, geometry=geometries, crs=self.crs)
        self.layers[layer_name] = gdf

        print(f"已创建点图层: {layer_name}, 包含 {len(points)} 个点")

    def create_line_layer(self, layer_name: str, lines: List[List[Tuple[float, float]]],
                         properties: Optional[List[Dict]] = None):
        """
        创建线图层

        参数：
            layer_name: 图层名称
            lines: 线坐标列表 [[(x1, y1), (x2, y2), ...], ...]
            properties: 属性列表
        """
        geometries = [LineString(coords) for coords in lines]

        if properties is None:
            properties = [{}] * len(lines)

        gdf = gpd.GeoDataFrame(properties, geometry=geometries, crs=self.crs)
        self.layers[layer_name] = gdf

        print(f"已创建线图层: {layer_name}, 包含 {len(lines)} 条线")

    def create_polygon_layer(self, layer_name: str, polygons: List[List[Tuple[float, float]]],
                            properties: Optional[List[Dict]] = None):
        """
        创建面图层

        参数：
            layer_name: 图层名称
            polygons: 多边形坐标列表 [[(x1, y1), (x2, y2), ...], ...]
            properties: 属性列表
        """
        geometries = [Polygon(coords) for coords in polygons]

        if properties is None:
            properties = [{}] * len(polygons)

        gdf = gpd.GeoDataFrame(properties, geometry=geometries, crs=self.crs)
        self.layers[layer_name] = gdf

        print(f"已创建面图层: {layer_name}, 包含 {len(polygons)} 个多边形")

    def spatial_join(self, left_layer: str, right_layer: str, how: str = 'inner') -> gpd.GeoDataFrame:
        """
        空间连接

        参数：
            left_layer: 左侧图层名称
            right_layer: 右侧图层名称
            how: 连接方式 ('inner', 'left', 'right')

        返回：
            连接后的GeoDataFrame
        """
        if left_layer not in self.layers or right_layer not in self.layers:
            raise ValueError("指定的图层不存在")

        left_gdf = self.layers[left_layer]
        right_gdf = self.layers[right_layer]

        result = gpd.sjoin(left_gdf, right_gdf, how=how)

        return result

    def buffer(self, layer_name: str, distance: float, output_layer: str):
        """
        缓冲区分析

        参数：
            layer_name: 图层名称
            distance: 缓冲距离
            output_layer: 输出图层名称
        """
        if layer_name not in self.layers:
            raise ValueError(f"图层 {layer_name} 不存在")

        gdf = self.layers[layer_name]
        buffered = gdf.copy()
        buffered['geometry'] = gdf.geometry.buffer(distance)

        self.layers[output_layer] = buffered

        print(f"缓冲区分析完成: {output_layer}")

    def intersects(self, layer1: str, layer2: str) -> gpd.GeoDataFrame:
        """
        相交分析

        参数：
            layer1: 图层1名称
            layer2: 图层2名称

        返回：
            相交的要素
        """
        if layer1 not in self.layers or layer2 not in self.layers:
            raise ValueError("指定的图层不存在")

        gdf1 = self.layers[layer1]
        gdf2 = self.layers[layer2]

        # 找出相交的要素
        result = gdf1[gdf1.geometry.intersects(gdf2.unary_union)]

        return result

    def get_bounds(self, layer_name: str) -> Tuple[float, float, float, float]:
        """
        获取图层边界

        返回：
            (minx, miny, maxx, maxy)
        """
        if layer_name not in self.layers:
            raise ValueError(f"图层 {layer_name} 不存在")

        gdf = self.layers[layer_name]
        return gdf.total_bounds

    def visualize(self, layer_names: Optional[List[str]] = None, figsize=(12, 8),
                 save_path: Optional[str] = None):
        """
        可视化图层

        参数：
            layer_names: 要显示的图层名称列表（None表示全部）
            figsize: 图形大小
            save_path: 保存路径（None表示不保存）
        """
        import matplotlib.pyplot as plt

        if layer_names is None:
            layer_names = list(self.layers.keys())

        fig, ax = plt.subplots(figsize=figsize)

        colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']

        for i, layer_name in enumerate(layer_names):
            if layer_name in self.layers:
                gdf = self.layers[layer_name]
                color = colors[i % len(colors)]

                # 根据几何类型选择绘制参数
                geom_type = gdf.geometry.type.iloc[0] if len(gdf) > 0 else None

                if geom_type == 'Point':
                    gdf.plot(ax=ax, color=color, markersize=50, label=layer_name, alpha=0.6)
                elif geom_type in ['LineString', 'MultiLineString']:
                    gdf.plot(ax=ax, color=color, linewidth=2, label=layer_name, alpha=0.8)
                else:
                    gdf.plot(ax=ax, color=color, edgecolor='black', label=layer_name, alpha=0.5)

        ax.set_xlabel('Longitude', fontsize=12)
        ax.set_ylabel('Latitude', fontsize=12)
        ax.set_title('GIS Layers Visualization', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"可视化结果已保存到: {save_path}")

        return fig, ax


def create_water_network_geojson(nodes: List[Dict], links: List[Dict],
                                 output_file: str):
    """
    创建水网GeoJSON文件

    参数：
        nodes: 节点列表 [{'id': 'N1', 'x': 120.0, 'y': 30.0, 'elevation': 100}, ...]
        links: 管道列表 [{'id': 'L1', 'from': 'N1', 'to': 'N2'}, ...]
        output_file: 输出文件路径
    """
    if not GIS_AVAILABLE:
        raise ImportError("GIS库未安装")

    # 创建节点坐标字典
    node_coords = {node['id']: (node['x'], node['y']) for node in nodes}

    # 创建节点GeoDataFrame
    node_geometries = [Point(node['x'], node['y']) for node in nodes]
    node_properties = [{k: v for k, v in node.items() if k not in ['x', 'y']} for node in nodes]
    nodes_gdf = gpd.GeoDataFrame(node_properties, geometry=node_geometries, crs="EPSG:4326")

    # 创建管道GeoDataFrame
    link_geometries = []
    link_properties = []

    for link in links:
        from_node = link['from']
        to_node = link['to']

        if from_node in node_coords and to_node in node_coords:
            coords = [node_coords[from_node], node_coords[to_node]]
            link_geometries.append(LineString(coords))
            link_properties.append({k: v for k, v in link.items() if k not in ['from', 'to']})

    links_gdf = gpd.GeoDataFrame(link_properties, geometry=link_geometries, crs="EPSG:4326")

    # 保存为GeoJSON
    nodes_file = output_file.replace('.geojson', '_nodes.geojson')
    links_file = output_file.replace('.geojson', '_links.geojson')

    nodes_gdf.to_file(nodes_file, driver='GeoJSON')
    links_gdf.to_file(links_file, driver='GeoJSON')

    print(f"水网GeoJSON已创建:")
    print(f"  节点: {nodes_file}")
    print(f"  管道: {links_file}")

    return nodes_gdf, links_gdf


def hydroline_to_geojson(core_solver_result: Any, output_file: str):
    """
    将HydroClaude明渠求解器结果转换为GeoJSON

    参数：
        core_solver_result: 求解器结果对象
        output_file: 输出文件路径
    """
    if not GIS_AVAILABLE:
        raise ImportError("GIS库未安装")

    # 这是一个示例实现，实际需要根据求解器结构调整
    # 假设求解器有节点和单元信息

    features = []

    # 提取节点（假设有x坐标信息）
    if hasattr(core_solver_result, 'x') and hasattr(core_solver_result, 'h'):
        x = core_solver_result.x
        h = core_solver_result.h

        # 创建点要素
        for i in range(len(x)):
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [x[i], 0.0]  # 假设y=0
                },
                'properties': {
                    'id': i,
                    'x': float(x[i]),
                    'water_level': float(h[i]) if i < len(h) else 0.0
                }
            }
            features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    with open(output_file, 'w') as f:
        json.dump(geojson, f, indent=2)

    print(f"求解器结果已导出为GeoJSON: {output_file}")


# 导出
__all__ = [
    'GISAdapter',
    'GeometryType',
    'SpatialFeature',
    'create_water_network_geojson',
    'hydroline_to_geojson',
    'GIS_AVAILABLE',
]
