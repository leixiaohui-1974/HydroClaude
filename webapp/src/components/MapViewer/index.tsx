import React, { useState } from 'react';
import { MapContainer, TileLayer, ZoomControl, ScaleControl } from 'react-leaflet';
import { Card, Select, Space, Tag } from 'antd';
import type { LatLngExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './index.css';

// 修复Leaflet默认图标问题
import L from 'leaflet';
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

const DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

// 底图配置
export const BASE_MAPS = {
  osm: {
    name: 'OpenStreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  },
  osmHOT: {
    name: 'OpenStreetMap HOT',
    url: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors, Tiles courtesy of HOT',
  },
  cartoLight: {
    name: 'CartoDB Light',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CartoDB',
  },
  cartoDark: {
    name: 'CartoDB Dark',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CartoDB',
  },
  esriWorldImagery: {
    name: 'Esri World Imagery',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri',
  },
  esriWorldStreet: {
    name: 'Esri World Street',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri',
  },
};

export type BaseMapType = keyof typeof BASE_MAPS;

interface MapViewerProps {
  center?: LatLngExpression;
  zoom?: number;
  height?: string | number;
  defaultBaseMap?: BaseMapType;
  children?: React.ReactNode;
  showControls?: boolean;
  showBaseMapSelector?: boolean;
  onMapReady?: (map: L.Map) => void;
}

/**
 * 地图查看器组件
 * 
 * 功能：
 * - 基础地图显示
 * - 多种底图切换
 * - 缩放控件
 * - 比例尺显示
 * - 鼠标坐标显示
 */
const MapViewer: React.FC<MapViewerProps> = ({
  center = [39.9042, 116.4074], // 默认北京天安门
  zoom = 13,
  height = '600px',
  defaultBaseMap = 'osm',
  children,
  showControls = true,
  showBaseMapSelector = true,
  onMapReady,
}) => {
  const [baseMap, setBaseMap] = useState<BaseMapType>(defaultBaseMap);
  const [mousePosition, setMousePosition] = useState<{ lat: number; lng: number } | null>(null);
  const [mapZoom, setMapZoom] = useState(zoom);

  const handleMapCreated = (map: L.Map) => {
    // 监听鼠标移动
    map.on('mousemove', (e: L.LeafletMouseEvent) => {
      setMousePosition({
        lat: e.latlng.lat,
        lng: e.latlng.lng,
      });
    });

    // 监听缩放
    map.on('zoomend', () => {
      setMapZoom(map.getZoom());
    });

    // 回调
    onMapReady?.(map);
  };

  const currentBaseMap = BASE_MAPS[baseMap];

  return (
    <Card
      className="map-viewer-card"
      style={{ height: '100%' }}
      bodyStyle={{ padding: 0, height: '100%' }}
    >
      {/* 顶部控制栏 */}
      {showBaseMapSelector && (
        <div className="map-controls-bar">
          <Space>
            <span>底图:</span>
            <Select
              value={baseMap}
              onChange={setBaseMap}
              style={{ width: 200 }}
              options={Object.entries(BASE_MAPS).map(([key, value]) => ({
                label: value.name,
                value: key,
              }))}
            />
            <Tag color="blue">缩放级别: {mapZoom}</Tag>
          </Space>
        </div>
      )}

      {/* 地图容器 */}
      <div style={{ height: showBaseMapSelector ? 'calc(100% - 50px)' : '100%' }}>
        <MapContainer
          center={center}
          zoom={zoom}
          style={{ height: height, width: '100%' }}
          zoomControl={false}
          ref={(mapInstance: any) => {
            if (mapInstance) {
              handleMapCreated(mapInstance);
            }
          }}
        >
          {/* 底图层 */}
          <TileLayer
            url={currentBaseMap.url}
            attribution={currentBaseMap.attribution}
          />

          {/* 缩放控件 */}
          {showControls && <ZoomControl position="topright" />}

          {/* 比例尺 */}
          {showControls && <ScaleControl position="bottomleft" imperial={false} />}

          {/* 子组件 */}
          {children}
        </MapContainer>
      </div>

      {/* 底部坐标显示 */}
      {mousePosition && (
        <div className="map-coordinates">
          <Space>
            <span>纬度: {mousePosition.lat.toFixed(6)}</span>
            <span>经度: {mousePosition.lng.toFixed(6)}</span>
          </Space>
        </div>
      )}
    </Card>
  );
};

export default MapViewer;
