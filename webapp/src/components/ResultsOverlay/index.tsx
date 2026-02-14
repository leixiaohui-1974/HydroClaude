import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Polyline, CircleMarker, Popup } from 'react-leaflet';
import { Card, Space, Switch, Slider, Select, Row, Col } from 'antd';
import type { Position } from 'geojson';
import { getColorString, generateLegendData, calculateColorRange, ColorMapType } from '@/utils/colorMaps';
import './index.css';

export interface ResultsOverlayData {
  coordinates: Position[];     // 渠道坐标
  depths: number[];            // 水深数组
  velocities: number[];        // 流速数组
  positions: number[];         // 距起点距离
  froudeNumbers?: number[];    // Froude数（可选）
}

interface ResultsOverlayProps {
  data: ResultsOverlayData;
  showDepth?: boolean;
  showVelocity?: boolean;
  showVelocityVectors?: boolean;
}

/**
 * 结果叠加组件
 * 
 * 功能：
 * - 水深颜色映射
 * - 流速矢量场
 * - 图例显示
 * - 透明度控制
 */
const ResultsOverlay: React.FC<ResultsOverlayProps> = ({
  data,
  showDepth: initialShowDepth = true,
  showVelocity: initialShowVelocity = false,
  showVelocityVectors: initialShowVectors = false,
}) => {
  const { t } = useTranslation();
  const [showDepth, setShowDepth] = useState(initialShowDepth);
  const [showVelocity, setShowVelocity] = useState(initialShowVelocity);
  const [showVectors, setShowVectors] = useState(initialShowVectors);
  const [opacity, setOpacity] = useState(0.8);
  const [depthColorMap, setDepthColorMap] = useState<ColorMapType>('depth');
  const [velocityColorMap, setVelocityColorMap] = useState<ColorMapType>('velocity');
  const [vectorDensity, setVectorDensity] = useState(10); // 每隔多少个点显示一个矢量

  // 计算颜色范围
  const depthRange = useMemo(
    () => calculateColorRange(data.depths),
    [data.depths]
  );
  
  const velocityRange = useMemo(
    () => calculateColorRange(data.velocities),
    [data.velocities]
  );

  // 生成水深颜色分段
  const depthSegments = useMemo(() => {
    const segments = [];
    for (let i = 0; i < data.coordinates.length - 1; i++) {
      const depth = data.depths[i];
      const color = getColorString(depth, depthRange.min, depthRange.max, depthColorMap);
      
      segments.push({
        positions: [data.coordinates[i], data.coordinates[i + 1]],
        color,
        depth,
        position: data.positions[i],
      });
    }
    return segments;
  }, [data, depthRange, depthColorMap]);

  // 生成流速颜色分段
  const velocitySegments = useMemo(() => {
    const segments = [];
    for (let i = 0; i < data.coordinates.length - 1; i++) {
      const velocity = data.velocities[i];
      const color = getColorString(velocity, velocityRange.min, velocityRange.max, velocityColorMap);
      
      segments.push({
        positions: [data.coordinates[i], data.coordinates[i + 1]],
        color,
        velocity,
        position: data.positions[i],
      });
    }
    return segments;
  }, [data, velocityRange, velocityColorMap]);

  // 生成流速矢量
  const velocityVectors = useMemo(() => {
    const vectors = [];
    for (let i = 0; i < data.coordinates.length; i += vectorDensity) {
      if (i >= data.coordinates.length - 1) continue;
      
      const velocity = data.velocities[i];
      const start = data.coordinates[i];
      const end = data.coordinates[i + 1];
      
      // 计算方向向量
      const dx = end[0] - start[0];
      const dy = end[1] - start[1];
      const length = Math.sqrt(dx * dx + dy * dy);
      
      if (length > 0) {
        // 归一化并缩放
        const scale = velocity * 0.0001; // 调整矢量长度
        const arrowEnd: Position = [
          start[0] + (dx / length) * scale,
          start[1] + (dy / length) * scale,
        ];
        
        const color = getColorString(velocity, velocityRange.min, velocityRange.max, velocityColorMap);
        
        vectors.push({
          start,
          end: arrowEnd,
          color,
          velocity,
        });
      }
    }
    return vectors;
  }, [data, velocityRange, velocityColorMap, vectorDensity]);

  // 水深图例
  const depthLegend = useMemo(
    () => generateLegendData(depthRange.min, depthRange.max, 10, depthColorMap),
    [depthRange, depthColorMap]
  );

  // 流速图例
  const velocityLegend = useMemo(
    () => generateLegendData(velocityRange.min, velocityRange.max, 10, velocityColorMap),
    [velocityRange, velocityColorMap]
  );

  return (
    <>
      {/* 控制面板 */}
      <Card
        className="results-overlay-controls"
        style={{
          position: 'absolute',
          top: 80,
          right: 20,
          zIndex: 1000,
          width: 280,
        }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 显示选项 */}
          <div>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Space>
                <Switch checked={showDepth} onChange={setShowDepth} />
                <span>{t('resultsOverlay.showDepth')}</span>
              </Space>
              <Space>
                <Switch checked={showVelocity} onChange={setShowVelocity} />
                <span>{t('resultsOverlay.showVelocity')}</span>
              </Space>
              <Space>
                <Switch checked={showVectors} onChange={setShowVectors} />
                <span>{t('resultsOverlay.showVectorField')}</span>
              </Space>
            </Space>
          </div>

          {/* 透明度 */}
          <div>
            <div style={{ marginBottom: 8 }}>{t('resultsOverlay.opacity')}: {(opacity * 100).toFixed(0)}%</div>
            <Slider
              value={opacity * 100}
              onChange={(v) => setOpacity(v / 100)}
              min={10}
              max={100}
            />
          </div>

          {/* 颜色方案 */}
          {showDepth && (
            <div>
              <div style={{ marginBottom: 8 }}>{t('resultsOverlay.depthColorScheme')}:</div>
              <Select
                value={depthColorMap}
                onChange={setDepthColorMap}
                style={{ width: '100%' }}
                options={[
                  { label: t('resultsOverlay.colorDepthBlueYellow'), value: 'depth' },
                  { label: 'Viridis', value: 'viridis' },
                  { label: 'Plasma', value: 'plasma' },
                  { label: 'CoolWarm', value: 'coolwarm' },
                ]}
              />
            </div>
          )}

          {showVelocity && (
            <div>
              <div style={{ marginBottom: 8 }}>{t('resultsOverlay.velocityColorScheme')}:</div>
              <Select
                value={velocityColorMap}
                onChange={setVelocityColorMap}
                style={{ width: '100%' }}
                options={[
                  { label: t('resultsOverlay.colorVelocityBlueRed'), value: 'velocity' },
                  { label: 'Viridis', value: 'viridis' },
                  { label: 'Plasma', value: 'plasma' },
                  { label: 'CoolWarm', value: 'coolwarm' },
                ]}
              />
            </div>
          )}

          {showVectors && (
            <div>
              <div style={{ marginBottom: 8 }}>{t('resultsOverlay.vectorDensity')}: {vectorDensity}</div>
              <Slider
                value={vectorDensity}
                onChange={setVectorDensity}
                min={1}
                max={50}
              />
            </div>
          )}
        </Space>
      </Card>

      {/* 水深图例 */}
      {showDepth && (
        <Card
          className="results-overlay-legend"
          title={t('resultsOverlay.depthLegendTitle')}
          style={{
            position: 'absolute',
            bottom: 60,
            right: 20,
            zIndex: 1000,
            width: 120,
          }}
          bodyStyle={{ padding: '8px' }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {depthLegend.map((item, i) => (
              <Row key={i} align="middle" gutter={8}>
                <Col span={8}>
                  <div
                    style={{
                      width: '100%',
                      height: '20px',
                      backgroundColor: item.color,
                      border: '1px solid #ddd',
                    }}
                  />
                </Col>
                <Col span={16}>
                  <span style={{ fontSize: '12px' }}>{item.label}</span>
                </Col>
              </Row>
            ))}
          </div>
        </Card>
      )}

      {/* 流速图例 */}
      {showVelocity && !showDepth && (
        <Card
          className="results-overlay-legend"
          title={t('resultsOverlay.velocityLegendTitle')}
          style={{
            position: 'absolute',
            bottom: 60,
            right: 20,
            zIndex: 1000,
            width: 120,
          }}
          bodyStyle={{ padding: '8px' }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {velocityLegend.map((item, i) => (
              <Row key={i} align="middle" gutter={8}>
                <Col span={8}>
                  <div
                    style={{
                      width: '100%',
                      height: '20px',
                      backgroundColor: item.color,
                      border: '1px solid #ddd',
                    }}
                  />
                </Col>
                <Col span={16}>
                  <span style={{ fontSize: '12px' }}>{item.label}</span>
                </Col>
              </Row>
            ))}
          </div>
        </Card>
      )}

      {/* 水深颜色叠加 */}
      {showDepth &&
        depthSegments.map((segment, i) => (
          <Polyline
            key={`depth-${i}`}
            positions={segment.positions as any}
            color={segment.color}
            weight={8}
            opacity={opacity}
          >
            <Popup>
              <div>
                <strong>{t('resultsOverlay.position')}:</strong> {segment.position.toFixed(1)} m<br />
                <strong>{t('resultsOverlay.depth')}:</strong> {segment.depth.toFixed(3)} m
              </div>
            </Popup>
          </Polyline>
        ))}

      {/* 流速颜色叠加 */}
      {showVelocity &&
        velocitySegments.map((segment, i) => (
          <Polyline
            key={`velocity-${i}`}
            positions={segment.positions as any}
            color={segment.color}
            weight={6}
            opacity={opacity}
          >
            <Popup>
              <div>
                <strong>{t('resultsOverlay.position')}:</strong> {segment.position.toFixed(1)} m<br />
                <strong>{t('resultsOverlay.velocity')}:</strong> {segment.velocity.toFixed(3)} m/s
              </div>
            </Popup>
          </Polyline>
        ))}

      {/* 流速矢量场 */}
      {showVectors &&
        velocityVectors.map((vector, i) => (
          <React.Fragment key={`vector-${i}`}>
            <Polyline
              positions={[vector.start, vector.end] as any}
              color={vector.color}
              weight={2}
              opacity={0.8}
            />
            <CircleMarker
              center={vector.end as any}
              radius={3}
              fillColor={vector.color}
              fillOpacity={0.8}
              stroke={false}
            >
              <Popup>
                <div>
                  <strong>{t('resultsOverlay.velocity')}:</strong> {vector.velocity.toFixed(3)} m/s
                </div>
              </Popup>
            </CircleMarker>
          </React.Fragment>
        ))}
    </>
  );
};

export default ResultsOverlay;
