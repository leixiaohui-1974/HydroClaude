import React from 'react';
import { Form, InputNumber, Select, Card, Space, Collapse, Button, Row, Col, Switch } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { SimulationConfig } from '@/services/simulations';

const { Option } = Select;

interface FormEditorProps {
  config: SimulationConfig;
  onChange: (config: SimulationConfig) => void;
}

/** Simulation types that use the open-channel canal parameter panel. */
const CHANNEL_TYPES = ['steady', 'unsteady', 'open_channel', 'water_quality', 'water_temperature', 'ice_simulation', 'coupled_ice_wq'];

const FormEditor: React.FC<FormEditorProps> = ({ config, onChange }) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();

  const handleValuesChange = (_: any, allValues: any) => {
    onChange(allValues as SimulationConfig);
  };

  const simType = Form.useWatch(['simulation', 'type'], form) ?? config?.simulation?.type ?? 'steady';
  const isChannelType = CHANNEL_TYPES.includes(simType);
  const isWaterHammer = simType === 'water_hammer';

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={config}
      onValuesChange={handleValuesChange}
      scrollToFirstError
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Simulation Settings */}
        <Card title={t('form.simulationSettings')} size="small">
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label={t('form.simulationType')}
                name={['simulation', 'type']}
                rules={[{ required: true, message: t('form.pleaseSelectSimulationType') }]}
              >
                <Select placeholder={t('form.selectSimulationType')}>
                  <Option value="steady">{t('form.steadyFlow')}</Option>
                  <Option value="unsteady">{t('form.unsteadyFlow')}</Option>
                  <Option value="open_channel">{t('form.openChannelFlow')}</Option>
                  <Option value="water_quality">{t('form.waterQuality')}</Option>
                  <Option value="water_temperature">{t('form.waterTemperature')}</Option>
                  <Option value="ice_simulation">{t('form.iceSimulation')}</Option>
                  <Option value="coupled_ice_wq">{t('form.coupledIceWq')}</Option>
                  <Option value="water_hammer">{t('form.waterHammer')}</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label={t('form.simulationMode')}
                name={['simulation', 'mode']}
                rules={[{ required: true, message: t('form.pleaseSelectSimulationMode') }]}
              >
                <Select placeholder={t('form.selectSimulationMode')}>
                  <Option value="single_canal">{t('form.singleCanal')}</Option>
                  <Option value="network">{t('form.canalNetwork')}</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} md={8}>
              <Form.Item label={t('form.simulationDuration')} name={['simulation', 'end_time']}>
                <InputNumber style={{ width: '100%' }} placeholder={t('form.enterSimulationDuration')} min={1} step={100} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label={t('form.timeStep')} name={['simulation', 'dt']}>
                <InputNumber style={{ width: '100%' }} placeholder={t('form.enterTimeStep')} min={0.001} step={1} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item label={t('form.numberOfCells')} name={['canal', 'n_cells']}>
                <InputNumber style={{ width: '100%' }} placeholder={t('form.enterNumberOfCells')} min={10} step={50} />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* Canal Parameters – shown for channel-type simulations */}
        {isChannelType && (
          <Card title={t('form.canalParameters')} size="small">
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  label={t('form.canalLength')}
                  name={['canal', 'length']}
                  rules={[
                    { required: true, message: t('form.pleaseEnterCanalLength') },
                    { type: 'number', min: 1, message: t('form.lengthMustBePositive') }
                  ]}
                >
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterCanalLength')} min={1} step={100} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  label={t('form.canalWidth')}
                  name={['canal', 'width']}
                  rules={[
                    { required: true, message: t('form.pleaseEnterCanalWidth') },
                    { type: 'number', min: 0.1, message: t('form.widthMustBePositive') }
                  ]}
                >
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterCanalWidth')} min={0.1} step={1} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item
                  label={t('form.canalSlope')}
                  name={['canal', 'slope']}
                  rules={[
                    { required: true, message: t('form.pleaseEnterCanalSlope') },
                    { type: 'number', min: 0.0001, message: t('form.slopeMustBePositive') }
                  ]}
                >
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterCanalSlope')} min={0.0001} step={0.0001} precision={4} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item
                  label={t('form.manningCoefficient')}
                  name={['canal', 'manning_n']}
                  rules={[
                    { required: true, message: t('form.pleaseEnterManningCoefficient') },
                    { type: 'number', min: 0.01, max: 0.1, message: t('form.manningRange') }
                  ]}
                >
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterManningCoefficient')} min={0.01} max={0.1} step={0.001} precision={3} />
                </Form.Item>
              </Col>
            </Row>
            {/* Depth & velocity for WQ / temperature / ice types */}
            {['water_quality', 'water_temperature', 'ice_simulation', 'coupled_ice_wq'].includes(simType) && (
              <Row gutter={16}>
                <Col xs={24} md={12}>
                  <Form.Item label={t('form.channelDepth')} name={['canal', 'depth']}>
                    <InputNumber style={{ width: '100%' }} placeholder={t('form.enterChannelDepth')} min={0.1} step={0.5} />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item label={t('form.channelVelocity')} name={['canal', 'velocity']}>
                    <InputNumber style={{ width: '100%' }} placeholder={t('form.enterChannelVelocity')} min={0} step={0.1} />
                  </Form.Item>
                </Col>
              </Row>
            )}
          </Card>
        )}

        {/* Water Quality Parameters */}
        {simType === 'water_quality' && (
          <Card title={t('form.waterQualityParams')} size="small">
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.initialConcentration')} name={['water_quality', 'initial_concentration']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterInitialConcentration')} min={0} step={1} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.decayRate')} name={['water_quality', 'decay_rate']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterDecayRate')} min={0} step={0.0001} precision={4} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.sourcePosition')} name={['water_quality', 'source_position']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterSourcePosition')} min={0} max={1} step={0.05} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.sourceRate')} name={['water_quality', 'source_rate']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterSourceRate')} min={0} step={0.01} />
                </Form.Item>
              </Col>
            </Row>
          </Card>
        )}

        {/* Water Temperature Parameters */}
        {simType === 'water_temperature' && (
          <Card title={t('form.temperatureParams')} size="small">
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.initialTemperature')} name={['temperature', 'initial_temperature']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterInitialTemperature')} step={1} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.airTemperature')} name={['temperature', 'air_temperature']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterAirTemperature')} step={1} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={8}>
                <Form.Item label={t('form.solarRadiation')} name={['temperature', 'solar_radiation']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterSolarRadiation')} min={0} step={50} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label={t('form.windSpeed')} name={['temperature', 'wind_speed']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterWindSpeed')} min={0} step={0.5} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label={t('form.relativeHumidity')} name={['temperature', 'relative_humidity']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterRelativeHumidity')} min={0} max={1} step={0.05} />
                </Form.Item>
              </Col>
            </Row>
          </Card>
        )}

        {/* Ice Simulation Parameters */}
        {simType === 'ice_simulation' && (
          <Card title={t('form.iceParams')} size="small">
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.iceWaterTemperature')} name={['ice', 'water_temperature']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterIceWaterTemperature')} step={0.5} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.iceAirTemperature')} name={['ice', 'air_temperature']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterIceAirTemperature')} step={1} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.initialIceThickness')} name={['ice', 'initial_ice_thickness']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterInitialIceThickness')} min={0} step={0.01} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.freezingTemperature')} name={['ice', 'T_freeze']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterFreezingTemperature')} step={0.1} />
                </Form.Item>
              </Col>
            </Row>
          </Card>
        )}

        {/* Coupled Ice + WQ Parameters */}
        {simType === 'coupled_ice_wq' && (
          <Card title={t('form.coupledParams')} size="small">
            <Row gutter={16}>
              <Col xs={24} md={6}>
                <Form.Item label={t('form.enableTemperature')} name={['coupled', 'enable_temperature']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label={t('form.enableDO')} name={['coupled', 'enable_do']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label={t('form.enableIce')} name={['coupled', 'enable_ice']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label={t('form.enableNutrients')} name={['coupled', 'enable_nutrients']} valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.initialTemperature')} name={['coupled', 'initial_temperature']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterInitialTemperature')} step={1} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.initialDO')} name={['coupled', 'initial_do']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterInitialDO')} min={0} step={1} />
                </Form.Item>
              </Col>
            </Row>
          </Card>
        )}

        {/* Water Hammer – Pipe Parameters */}
        {isWaterHammer && (
          <Card title={t('form.pipeParams')} size="small">
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.pipeLength')} name={['pipe', 'length']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterPipeLength')} min={1} step={100} />
                </Form.Item>
              </Col>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.pipeDiameter')} name={['pipe', 'diameter']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterPipeDiameter')} min={0.01} step={0.1} />
                </Form.Item>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col xs={24} md={8}>
                <Form.Item label={t('form.frictionFactor')} name={['pipe', 'friction_factor']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterFrictionFactor')} min={0.001} step={0.005} precision={3} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label={t('form.initialFlow')} name={['pipe', 'initial_flow']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterInitialFlow')} min={0} step={0.1} />
                </Form.Item>
              </Col>
              <Col xs={24} md={8}>
                <Form.Item label={t('form.upstreamHead')} name={['pipe', 'upstream_head']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterUpstreamHead')} min={0} step={10} />
                </Form.Item>
              </Col>
            </Row>
          </Card>
        )}

        {/* Valve Parameters (Water Hammer) */}
        {isWaterHammer && (
          <Card title={t('form.valveParams')} size="small">
            <Row gutter={16}>
              <Col xs={24} md={12}>
                <Form.Item label={t('form.closureTime')} name={['valve', 'closure_time']}>
                  <InputNumber style={{ width: '100%' }} placeholder={t('form.enterClosureTime')} min={0.01} step={0.5} />
                </Form.Item>
              </Col>
            </Row>
          </Card>
        )}

        {/* Solver Settings */}
        <Card title={t('form.solverSettings')} size="small">
          <Form.Item
            label={t('form.solverMethod')}
            name={['solver', 'method']}
            rules={[{ required: true, message: t('form.pleaseSelectSolverMethod') }]}
          >
            <Select placeholder={t('form.selectSolverMethod')}>
              <Option value="hydrostatic">{t('form.hydrostaticSolver')}</Option>
              <Option value="godunov">{t('form.godunovScheme')}</Option>
              <Option value="hllc">{t('form.solverHLLC')}</Option>
              <Option value="weno3">{t('form.solverWENO3')}</Option>
              <Option value="weno5">{t('form.solverWENO5')}</Option>
              <Option value="maccormack">{t('form.solverMacCormack')}</Option>
              <Option value="preissmann">{t('form.solverPreissmann')}</Option>
              <Option value="moc">{t('form.solverMoC')}</Option>
              <Option value="simple">{t('form.simpleSolver')}</Option>
            </Select>
          </Form.Item>
        </Card>

        {/* Boundary Conditions – only for channel types */}
        {isChannelType && (
          <Card title={t('form.boundaryConditions')} size="small">
            <Collapse
              defaultActiveKey={['upstream', 'downstream']}
              items={[
                {
                  key: 'upstream',
                  label: t('form.upstreamBoundary'),
                  children: (
                    <Row gutter={16}>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label={t('form.boundaryType')}
                          name={['boundary_conditions', 'upstream', 'type']}
                          rules={[{ required: true, message: t('form.pleaseSelectBoundaryType') }]}
                        >
                          <Select placeholder={t('form.selectBoundaryType')}>
                            <Option value="flow">{t('form.flowBoundary')}</Option>
                            <Option value="depth">{t('form.depthBoundary')}</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label={t('form.boundaryValue')}
                          name={['boundary_conditions', 'upstream', 'value']}
                          rules={[
                            { required: true, message: t('form.pleaseEnterBoundaryValue') },
                            { type: 'number', min: 0, message: t('form.boundaryValuePositive') }
                          ]}
                        >
                          <InputNumber style={{ width: '100%' }} placeholder={t('form.enterBoundaryValue')} min={0} step={0.1} />
                        </Form.Item>
                      </Col>
                    </Row>
                  ),
                },
                {
                  key: 'downstream',
                  label: t('form.downstreamBoundary'),
                  children: (
                    <Row gutter={16}>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label={t('form.boundaryType')}
                          name={['boundary_conditions', 'downstream', 'type']}
                          rules={[{ required: true, message: t('form.pleaseSelectBoundaryType') }]}
                        >
                          <Select placeholder={t('form.selectBoundaryType')}>
                            <Option value="depth">{t('form.depthBoundary')}</Option>
                            <Option value="flow">{t('form.flowBoundary')}</Option>
                            <Option value="rating_curve">{t('form.ratingCurve')}</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={12}>
                        <Form.Item
                          label={t('form.calculationMethod')}
                          name={['boundary_conditions', 'downstream', 'method']}
                        >
                          <Select placeholder={t('form.selectCalculationMethod')} allowClear>
                            <Option value="uniform_flow">{t('form.uniformFlow')}</Option>
                            <Option value="critical_depth">{t('form.criticalDepth')}</Option>
                            <Option value="specified">{t('form.specified')}</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                    </Row>
                  ),
                },
              ]}
            />
          </Card>
        )}

        {/* Hydraulic Structures (optional) */}
        {isChannelType && (
          <Card
            title={t('form.hydraulicStructures')}
            size="small"
            extra={<Button type="dashed" icon={<PlusOutlined />}>{t('form.addStructure')}</Button>}
          >
            <Form.List name="structures">
              {(fields, { add, remove }) => (
                <>
                  {fields.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                      {t('form.noStructures')}
                    </div>
                  )}
                  {fields.map((field, index) => (
                    <Card
                      key={field.key}
                      size="small"
                      type="inner"
                      title={t('form.structureIndex', { index: index + 1 })}
                      extra={
                        <Button
                          type="link"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(field.name)}
                        >
                          {t('common.delete')}
                        </Button>
                      }
                      style={{ marginBottom: 16 }}
                    >
                      <Row gutter={16}>
                        <Col xs={24} md={8}>
                          <Form.Item
                            {...field}
                            label={t('form.structureType')}
                            name={[field.name, 'type']}
                            rules={[{ required: true, message: t('form.pleaseSelectStructureType') }]}
                          >
                            <Select placeholder={t('form.selectStructureType')}>
                              <Option value="sluice_gate">{t('form.sluiceGate')}</Option>
                              <Option value="weir">{t('form.weir')}</Option>
                              <Option value="orifice">{t('form.orifice')}</Option>
                            </Select>
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item
                            {...field}
                            label={t('form.position')}
                            name={[field.name, 'position']}
                            rules={[{ required: true, message: t('form.pleaseEnterPosition') }]}
                          >
                            <InputNumber style={{ width: '100%' }} placeholder={t('form.enterPosition')} min={0} />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={8}>
                          <Form.Item
                            {...field}
                            label={t('form.widthM')}
                            name={[field.name, 'parameters', 'width']}
                          >
                            <InputNumber style={{ width: '100%' }} placeholder={t('form.enterWidth')} min={0.1} />
                          </Form.Item>
                        </Col>
                      </Row>
                    </Card>
                  ))}
                  <Button
                    type="dashed"
                    onClick={() => add()}
                    block
                    icon={<PlusOutlined />}
                  >
                    {t('form.addStructure')}
                  </Button>
                </>
              )}
            </Form.List>
          </Card>
        )}
      </Space>
    </Form>
  );
};

export default FormEditor;
