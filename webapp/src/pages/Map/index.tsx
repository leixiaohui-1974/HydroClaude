import React, { useState } from 'react';
import { Layout, Tabs, Card, Space, Button, message } from 'antd';
import {
  EnvironmentOutlined,
  EditOutlined,
  EyeOutlined,
  SaveOutlined,
  FolderOpenOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import MapViewer from '@/components/MapViewer';
import CanalDrawTool from '@/components/CanalDrawTool';
import ResultsOverlay from '@/components/ResultsOverlay';
import type { LatLngExpression } from 'leaflet';

const { Content } = Layout;

const GEOJSON_STORAGE_KEY = 'hydroclaude_map_geojson';

/**
 * 地图页面
 *
 * 功能：
 * - 地图查看
 * - 渠道绘制
 * - 结果叠加
 */
const MapPage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('view');
  const [mapCenter] = useState<LatLngExpression>([39.9042, 116.4074]); // 北京
  const [mapZoom] = useState(13);
  const [geoJsonData, setGeoJsonData] = useState<any>(null);

  const handleSave = () => {
    if (geoJsonData) {
      localStorage.setItem(GEOJSON_STORAGE_KEY, JSON.stringify(geoJsonData));
      message.success(t('map.geoJsonSavedSuccess'));
    } else {
      message.warning(t('map.noGeoJsonToSave'));
    }
  };

  const handleLoad = () => {
    const saved = localStorage.getItem(GEOJSON_STORAGE_KEY);
    if (saved) {
      try {
        const data = JSON.parse(saved);
        setGeoJsonData(data);
        message.success(t('map.geoJsonLoadSuccess'));
      } catch {
        message.error(t('map.loadError'));
      }
    } else {
      message.info(t('map.noSavedGeoJson'));
    }
  };

  const tabItems = [
    {
      key: 'view',
      label: (
        <Space>
          <EyeOutlined />
          <span>{t('map.mapView')}</span>
        </Space>
      ),
      children: (
        <MapViewer
          center={mapCenter}
          zoom={mapZoom}
          height="calc(100vh - 230px)"
          showControls
          showBaseMapSelector
        />
      ),
    },
    {
      key: 'draw',
      label: (
        <Space>
          <EditOutlined />
          <span>{t('map.canalDraw')}</span>
        </Space>
      ),
      children: (
        <MapViewer
          center={mapCenter}
          zoom={mapZoom}
          height="calc(100vh - 230px)"
          showControls
          showBaseMapSelector
          defaultBaseMap="cartoLight"
        >
          <CanalDrawTool
            onSave={(data) => {
              setGeoJsonData(data);
              message.success(t('map.canalSavedToMemory'));
            }}
          />
        </MapViewer>
      ),
    },
    {
      key: 'overlay',
      label: (
        <Space>
          <EnvironmentOutlined />
          <span>{t('map.resultsOverlay')}</span>
        </Space>
      ),
      children: (
        <MapViewer
          center={mapCenter}
          zoom={mapZoom}
          height="calc(100vh - 230px)"
          showControls
          showBaseMapSelector
          defaultBaseMap="cartoLight"
        >
          <ResultsOverlay
            data={{
              coordinates: [
                [116.404, 39.915],
                [116.405, 39.916],
                [116.406, 39.917],
                [116.407, 39.918],
                [116.408, 39.919],
              ],
              depths: [3.0, 2.9, 2.8, 2.7, 2.6],
              velocities: [1.5, 1.6, 1.7, 1.8, 1.9],
              positions: [0, 150, 300, 450, 600],
              froudeNumbers: [0.85, 0.92, 0.99, 1.05, 1.12],
            }}
            showDepth
            showVelocity={false}
            showVelocityVectors={false}
          />
        </MapViewer>
      ),
    },
  ];

  return (
    <Layout style={{ height: 'calc(100vh - 64px)' }}>
      <Content style={{ padding: '24px', background: '#f0f2f5' }}>
        <Card
          title={
            <Space>
              <EnvironmentOutlined />
              <span>{t('map.mapTools')}</span>
            </Space>
          }
          extra={
            <Space>
              <Button icon={<FolderOpenOutlined />} onClick={handleLoad}>
                {t('map.loadGeojson')}
              </Button>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                {t('map.save')}
              </Button>
            </Space>
          }
          style={{ height: '100%' }}
          bodyStyle={{ padding: 0, height: 'calc(100% - 57px)' }}
        >
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            style={{ height: '100%' }}
            tabBarStyle={{ padding: '0 24px', margin: 0 }}
          />
        </Card>
      </Content>
    </Layout>
  );
};

export default MapPage;
