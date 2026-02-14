import React, { useState } from 'react';
import { Layout, Tabs, Card, Space, Button, message } from 'antd';
import {
  EnvironmentOutlined,
  EditOutlined,
  EyeOutlined,
  SaveOutlined,
  FolderOpenOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import MapViewer from '@/components/MapViewer';
import CanalDrawTool from '@/components/CanalDrawTool';
import ResultsOverlay from '@/components/ResultsOverlay';
import type { LatLngExpression } from 'leaflet';

const { Content } = Layout;

const GEOJSON_STORAGE_KEY = 'hydroclaude_map_geojson';

const MapPage: React.FC = () => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('view');
  // Neutral world center so map is not biased to any region
  const [mapCenter] = useState<LatLngExpression>([30.0, 0.0]);
  const [mapZoom] = useState(3);
  const [geoJsonData, setGeoJsonData] = useState<any>(null);

  const handleSave = () => {
    if (geoJsonData) {
      localStorage.setItem(GEOJSON_STORAGE_KEY, JSON.stringify(geoJsonData));
      message.success(t('map.geoJsonSavedSuccess'));
    } else {
      message.warning(t('map.noGeoJsonToSave'));
    }
  };

  const handleDownload = () => {
    if (!geoJsonData) {
      message.warning(t('map.noGeoJsonToSave'));
      return;
    }
    const blob = new Blob([JSON.stringify(geoJsonData, null, 2)], { type: 'application/geo+json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'hydroclaude_canal.geojson';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    message.success(t('map.downloadSuccess', 'GeoJSON downloaded'));
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
          {geoJsonData ? (
            <ResultsOverlay
              data={{
                coordinates: geoJsonData.features?.[0]?.geometry?.coordinates?.map(
                  (c: number[]) => [c[0], c[1]] as [number, number]
                ) || [],
                depths: [],
                velocities: [],
                positions: [],
              }}
              showDepth
              showVelocity={false}
              showVelocityVectors={false}
            />
          ) : null}
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
              <Button icon={<DownloadOutlined />} onClick={handleDownload}>
                {t('map.downloadGeoJson', 'Download GeoJSON')}
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
