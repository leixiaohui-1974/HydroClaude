import React, { useState } from 'react';
import { Layout, Tabs, Card, Space, Button, message } from 'antd';
import {
  EnvironmentOutlined,
  EditOutlined,
  EyeOutlined,
  SaveOutlined,
  FolderOpenOutlined,
} from '@ant-design/icons';
import MapViewer from '@/components/MapViewer';
import CanalDrawTool from '@/components/CanalDrawTool';
import ResultsOverlay from '@/components/ResultsOverlay';
import type { LatLngExpression } from 'leaflet';

const { Content } = Layout;
const { TabPane } = Tabs;

/**
 * 地图页面
 * 
 * 功能：
 * - 地图查看
 * - 渠道绘制（待实现）
 * - 结果叠加（待实现）
 */
const MapPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('view');
  const [mapCenter] = useState<LatLngExpression>([39.9042, 116.4074]); // 北京
  const [mapZoom] = useState(13);

  const handleSave = () => {
    message.success('保存成功！');
  };

  const handleLoad = () => {
    message.info('加载GeoJSON...');
  };

  return (
    <Layout style={{ height: 'calc(100vh - 64px)' }}>
      <Content style={{ padding: '24px', background: '#f0f2f5' }}>
        <Card
          title={
            <Space>
              <EnvironmentOutlined />
              <span>地图工具</span>
            </Space>
          }
          extra={
            <Space>
              <Button icon={<FolderOpenOutlined />} onClick={handleLoad}>
                加载GeoJSON
              </Button>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleSave}>
                保存
              </Button>
            </Space>
          }
          style={{ height: '100%' }}
          bodyStyle={{ padding: 0, height: 'calc(100% - 57px)' }}
        >
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            style={{ height: '100%' }}
            tabBarStyle={{ padding: '0 24px', margin: 0 }}
          >
            {/* 地图查看 */}
            <TabPane
              tab={
                <Space>
                  <EyeOutlined />
                  <span>地图查看</span>
                </Space>
              }
              key="view"
              style={{ height: '100%' }}
            >
              <MapViewer
                center={mapCenter}
                zoom={mapZoom}
                height="calc(100vh - 230px)"
                showControls
                showBaseMapSelector
              />
            </TabPane>

            {/* 渠道绘制 */}
            <TabPane
              tab={
                <Space>
                  <EditOutlined />
                  <span>渠道绘制</span>
                </Space>
              }
              key="draw"
              style={{ height: '100%' }}
            >
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
                    console.log('保存的GeoJSON:', data);
                    message.success('渠道已保存！');
                  }}
                />
              </MapViewer>
            </TabPane>

            {/* 结果叠加 */}
            <TabPane
              tab={
                <Space>
                  <EnvironmentOutlined />
                  <span>结果叠加</span>
                </Space>
              }
              key="overlay"
              style={{ height: '100%' }}
            >
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
            </TabPane>
          </Tabs>
        </Card>
      </Content>
    </Layout>
  );
};

export default MapPage;
