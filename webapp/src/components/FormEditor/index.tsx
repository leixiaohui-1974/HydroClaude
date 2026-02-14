import React from 'react';
import { Form, InputNumber, Select, Card, Space, Collapse, Button, Row, Col } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { SimulationConfig } from '@/services/simulations';

const { Option } = Select;

interface FormEditorProps {
  config: SimulationConfig;
  onChange: (config: SimulationConfig) => void;
}

const FormEditor: React.FC<FormEditorProps> = ({ config, onChange }) => {
  const { t } = useTranslation();
  const [form] = Form.useForm();

  // 表单值变化时更新配置
  const handleValuesChange = (_: any, allValues: any) => {
    onChange(allValues as SimulationConfig);
  };

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={config}
      onValuesChange={handleValuesChange}
      scrollToFirstError
    >
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 仿真设置 */}
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
        </Card>

        {/* 渠道参数 */}
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
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={t('form.enterCanalLength')}
                  min={1}
                  step={100}
                />
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
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={t('form.enterCanalWidth')}
                  min={0.1}
                  step={1}
                />
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
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={t('form.enterCanalSlope')}
                  min={0.0001}
                  step={0.0001}
                  precision={4}
                />
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
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={t('form.enterManningCoefficient')}
                  min={0.01}
                  max={0.1}
                  step={0.001}
                  precision={3}
                />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 求解器设置 */}
        <Card title={t('form.solverSettings')} size="small">
          <Form.Item
            label={t('form.solverMethod')}
            name={['solver', 'method']}
            rules={[{ required: true, message: t('form.pleaseSelectSolverMethod') }]}
          >
            <Select placeholder={t('form.selectSolverMethod')}>
              <Option value="hydrostatic">{t('form.hydrostaticSolver')}</Option>
              <Option value="godunov">{t('form.godunovScheme')}</Option>
              <Option value="simple">{t('form.simpleSolver')}</Option>
            </Select>
          </Form.Item>
        </Card>

        {/* 边界条件 */}
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
                        <InputNumber
                          style={{ width: '100%' }}
                          placeholder={t('form.enterBoundaryValue')}
                          min={0}
                          step={0.1}
                        />
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

        {/* 水工结构（可选） */}
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
                          <InputNumber
                            style={{ width: '100%' }}
                            placeholder={t('form.enterPosition')}
                            min={0}
                          />
                        </Form.Item>
                      </Col>
                      <Col xs={24} md={8}>
                        <Form.Item
                          {...field}
                          label={t('form.widthM')}
                          name={[field.name, 'parameters', 'width']}
                        >
                          <InputNumber
                            style={{ width: '100%' }}
                            placeholder={t('form.enterWidth')}
                            min={0.1}
                          />
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
      </Space>
    </Form>
  );
};

export default FormEditor;
