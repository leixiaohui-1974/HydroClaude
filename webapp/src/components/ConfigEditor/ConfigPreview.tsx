import React from 'react';
import { Descriptions, Card, Tag, Space, Divider, Empty } from 'antd';
import { 
  CheckCircleOutlined, 
  WarningOutlined, 
  InfoCircleOutlined 
} from '@ant-design/icons';
import type { SimulationConfig } from '@/services/simulations';

interface ConfigPreviewProps {
  config: SimulationConfig;
}

const ConfigPreview: React.FC<ConfigPreviewProps> = ({ config }) => {
  if (!config) {
    return <Empty description="无配置数据" />;
  }

  // 计算一些派生信息
  const calculateInfo = () => {
    const { canal } = config;
    
    // 计算网格数（估算）
    const estimatedCells = Math.ceil(canal.length / 10);
    
    // 估算运行时间
    const estimatedTime = config.simulation.type === 'steady' ? '< 5秒' : '10-60秒';
    
    // 计算弗劳德数（简化）
    const avgDepth = 2.0; // 假设平均水深
    const avgVelocity = 1.5; // 假设平均流速
    const g = 9.81;
    const froudeNumber = avgVelocity / Math.sqrt(g * avgDepth);
    
    return {
      estimatedCells,
      estimatedTime,
      froudeNumber: froudeNumber.toFixed(3),
      flowRegime: froudeNumber < 1 ? '缓流' : froudeNumber > 1 ? '急流' : '临界流',
    };
  };

  const info = calculateInfo();

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {/* 仿真设置预览 */}
      <Card title="仿真设置" size="small">
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="仿真类型">
            <Tag color={config.simulation.type === 'steady' ? 'blue' : 'purple'}>
              {config.simulation.type === 'steady' ? '稳态流' : '非恒定流'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="仿真模式">
            <Tag color="cyan">
              {config.simulation.mode === 'single_canal' ? '单一渠道' : '渠道网络'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="求解方法">
            {config.solver.method}
          </Descriptions.Item>
          <Descriptions.Item label="预计运行时间">
            {info.estimatedTime}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 渠道参数预览 */}
      <Card title="渠道参数" size="small">
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="长度">
            {config.canal.length} m
          </Descriptions.Item>
          <Descriptions.Item label="宽度">
            {config.canal.width} m
          </Descriptions.Item>
          <Descriptions.Item label="坡度">
            {config.canal.slope}
          </Descriptions.Item>
          <Descriptions.Item label="Manning系数">
            {config.canal.manning_n}
          </Descriptions.Item>
          <Descriptions.Item label="预估网格数">
            {info.estimatedCells} 个
          </Descriptions.Item>
          <Descriptions.Item label="网格尺寸">
            约 {(config.canal.length / info.estimatedCells).toFixed(1)} m
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 边界条件预览 */}
      <Card title="边界条件" size="small">
        <Descriptions bordered column={1} size="small">
          <Descriptions.Item label="上游边界">
            <Space>
              <Tag color="blue">
                {config.boundary_conditions.upstream.type === 'flow' ? '流量边界' : '水深边界'}
              </Tag>
              <span>值: {config.boundary_conditions.upstream.value}</span>
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="下游边界">
            <Space>
              <Tag color="green">
                {config.boundary_conditions.downstream.type === 'depth' ? '水深边界' : 
                 config.boundary_conditions.downstream.type === 'flow' ? '流量边界' : '水位流量关系'}
              </Tag>
              {config.boundary_conditions.downstream.method && (
                <span>方法: {config.boundary_conditions.downstream.method}</span>
              )}
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 水工结构预览 */}
      {config.structures && config.structures.length > 0 && (
        <Card title="水工结构" size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            {config.structures.map((structure: any, index: number) => (
              <Card key={index} type="inner" size="small">
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="结构类型">
                    <Tag color="orange">
                      {structure.type === 'sluice_gate' ? '闸门' : 
                       structure.type === 'weir' ? '堰' : '孔板'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="位置">
                    {structure.position} m
                  </Descriptions.Item>
                  {structure.parameters?.width && (
                    <Descriptions.Item label="宽度" span={2}>
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
      <Card title="水力学分析预估" size="small">
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="预估Froude数">
            {info.froudeNumber}
          </Descriptions.Item>
          <Descriptions.Item label="流态">
            <Tag color={info.flowRegime === '缓流' ? 'green' : 
                        info.flowRegime === '急流' ? 'red' : 'orange'}>
              {info.flowRegime}
            </Tag>
          </Descriptions.Item>
        </Descriptions>
        
        <Divider />
        
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
            <span>配置基本参数完整</span>
          </div>
          {config.canal.slope < 0.0001 && (
            <div>
              <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
              <span>坡度较小，可能需要较长计算时间</span>
            </div>
          )}
          {config.canal.manning_n < 0.015 && (
            <div>
              <InfoCircleOutlined style={{ color: '#1890ff', marginRight: 8 }} />
              <span>Manning系数较小，表面较光滑</span>
            </div>
          )}
        </Space>
      </Card>
    </Space>
  );
};

export default ConfigPreview;
