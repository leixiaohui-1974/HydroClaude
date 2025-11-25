# -*- coding: utf-8 -*-
"""
GIS水网空间数据集成案例

本案例展示如何使用HydroClaude的GIS集成功能处理水网空间数据

功能展示：
1. 创建水网GeoJSON数据
2. 空间数据的导入和导出
3. 空间分析（缓冲区、相交等）
4. 水网地图可视化

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
import sys
import os

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from integration.gis_adapter import (
    GISAdapter,
    create_water_network_geojson,
    GIS_AVAILABLE
)


def example_create_water_network():
    """示例1：创建水网GIS数据"""
    print("=" * 60)
    print("示例1：创建水网GIS数据")
    print("=" * 60)

    # 定义水网节点
    nodes = [
        {'id': 'N1', 'x': 120.0, 'y': 30.0, 'elevation': 100.0, 'type': 'reservoir'},
        {'id': 'N2', 'x': 120.1, 'y': 30.0, 'elevation': 95.0, 'type': 'junction'},
        {'id': 'N3', 'x': 120.2, 'y': 30.0, 'elevation': 90.0, 'type': 'junction'},
        {'id': 'N4', 'x': 120.3, 'y': 30.0, 'elevation': 85.0, 'type': 'junction'},
        {'id': 'N5', 'x': 120.4, 'y': 30.0, 'elevation': 80.0, 'type': 'outlet'},
        {'id': 'N6', 'x': 120.2, 'y': 30.1, 'elevation': 92.0, 'type': 'junction'},
    ]

    # 定义水网管道
    links = [
        {'id': 'L1', 'from': 'N1', 'to': 'N2', 'length': 1000, 'diameter': 1.0, 'roughness': 0.013},
        {'id': 'L2', 'from': 'N2', 'to': 'N3', 'length': 1000, 'diameter': 0.8, 'roughness': 0.013},
        {'id': 'L3', 'from': 'N3', 'to': 'N4', 'length': 1000, 'diameter': 0.8, 'roughness': 0.013},
        {'id': 'L4', 'from': 'N4', 'to': 'N5', 'length': 1000, 'diameter': 0.6, 'roughness': 0.013},
        {'id': 'L5', 'from': 'N2', 'to': 'N6', 'length': 500, 'diameter': 0.4, 'roughness': 0.013},
        {'id': 'L6', 'from': 'N6', 'to': 'N3', 'length': 500, 'diameter': 0.4, 'roughness': 0.013},
    ]

    print(f"\n水网配置:")
    print(f"  节点数量: {len(nodes)}")
    print(f"  管道数量: {len(links)}")

    # 创建GeoJSON文件
    output_file = 'water_network.geojson'

    if GIS_AVAILABLE:
        nodes_gdf, links_gdf = create_water_network_geojson(nodes, links, output_file)

        print(f"\n节点类型统计:")
        if 'type' in nodes_gdf.columns:
            print(nodes_gdf['type'].value_counts())

        print(f"\n管道长度统计:")
        if 'length' in links_gdf.columns:
            print(f"  总长度: {links_gdf['length'].sum():.1f}m")
            print(f"  平均长度: {links_gdf['length'].mean():.1f}m")
            print(f"  最长管道: {links_gdf['length'].max():.1f}m")

        return nodes_gdf, links_gdf
    else:
        print("\n错误: GIS库未安装")
        return None, None


def example_spatial_analysis():
    """示例2：空间分析"""
    print("\n" + "=" * 60)
    print("示例2：空间分析")
    print("=" * 60)

    if not GIS_AVAILABLE:
        print("错误: GIS库未安装")
        return

    # 创建GIS适配器
    adapter = GISAdapter(crs="EPSG:4326")

    # 加载之前创建的水网数据
    try:
        nodes_gdf = adapter.load_geojson('water_network_nodes.geojson', 'nodes')
        links_gdf = adapter.load_geojson('water_network_links.geojson', 'links')
    except Exception as e:
        print(f"警告: 无法加载水网数据: {e}")
        print("请先运行示例1创建水网数据")
        return

    # 1. 缓冲区分析
    print("\n执行缓冲区分析...")
    buffer_distance = 0.01  # 约1km
    adapter.buffer('nodes', buffer_distance, 'node_buffers')

    print(f"  缓冲距离: {buffer_distance}度")
    print(f"  缓冲区数量: {len(adapter.layers['node_buffers'])}")

    # 2. 获取边界
    bounds = adapter.get_bounds('nodes')
    print(f"\n水网边界:")
    print(f"  西经: {bounds[0]:.6f}")
    print(f"  南纬: {bounds[1]:.6f}")
    print(f"  东经: {bounds[2]:.6f}")
    print(f"  北纬: {bounds[3]:.6f}")

    # 3. 创建服务区域（多边形）
    service_areas = [
        [(120.0, 29.9), (120.5, 29.9), (120.5, 30.2), (120.0, 30.2), (120.0, 29.9)]
    ]
    service_properties = [{'name': 'Service Area 1', 'population': 50000}]

    adapter.create_polygon_layer('service_areas', service_areas, service_properties)

    print(f"\n服务区域已创建:")
    print(f"  面积: 约 {(bounds[2]-bounds[0]) * (bounds[3]-bounds[1]) * 111 * 111:.2f} km^2")

    return adapter


def example_visualization():
    """示例3：地图可视化"""
    print("\n" + "=" * 60)
    print("示例3：地图可视化")
    print("=" * 60)

    if not GIS_AVAILABLE:
        print("错误: GIS库未安装")
        return

    # 创建GIS适配器
    adapter = GISAdapter()

    try:
        # 加载数据
        adapter.load_geojson('water_network_nodes.geojson', 'nodes')
        adapter.load_geojson('water_network_links.geojson', 'links')

        # 可视化
        print("\n生成地图可视化...")
        adapter.visualize(['nodes', 'links'], figsize=(14, 10), save_path='water_network_map.png')

        print("地图已保存！")

    except Exception as e:
        print(f"可视化失败: {e}")


def example_complex_network():
    """示例4：创建复杂水网"""
    print("\n" + "=" * 60)
    print("示例4：创建复杂水网（环状管网）")
    print("=" * 60)

    if not GIS_AVAILABLE:
        print("错误: GIS库未安装")
        return

    # 创建环状管网
    # 中心点
    center_x, center_y = 120.0, 30.0
    radius = 0.05  # 约5km

    # 生成环形节点
    n_nodes = 12
    nodes = []
    for i in range(n_nodes):
        angle = 2 * np.pi * i / n_nodes
        x = center_x + radius * np.cos(angle)
        y = center_y + radius * np.sin(angle)

        nodes.append({
            'id': f'N{i+1}',
            'x': x,
            'y': y,
            'elevation': 100 - i * 2,
            'type': 'junction'
        })

    # 添加中心节点
    nodes.append({
        'id': 'CENTER',
        'x': center_x,
        'y': center_y,
        'elevation': 110,
        'type': 'reservoir'
    })

    # 创建环形管道
    links = []
    for i in range(n_nodes):
        # 环形连接
        next_i = (i + 1) % n_nodes
        links.append({
            'id': f'L_ring_{i+1}',
            'from': f'N{i+1}',
            'to': f'N{next_i+1}',
            'diameter': 0.6
        })

        # 径向连接
        links.append({
            'id': f'L_radial_{i+1}',
            'from': 'CENTER',
            'to': f'N{i+1}',
            'diameter': 0.8
        })

    print(f"\n复杂水网配置:")
    print(f"  节点数量: {len(nodes)}")
    print(f"  管道数量: {len(links)}")
    print(f"  网络类型: 环状+径向")

    # 创建GeoJSON
    if GIS_AVAILABLE:
        nodes_gdf, links_gdf = create_water_network_geojson(
            nodes, links, 'complex_network.geojson'
        )

        # 可视化
        adapter = GISAdapter()
        adapter.layers['nodes'] = nodes_gdf
        adapter.layers['links'] = links_gdf

        adapter.visualize(['nodes', 'links'], figsize=(12, 12),
                        save_path='complex_network_map.png')

        print("\n复杂水网地图已保存: complex_network_map.png")

        return adapter


def example_export_to_shapefile():
    """示例5：导出为Shapefile"""
    print("\n" + "=" * 60)
    print("示例5：导出为Shapefile")
    print("=" * 60)

    if not GIS_AVAILABLE:
        print("错误: GIS库未安装")
        return

    adapter = GISAdapter()

    try:
        # 加载数据
        adapter.load_geojson('water_network_nodes.geojson', 'nodes')
        adapter.load_geojson('water_network_links.geojson', 'links')

        # 导出为Shapefile
        print("\n导出为Shapefile...")
        adapter.save_shapefile('nodes', 'water_network_nodes.shp')
        adapter.save_shapefile('links', 'water_network_links.shp')

        print("\nShapefile导出完成！")
        print("可以在QGIS、ArcGIS等GIS软件中打开查看")

    except Exception as e:
        print(f"导出失败: {e}")


def main():
    """主函数"""
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║              GIS水网空间数据集成案例                          ║
    ╚════════════════════════════════════════════════════════════════╝

    本案例展示HydroClaude的GIS集成功能

    功能：
    1. 创建水网GeoJSON数据
    2. 空间分析（缓冲区、边界等）
    3. 地图可视化
    4. 导出Shapefile格式

    要求：
    - 安装geopandas: pip install geopandas shapely fiona
    """)

    if not GIS_AVAILABLE:
        print("\n" + "=" * 60)
        print("错误: GIS库未安装！")
        print("=" * 60)
        print("\n请先安装GIS依赖:")
        print("  pip install geopandas shapely fiona pyproj")
        print("\n或者使用conda:")
        print("  conda install -c conda-forge geopandas")
        return

    # 运行示例
    try:
        # 示例1：创建水网
        nodes_gdf, links_gdf = example_create_water_network()

        if nodes_gdf is not None:
            # 示例2：空间分析
            adapter = example_spatial_analysis()

            # 示例3：可视化
            example_visualization()

            # 示例4：复杂网络
            example_complex_network()

            # 示例5：导出Shapefile
            example_export_to_shapefile()

            print("\n" + "=" * 60)
            print("所有示例运行完成！")
            print("=" * 60)

            print("\n生成的文件:")
            print("- water_network_nodes.geojson")
            print("- water_network_links.geojson")
            print("- water_network_map.png")
            print("- complex_network_map.png")
            print("- water_network_nodes.shp")
            print("- water_network_links.shp")

            print("\n应用场景:")
            print("- 水网规划与设计")
            print("- 管网巡检路径规划")
            print("- 服务区域分析")
            print("- 与GIS平台集成")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
