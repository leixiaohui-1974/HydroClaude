import React from 'react';
import { Descriptions, Card, Tag, Space, Divider, Empty } from 'antd';
import {
  CheckCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { SimulationConfig } from '@/services/simulations';

interface ConfigPreviewProps {
  config: SimulationConfig;
}

const ConfigPreview: React.FC<ConfigPreviewProps> = ({ config }) => {
  const { t } = useTranslation();

  if (!config) {
    return <Empty description={t('configPreview.noConfigData')} />;
  }

  // 计算一些派生信息
  const calculateInfo = () => {
    const { canal } = config;
    
    // 计算网格数（估算）
    const estimatedCells = Math.ceil(canal.length / 10);
    
    // 估算运行时间
    const estimatedTime = config.simulation.type === 'steady' ? t('configPreview.estimatedTimeSteady') : t('configPreview.estimatedTimeUnsteady');
    
    // 计算弗劳德数（简化）
    const avgDepth = 2.0; // 假设平均水深
    const avgVelocity = 1.5; // 假设平均流速
    const g = 9.81;
    const froudeNumber = avgVelocity / Math.sqrt(g * avgDepth);
    
    return {
      estimatedCells,
      estimatedTime,
      froudeNumber: froudeNumber.toFixed(3),
      flowRegime: froudeNumber < 1 ? t('configPreview.subcriticalFlow') : froudeNumber > 1 ? t('configPreview.supercriticalFlow') : t('configPreview.criticalFlow'),
    };
  };

  const info = calculateInfo();

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* 仿真设置预览 */}
      <Card title={t('configPreview.simulationSettings')} size="small">
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label={t('configPreview.simulationType')}>
            <Tag color={config.simulation.type === 'steady' ? 'blue' : 'purple'}>
              {config.simulation.type === 'steady' ? t('configPreview.steadyFlow') : t('configPreview.unsteadyFlow')}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.simulationMode')}>
            <Tag color="cyan">
              {config.simulation.mode === 'single_canal' ? t('configPreview.singleCanal') : t('configPreview.canalNetwork')}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.solverMethod')}>
            {config.solver.method}
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.estimatedRunTime')}>
            {info.estimatedTime}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 渠道参数预览 */}
      <Card title={t('configPreview.canalParameters')} size="small">
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label={t('configPreview.length')}>
            {config.canal.length} m
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.width')}>
            {config.canal.width} m
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.slope')}>
            {config.canal.slope}
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.manningCoeff')}>
            {config.canal.manning_n}
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.estimatedCells')}>
            {info.estimatedCells}
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.cellSize')}>
            ~{(config.canal.length / info.estimatedCells).toFixed(1)} m
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 边界条件预览 */}
      <Card title={t('configPreview.boundaryConditions')} size="small">
        <Descriptions bordered column={1} size="small">
          <Descriptions.Item label={t('configPreview.upstreamBoundary')}>
            <Space>
              <Tag color="blue">
                {config.boundary_conditions.upstream.type === 'flow' ? t('configPreview.flowBoundary') : t('configPreview.depthBoundary')}
              </Tag>
              <span>{t('configPreview.value')}: {config.boundary_conditions.upstream.value}</span>
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.downstreamBoundary')}>
            <Space>
              <Tag color="green">
                {config.boundary_conditions.downstream.type === 'depth' ? t('configPreview.depthBoundary') :
                 config.boundary_conditions.downstream.type === 'flow' ? t('configPreview.flowBoundary') : t('configPreview.ratingCurve')}
              </Tag>
              {config.boundary_conditions.downstream.method && (
                <span>{t('configPreview.method')}: {config.boundary_conditions.downstream.method}</span>
              )}
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 水工结构预览 */}
      {config.structures && config.structures.length > 0 && (
        <Card title={t('configPreview.hydraulicStructures')} size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            {config.structures.map((structure: any, index: number) => (
              <Card key={index} type="inner" size="small">
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label={t('configPreview.structureType')}>
                    <Tag color="orange">
                      {structure.type === 'sluice_gate' ? t('configPreview.sluiceGate') :
                       structure.type === 'weir' ? t('configPreview.weir') : t('configPreview.orifice')}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label={t('configPreview.position')}>
                    {structure.position} m
                  </Descriptions.Item>
                  {structure.parameters?.width && (
                    <Descriptions.Item label={t('configPreview.width')} span={2}>
                      {structure.parameters.width} m
                    </Descriptions.Item>
                  )}
                </Descriptions>
              </Card>
            ))}
          </Space>
        </Card>
      )}

      {/* 水力学分析预览 */}
      <Card title={t('configPreview.hydraulicAnalysis')} size="small">
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label={t('configPreview.estimatedFroude')}>
            {info.froudeNumber}
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.flowRegime')}>
            <Tag color={info.flowRegime === t('configPreview.subcriticalFlow') ? 'green' :
                        info.flowRegime === t('configPreview.supercriticalFlow') ? 'red' : 'orange'}>
              {info.flowRegime}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
        
        <Divider />
        
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            <span>{t('configPreview.configComplete')}</span>
          </div>
          {config.canal.slope < 0.0001 && (
            <div>
              <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
              <span>{t('configPreview.smallSlopeWarning')}</span>
            </div>
          )}
          {config.canal.manning_n < 0.015 && (
            <div>
              <InfoCircleOutlined style={{ color: '#1890ff', marginRight: 8 }} />
              <span>{t('configPreview.smallManningInfo')}</span>
            </div>
          )}
        </Space>
      </Card>
    </Space>
  );
};

export default ConfigPreview;
