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

const SIM_TYPE_COLORS: Record<string, string> = {
  steady: 'blue',
  unsteady: 'purple',
  open_channel: 'geekblue',
  water_quality: 'green',
  water_temperature: 'orange',
  ice_simulation: 'cyan',
  coupled_ice_wq: 'magenta',
  water_hammer: 'red',
};

const SIM_TYPE_KEYS: Record<string, string> = {
  steady: 'form.steadyFlow',
  unsteady: 'form.unsteadyFlow',
  open_channel: 'form.openChannelFlow',
  water_quality: 'form.waterQuality',
  water_temperature: 'form.waterTemperature',
  ice_simulation: 'form.iceSimulation',
  coupled_ice_wq: 'form.coupledIceWq',
  water_hammer: 'form.waterHammer',
};

const CHANNEL_TYPES = ['steady', 'unsteady', 'open_channel', 'water_quality', 'water_temperature', 'ice_simulation', 'coupled_ice_wq'];

const ConfigPreview: React.FC<ConfigPreviewProps> = ({ config }) => {
  const { t } = useTranslation();

  if (!config) {
    return <Empty description={t('configPreview.noConfigData')} />;
  }

  const simType = config.simulation?.type ?? 'steady';
  const isChannelType = CHANNEL_TYPES.includes(simType);
  const isWaterHammer = simType === 'water_hammer';

  const calculateInfo = () => {
    const canal = config.canal ?? { length: 1000, width: 10, slope: 0.001, manning_n: 0.025 };
    const estimatedCells = config.canal?.n_cells ?? Math.ceil(canal.length / 10);
    const estimatedTime = ['steady', 'open_channel'].includes(simType)
      ? t('configPreview.estimatedTimeSteady')
      : t('configPreview.estimatedTimeUnsteady');

    const avgDepth = config.canal?.depth ?? 2.0;
    const avgVelocity = config.canal?.velocity ?? 1.5;
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
      {/* Simulation Settings */}
      <Card title={t('configPreview.simulationSettings')} size="small">
        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label={t('configPreview.simulationType')}>
            <Tag color={SIM_TYPE_COLORS[simType] ?? 'default'}>
              {t(SIM_TYPE_KEYS[simType] ?? 'form.steadyFlow')}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.simulationMode')}>
            <Tag color="cyan">
              {config.simulation?.mode === 'single_canal' ? t('configPreview.singleCanal') : t('configPreview.canalNetwork')}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.solverMethod')}>
            {config.solver?.method ?? '-'}
          </Descriptions.Item>
          <Descriptions.Item label={t('configPreview.estimatedRunTime')}>
            {info.estimatedTime}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Canal Parameters - channel types */}
      {isChannelType && (
        <Card title={t('configPreview.canalParameters')} size="small">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label={t('configPreview.length')}>
              {config.canal?.length ?? '-'} m
            </Descriptions.Item>
            <Descriptions.Item label={t('configPreview.width')}>
              {config.canal?.width ?? '-'} m
            </Descriptions.Item>
            <Descriptions.Item label={t('configPreview.slope')}>
              {config.canal?.slope ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('configPreview.manningCoeff')}>
              {config.canal?.manning_n ?? '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('configPreview.estimatedCells')}>
              {info.estimatedCells}
            </Descriptions.Item>
            <Descriptions.Item label={t('configPreview.cellSize')}>
              ~{((config.canal?.length ?? 1000) / info.estimatedCells).toFixed(1)} m
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* Water Quality Preview */}
      {simType === 'water_quality' && config.water_quality && (
        <Card title={t('form.waterQualityParams')} size="small">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label={t('form.initialConcentration')}>
              {config.water_quality.initial_concentration ?? 5} mg/L
            </Descriptions.Item>
            <Descriptions.Item label={t('form.decayRate')}>
              {config.water_quality.decay_rate ?? 0} 1/s
            </Descriptions.Item>
            <Descriptions.Item label={t('form.sourcePosition')}>
              {config.water_quality.source_position ?? 0.1}
            </Descriptions.Item>
            <Descriptions.Item label={t('form.sourceRate')}>
              {config.water_quality.source_rate ?? 0} mg/L/s
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* Temperature Preview */}
      {simType === 'water_temperature' && config.temperature && (
        <Card title={t('form.temperatureParams')} size="small">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label={t('form.initialTemperature')}>
              {config.temperature.initial_temperature ?? 15} °C
            </Descriptions.Item>
            <Descriptions.Item label={t('form.airTemperature')}>
              {config.temperature.air_temperature ?? 10} °C
            </Descriptions.Item>
            <Descriptions.Item label={t('form.solarRadiation')}>
              {config.temperature.solar_radiation ?? 200} W/m²
            </Descriptions.Item>
            <Descriptions.Item label={t('form.windSpeed')}>
              {config.temperature.wind_speed ?? 2} m/s
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* Ice Simulation Preview */}
      {simType === 'ice_simulation' && config.ice && (
        <Card title={t('form.iceParams')} size="small">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label={t('form.iceWaterTemperature')}>
              {config.ice.water_temperature ?? 0.5} °C
            </Descriptions.Item>
            <Descriptions.Item label={t('form.iceAirTemperature')}>
              {config.ice.air_temperature ?? -10} °C
            </Descriptions.Item>
            <Descriptions.Item label={t('form.initialIceThickness')}>
              {config.ice.initial_ice_thickness ?? 0} m
            </Descriptions.Item>
            <Descriptions.Item label={t('form.freezingTemperature')}>
              {config.ice.T_freeze ?? 0} °C
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* Coupled Preview */}
      {simType === 'coupled_ice_wq' && config.coupled && (
        <Card title={t('form.coupledParams')} size="small">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label={t('form.enableTemperature')}>
              <Tag color={config.coupled.enable_temperature ? 'green' : 'default'}>
                {config.coupled.enable_temperature ? t('common.yes') : t('common.no')}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('form.enableDO')}>
              <Tag color={config.coupled.enable_do ? 'green' : 'default'}>
                {config.coupled.enable_do ? t('common.yes') : t('common.no')}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('form.enableIce')}>
              <Tag color={config.coupled.enable_ice ? 'green' : 'default'}>
                {config.coupled.enable_ice ? t('common.yes') : t('common.no')}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('form.enableNutrients')}>
              <Tag color={config.coupled.enable_nutrients ? 'green' : 'default'}>
                {config.coupled.enable_nutrients ? t('common.yes') : t('common.no')}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* Water Hammer Preview */}
      {isWaterHammer && config.pipe && (
        <Card title={t('form.pipeParams')} size="small">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label={t('form.pipeLength')}>
              {config.pipe.length ?? 500} m
            </Descriptions.Item>
            <Descriptions.Item label={t('form.pipeDiameter')}>
              {config.pipe.diameter ?? 0.5} m
            </Descriptions.Item>
            <Descriptions.Item label={t('form.frictionFactor')}>
              {config.pipe.friction_factor ?? 0.02}
            </Descriptions.Item>
            <Descriptions.Item label={t('form.initialFlow')}>
              {config.pipe.initial_flow ?? 0.5} m³/s
            </Descriptions.Item>
            <Descriptions.Item label={t('form.upstreamHead')}>
              {config.pipe.upstream_head ?? 100} m
            </Descriptions.Item>
            {config.valve && (
              <Descriptions.Item label={t('form.closureTime')}>
                {config.valve.closure_time ?? 2} s
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}

      {/* Boundary Conditions - channel types */}
      {isChannelType && config.boundary_conditions && (
        <Card title={t('configPreview.boundaryConditions')} size="small">
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label={t('configPreview.upstreamBoundary')}>
              <Space>
                <Tag color="blue">
                  {config.boundary_conditions.upstream?.type === 'flow' ? t('configPreview.flowBoundary') : t('configPreview.depthBoundary')}
                </Tag>
                <span>{t('configPreview.value')}: {config.boundary_conditions.upstream?.value ?? '-'}</span>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label={t('configPreview.downstreamBoundary')}>
              <Space>
                <Tag color="green">
                  {config.boundary_conditions.downstream?.type === 'depth' ? t('configPreview.depthBoundary') :
                   config.boundary_conditions.downstream?.type === 'flow' ? t('configPreview.flowBoundary') : t('configPreview.ratingCurve')}
                </Tag>
                {config.boundary_conditions.downstream?.method && (
                  <span>{t('configPreview.method')}: {config.boundary_conditions.downstream.method}</span>
                )}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* Hydraulic Structures */}
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

      {/* Hydraulic Analysis - only for channel types */}
      {isChannelType && (
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
            {config.canal?.slope != null && config.canal.slope < 0.0001 && (
              <div>
                <WarningOutlined style={{ color: '#faad14', marginRight: 8 }} />
                <span>{t('configPreview.smallSlopeWarning')}</span>
              </div>
            )}
            {config.canal?.manning_n != null && config.canal.manning_n < 0.015 && (
              <div>
                <InfoCircleOutlined style={{ color: '#1890ff', marginRight: 8 }} />
                <span>{t('configPreview.smallManningInfo')}</span>
              </div>
            )}
          </Space>
        </Card>
      )}
    </Space>
  );
};

export default ConfigPreview;
