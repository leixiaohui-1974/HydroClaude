/**
 * Enhanced drag & drop modeling component - covers all component types
 *
 * Features:
 * 1. More hydraulic structure types (bridge, culvert, drop, side weir, etc.)
 * 2. Network junctions and pipes
 * 3. Boundary condition settings
 * 4. Initial condition configuration
 * 5. Grid visualization
 * 6. Parameter validation
 * 7. Real-time preview
 */

import React, { useState, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Card, Button, InputNumber, Select, message, Space, Divider,
    Modal, Tabs, Form, Row, Col, Tag, Collapse
} from 'antd';
import {
    DeleteOutlined, EditOutlined,
    ExportOutlined, EyeOutlined, CheckCircleOutlined
} from '@ant-design/icons';

const { Option } = Select;

// Structure type key mapping for i18n
const STRUCTURE_TYPE_KEYS: Record<string, string> = {
    gate: 'gate',
    weir: 'weir',
    pump: 'pump',
    orifice: 'orifice',
    bridge: 'bridge',
    culvert: 'culvert',
    side_weir: 'sideWeir',
    drop: 'drop',
    junction: 'junction',
    reservoir: 'reservoir',
    valve: 'valve',
};

// Structure metadata (non-translatable parts)
const STRUCTURE_META = {
    GATE: { type: 'gate', icon: '\u{1F6AA}', color: '#1890ff', category: 'basic' },
    WEIR: { type: 'weir', icon: '\u26F0\uFE0F', color: '#52c41a', category: 'basic' },
    PUMP: { type: 'pump', icon: '\u{1F4A7}', color: '#722ed1', category: 'basic' },
    ORIFICE: { type: 'orifice', icon: '\u2B55', color: '#fa8c16', category: 'basic' },
    BRIDGE: { type: 'bridge', icon: '\u{1F309}', color: '#13c2c2', category: 'advanced' },
    CULVERT: { type: 'culvert', icon: '\u{1F532}', color: '#eb2f96', category: 'advanced' },
    SIDE_WEIR: { type: 'side_weir', icon: '\u2934\uFE0F', color: '#faad14', category: 'advanced' },
    DROP: { type: 'drop', icon: '\u2B07\uFE0F', color: '#2f54eb', category: 'advanced' },
    JUNCTION: { type: 'junction', icon: '\u26AB', color: '#595959', category: 'network' },
    RESERVOIR: { type: 'reservoir', icon: '\u{1F30A}', color: '#096dd9', category: 'network' },
    VALVE: { type: 'valve', icon: '\u{1F527}', color: '#d48806', category: 'network' },
};

interface StructureTypeInfo {
    type: string;
    label: string;
    icon: string;
    color: string;
    category: string;
}

// Build translated structure types
const getStructureTypes = (t: (key: string) => string): Record<string, StructureTypeInfo> => {
    const result: Record<string, StructureTypeInfo> = {};
    for (const [key, meta] of Object.entries(STRUCTURE_META)) {
        const i18nKey = STRUCTURE_TYPE_KEYS[meta.type] || meta.type;
        result[key] = {
            ...meta,
            label: t(`modelBuilder.${i18nKey}`),
        };
    }
    return result;
};

interface Structure {
    id: string;
    type: string;
    position: number;
    params: Record<string, any>;
    label: string;
    category: string;
}

interface BoundaryCondition {
    type: 'upstream' | 'downstream';
    condition: 'flow' | 'depth' | 'stage';
    value: number;
}

interface EnhancedCanalConfig {
    length: number;
    width: number;
    slope: number;
    roughness: number;
    nx: number;
    shape: 'rectangular' | 'trapezoidal' | 'circular';
    sideSlope?: number;
    diameter?: number;
}

const EnhancedDragModelBuilder: React.FC = () => {
    const { t } = useTranslation();

    const ALL_STRUCTURE_TYPES = getStructureTypes(t);

    const [canalConfig, setCanalConfig] = useState<EnhancedCanalConfig>({
        length: 10000,
        width: 10,
        slope: 0.001,
        roughness: 0.025,
        nx: 500,
        shape: 'rectangular',
    });

    const [flowConfig, setFlowConfig] = useState({
        flow_rate: 50,
        type: 'steady',
        time_step: 1.0,
        duration: 3600,
    });

    const [boundaryConditions, setBoundaryConditions] = useState<BoundaryCondition[]>([
        { type: 'upstream', condition: 'flow', value: 50 },
        { type: 'downstream', condition: 'depth', value: 5 },
    ]);

    const [structures, setStructures] = useState<Structure[]>([]);
    const [selectedStructure, setSelectedStructure] = useState<Structure | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [dragType, setDragType] = useState<string>('');
    const [showConfigModal, setShowConfigModal] = useState(false);
    const [showGridModal, setShowGridModal] = useState(false);
    const [activeCategory, setActiveCategory] = useState<string>('basic');

    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const drawCanal = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const canalHeight = 120;
        const canalY = canvas.height / 2 - canalHeight / 2;
        const canalWidth = canvas.width - 100;

        if (canalConfig.shape === 'rectangular') {
            ctx.fillStyle = '#e6f7ff';
            ctx.fillRect(50, canalY, canalWidth, canalHeight);
            ctx.strokeStyle = '#1890ff';
            ctx.lineWidth = 2;
            ctx.strokeRect(50, canalY, canalWidth, canalHeight);
        } else if (canalConfig.shape === 'trapezoidal') {
            ctx.fillStyle = '#e6f7ff';
            ctx.beginPath();
            ctx.moveTo(50, canalY + canalHeight);
            ctx.lineTo(70, canalY);
            ctx.lineTo(50 + canalWidth - 20, canalY);
            ctx.lineTo(50 + canalWidth, canalY + canalHeight);
            ctx.closePath();
            ctx.fill();
            ctx.strokeStyle = '#1890ff';
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Draw grid
        const gridSpacing = canalWidth / canalConfig.nx;
        ctx.strokeStyle = '#d9d9d9';
        ctx.lineWidth = 0.5;
        for (let i = 0; i <= canalConfig.nx; i += Math.floor(canalConfig.nx / 20)) {
            const x = 50 + i * gridSpacing;
            ctx.beginPath();
            ctx.moveTo(x, canalY);
            ctx.lineTo(x, canalY + canalHeight);
            ctx.stroke();
        }

        // Labels
        ctx.fillStyle = '#666';
        ctx.font = '12px Arial';
        ctx.fillText('0 m', 45, canalY + canalHeight + 20);
        ctx.fillText(`${canalConfig.length} m`, canvas.width - 95, canalY + canalHeight + 20);
        ctx.fillText(t('modelBuilderEnhanced.gridCount', { count: canalConfig.nx }), canvas.width / 2 - 30, canalY - 10);

        // Draw structures
        structures.forEach((structure) => {
            const posRatio = structure.position / canalConfig.length;
            const x = 50 + canalWidth * posRatio;
            const structureInfo = ALL_STRUCTURE_TYPES[structure.type.toUpperCase() as keyof typeof ALL_STRUCTURE_TYPES];

            if (structureInfo) {
                ctx.fillStyle = structureInfo.color;
                ctx.fillRect(x - 20, canalY + 10, 40, canalHeight - 20);
                ctx.strokeStyle = '#000';
                ctx.lineWidth = 2;
                ctx.strokeRect(x - 20, canalY + 10, 40, canalHeight - 20);

                ctx.font = '28px Arial';
                ctx.fillText(structureInfo.icon, x - 14, canalY + canalHeight / 2 + 10);

                ctx.font = '11px Arial';
                ctx.fillStyle = '#000';
                ctx.fillText(structure.label, x - 25, canalY + canalHeight + 35);
                ctx.fillText(`${structure.position.toFixed(0)}m`, x - 20, canalY + canalHeight + 47);

                ctx.font = '9px Arial';
                ctx.fillStyle = '#999';
                ctx.fillText(`[${structureInfo.category}]`, x - 22, canalY - 2);
            }

            if (selectedStructure?.id === structure.id) {
                ctx.strokeStyle = '#ff4d4f';
                ctx.lineWidth = 3;
                ctx.strokeRect(x - 23, canalY + 7, 46, canalHeight - 14);
            }
        });

        // Flow direction arrow
        ctx.fillStyle = '#1890ff';
        ctx.font = 'bold 16px Arial';
        ctx.fillText(t('modelBuilderEnhanced.flowDirectionArrow'), canvas.width / 2 - 30, canalY - 25);

    }, [canalConfig, structures, selectedStructure, t, ALL_STRUCTURE_TYPES]);

    React.useEffect(() => {
        drawCanal();
    }, [drawCanal]);

    React.useEffect(() => {
        const canvas = canvasRef.current;
        const container = containerRef.current;
        if (!canvas || !container) return;

        const resizeCanvas = () => {
            canvas.width = container.clientWidth;
            canvas.height = 350;
            drawCanal();
        };

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        return () => window.removeEventListener('resize', resizeCanvas);
    }, [drawCanal]);

    const handleDragStart = (type: string) => {
        setIsDragging(true);
        setDragType(type);
    };

    const handleDrop = (e: React.DragEvent<HTMLCanvasElement>) => {
        e.preventDefault();
        const canvas = canvasRef.current;
        if (!canvas || !isDragging) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const canvasWidth = canvas.width;

        const posRatio = Math.max(0, Math.min(1, (x - 50) / (canvasWidth - 100)));
        const position = posRatio * canalConfig.length;

        const structureKey = dragType.toUpperCase() as keyof typeof ALL_STRUCTURE_TYPES;
        const structureInfo = ALL_STRUCTURE_TYPES[structureKey];
        if (!structureInfo) return;

        const newStructure: Structure = {
            id: `${dragType}_${Date.now()}`,
            type: dragType,
            position: Math.round(position),
            label: `${structureInfo.label}${structures.filter(s => s.type === dragType).length + 1}`,
            category: structureInfo.category,
            params: getDefaultParams(dragType),
        };

        setStructures([...structures, newStructure]);
        setIsDragging(false);
        setDragType('');
        message.success(t('modelBuilder.structureAdded', { name: structureInfo.label }));
    };

    const getDefaultParams = (type: string): Record<string, any> => {
        const defaults: Record<string, any> = {
            gate: { width: canalConfig.width, opening: 5.0, discharge_coef: 0.6 },
            weir: { width: canalConfig.width, crest_height: 0.5, discharge_coef: 1.7 },
            pump: { flow_rate: 10.0, head: 5.0, efficiency: 0.85 },
            orifice: { diameter: 1.0, elevation: 0.0, discharge_coef: 0.61 },
            bridge: { width: canalConfig.width, clearance: 3.0, pier_count: 2 },
            culvert: { diameter: 2.0, length: 10.0, slope: 0.001 },
            side_weir: { length: 5.0, crest_height: 0.5, angle: 90 },
            drop: { height: 1.0, width: canalConfig.width },
            junction: { elevation: 0.0, diameter: 1.5 },
            reservoir: { area: 10000, max_depth: 10 },
            valve: { diameter: 1.0, opening: 100 },
        };
        return defaults[type] || {};
    };

    const handleDragOver = (e: React.DragEvent<HTMLCanvasElement>) => {
        e.preventDefault();
    };

    const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const canvasWidth = canvas.width;

        const clickedStructure = structures.find((structure) => {
            const posRatio = structure.position / canalConfig.length;
            const structureX = 50 + (canvasWidth - 100) * posRatio;
            return Math.abs(x - structureX) < 25;
        });

        setSelectedStructure(clickedStructure || null);
    };

    const handleDeleteStructure = () => {
        if (!selectedStructure) return;
        setStructures(structures.filter(s => s.id !== selectedStructure.id));
        setSelectedStructure(null);
        message.success(t('modelBuilder.structureDeleted'));
    };

    const handleEditStructure = () => {
        if (!selectedStructure) return;
        setShowConfigModal(true);
    };

    const handleUpdateStructure = (params: Record<string, any>) => {
        if (!selectedStructure) return;
        const updated = structures.map(s =>
            s.id === selectedStructure.id ? { ...s, params } : s
        );
        setStructures(updated);
        setSelectedStructure({ ...selectedStructure, params });
        setShowConfigModal(false);
        message.success(t('modelBuilder.paramsUpdated'));
    };

    const validateConfig = () => {
        const errors = [];

        if (canalConfig.length <= 0) errors.push(t('modelBuilderEnhanced.lengthError'));
        if (canalConfig.width <= 0) errors.push(t('modelBuilderEnhanced.widthError'));
        if (canalConfig.slope <= 0) errors.push(t('modelBuilderEnhanced.slopeError'));
        if (canalConfig.nx < 10) errors.push(t('modelBuilderEnhanced.gridMinError'));
        if (flowConfig.flow_rate <= 0) errors.push(t('modelBuilderEnhanced.flowRateError'));

        if (errors.length > 0) {
            message.error(errors.join('; '));
            return false;
        }

        message.success(t('modelBuilderEnhanced.configValidated'));
        return true;
    };

    const handleExportConfig = () => {
        if (!validateConfig()) return;

        const config = {
            name: 'enhanced_drag_model',
            description: t('modelBuilderEnhanced.exportDescription'),
            canal: canalConfig,
            flow: flowConfig,
            boundary_conditions: boundaryConditions,
            structures: structures.map(s => ({
                type: s.type,
                position: s.position,
                category: s.category,
                ...s.params,
            })),
            solver: {
                type: 'hydrostatic',
                max_iterations: 100,
                convergence_tol: 0.1,
            },
            metadata: {
                created_at: new Date().toISOString(),
                version: '2.0',
                structure_count: structures.length,
            }
        };

        const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `canal_model_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        message.success(t('modelBuilderEnhanced.configExported'));
    };

    const getStructuresByCategory = (category: string) => {
        return Object.values(ALL_STRUCTURE_TYPES).filter(s => s.category === category);
    };

    return (
        <div className="enhanced-drag-model-builder" style={{ padding: 20 }}>
            <Card title={`\u{1F3A8} ${t('modelBuilderEnhanced.title')}`} extra={
                <Space>
                    <Tag color="blue">{t('modelBuilderEnhanced.structureCountTag', { count: structures.length })}</Tag>
                    <Button icon={<CheckCircleOutlined />} onClick={validateConfig}>{t('modelBuilderEnhanced.validateConfig')}</Button>
                </Space>
            }>

                <Tabs
                    defaultActiveKey="canal"
                    items={[
                        {
                            key: 'canal',
                            label: t('modelBuilderEnhanced.canalConfig'),
                            children: (
                                <Form layout="vertical">
                                    <Row gutter={16}>
                                        <Col span={6}>
                                            <Form.Item label={t('modelBuilderEnhanced.canalShape')}>
                                                <Select
                                                    value={canalConfig.shape}
                                                    onChange={(val) => setCanalConfig({ ...canalConfig, shape: val })}
                                                >
                                                    <Option value="rectangular">{t('modelBuilderEnhanced.rectangular')}</Option>
                                                    <Option value="trapezoidal">{t('modelBuilderEnhanced.trapezoidal')}</Option>
                                                    <Option value="circular">{t('modelBuilderEnhanced.circular')}</Option>
                                                </Select>
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item label={t('modelBuilder.lengthM')}>
                                                <InputNumber
                                                    value={canalConfig.length}
                                                    onChange={(val) => setCanalConfig({ ...canalConfig, length: val || 10000 })}
                                                    min={100}
                                                    max={100000}
                                                    step={1000}
                                                    style={{ width: '100%' }}
                                                />
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item label={t('modelBuilder.widthM')}>
                                                <InputNumber
                                                    value={canalConfig.width}
                                                    onChange={(val) => setCanalConfig({ ...canalConfig, width: val || 10 })}
                                                    min={1}
                                                    max={100}
                                                    style={{ width: '100%' }}
                                                />
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item label={t('modelBuilder.slope')}>
                                                <InputNumber
                                                    value={canalConfig.slope}
                                                    onChange={(val) => setCanalConfig({ ...canalConfig, slope: val || 0.001 })}
                                                    min={0.0001}
                                                    max={0.1}
                                                    step={0.0001}
                                                    style={{ width: '100%' }}
                                                />
                                            </Form.Item>
                                        </Col>
                                    </Row>
                                    <Row gutter={16}>
                                        <Col span={6}>
                                            <Form.Item label={t('modelBuilder.roughness')}>
                                                <InputNumber
                                                    value={canalConfig.roughness}
                                                    onChange={(val) => setCanalConfig({ ...canalConfig, roughness: val || 0.025 })}
                                                    min={0.01}
                                                    max={0.1}
                                                    step={0.001}
                                                    style={{ width: '100%' }}
                                                />
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item label={t('modelBuilderEnhanced.gridNodes')}>
                                                <InputNumber
                                                    value={canalConfig.nx}
                                                    onChange={(val) => setCanalConfig({ ...canalConfig, nx: val || 500 })}
                                                    min={10}
                                                    max={10000}
                                                    step={10}
                                                    style={{ width: '100%' }}
                                                />
                                            </Form.Item>
                                        </Col>
                                    </Row>
                                </Form>
                            ),
                        },
                        {
                            key: 'flow',
                            label: t('modelBuilderEnhanced.flowConfig'),
                            children: (
                                <Form layout="vertical">
                                    <Row gutter={16}>
                                        <Col span={8}>
                                            <Form.Item label={t('modelBuilder.flowRateM3s')}>
                                                <InputNumber
                                                    value={flowConfig.flow_rate}
                                                    onChange={(val) => setFlowConfig({ ...flowConfig, flow_rate: val || 50 })}
                                                    min={0.1}
                                                    max={1000}
                                                    style={{ width: '100%' }}
                                                />
                                            </Form.Item>
                                        </Col>
                                        <Col span={8}>
                                            <Form.Item label={t('modelBuilderEnhanced.flowType')}>
                                                <Select
                                                    value={flowConfig.type}
                                                    onChange={(val) => setFlowConfig({ ...flowConfig, type: val })}
                                                >
                                                    <Option value="steady">{t('modelBuilder.steady')}</Option>
                                                    <Option value="unsteady">{t('modelBuilder.unsteady')}</Option>
                                                </Select>
                                            </Form.Item>
                                        </Col>
                                    </Row>
                                </Form>
                            ),
                        },
                        {
                            key: 'boundary',
                            label: t('modelBuilderEnhanced.boundaryConditions'),
                            children: (
                                <Collapse
                                    items={boundaryConditions.map((bc, idx) => ({
                                        key: String(idx),
                                        label: bc.type === 'upstream' ? t('modelBuilderEnhanced.upstreamBoundary') : t('modelBuilderEnhanced.downstreamBoundary'),
                                        children: (
                                            <Form layout="inline">
                                                <Form.Item label={t('modelBuilderEnhanced.conditionType')}>
                                                    <Select
                                                        value={bc.condition}
                                                        onChange={(val) => {
                                                            const updated = [...boundaryConditions];
                                                            updated[idx].condition = val;
                                                            setBoundaryConditions(updated);
                                                        }}
                                                        style={{ width: 120 }}
                                                    >
                                                        <Option value="flow">{t('modelBuilderEnhanced.flow')}</Option>
                                                        <Option value="depth">{t('modelBuilderEnhanced.depth')}</Option>
                                                        <Option value="stage">{t('modelBuilderEnhanced.stage')}</Option>
                                                    </Select>
                                                </Form.Item>
                                                <Form.Item label={t('modelBuilderEnhanced.value')}>
                                                    <InputNumber
                                                        value={bc.value}
                                                        onChange={(val) => {
                                                            const updated = [...boundaryConditions];
                                                            updated[idx].value = val || 0;
                                                            setBoundaryConditions(updated);
                                                        }}
                                                    />
                                                </Form.Item>
                                            </Form>
                                        ),
                                    }))}
                                />
                            ),
                        },
                    ]}
                />
            </Card>

            {/* Structure Toolbox */}
            <Card title={`\u{1F9F0} ${t('modelBuilderEnhanced.toolboxTitle', { count: 11 })}`} style={{ marginTop: 20 }}>
                <Tabs
                    activeKey={activeCategory}
                    onChange={setActiveCategory}
                    items={[
                        {
                            key: 'basic',
                            label: t('modelBuilderEnhanced.categoryBasic'),
                            children: (
                                <Space size="large" wrap>
                                    {getStructuresByCategory('basic').map((structure) => (
                                        <div
                                            key={structure.type}
                                            className="structure-tool"
                                            draggable
                                            onDragStart={() => handleDragStart(structure.type)}
                                            style={{
                                                padding: '12px 24px',
                                                border: `2px solid ${structure.color}`,
                                                borderRadius: '8px',
                                                cursor: 'grab',
                                                backgroundColor: '#fafafa',
                                                minWidth: '100px',
                                                textAlign: 'center',
                                            }}
                                        >
                                            <div style={{ fontSize: '28px' }}>{structure.icon}</div>
                                            <div style={{ fontSize: '13px', marginTop: 4 }}>{structure.label}</div>
                                        </div>
                                    ))}
                                </Space>
                            ),
                        },
                        {
                            key: 'advanced',
                            label: t('modelBuilderEnhanced.categoryAdvanced'),
                            children: (
                                <Space size="large" wrap>
                                    {getStructuresByCategory('advanced').map((structure) => (
                                        <div
                                            key={structure.type}
                                            className="structure-tool"
                                            draggable
                                            onDragStart={() => handleDragStart(structure.type)}
                                            style={{
                                                padding: '12px 24px',
                                                border: `2px solid ${structure.color}`,
                                                borderRadius: '8px',
                                                cursor: 'grab',
                                                backgroundColor: '#fafafa',
                                                minWidth: '100px',
                                                textAlign: 'center',
                                            }}
                                        >
                                            <div style={{ fontSize: '28px' }}>{structure.icon}</div>
                                            <div style={{ fontSize: '13px', marginTop: 4 }}>{structure.label}</div>
                                        </div>
                                    ))}
                                </Space>
                            ),
                        },
                        {
                            key: 'network',
                            label: t('modelBuilderEnhanced.categoryNetwork'),
                            children: (
                                <Space size="large" wrap>
                                    {getStructuresByCategory('network').map((structure) => (
                                        <div
                                            key={structure.type}
                                            className="structure-tool"
                                            draggable
                                            onDragStart={() => handleDragStart(structure.type)}
                                            style={{
                                                padding: '12px 24px',
                                                border: `2px solid ${structure.color}`,
                                                borderRadius: '8px',
                                                cursor: 'grab',
                                                backgroundColor: '#fafafa',
                                                minWidth: '100px',
                                                textAlign: 'center',
                                            }}
                                        >
                                            <div style={{ fontSize: '28px' }}>{structure.icon}</div>
                                            <div style={{ fontSize: '13px', marginTop: 4 }}>{structure.label}</div>
                                        </div>
                                    ))}
                                </Space>
                            ),
                        },
                    ]}
                />
                <div style={{ marginTop: 15, padding: '10px', background: '#f0f2f5', borderRadius: '4px' }}>
                    <Space>
                        <span style={{ color: '#666', fontSize: '13px' }}>
                            {`\u{1F4A1} ${t('modelBuilderEnhanced.dragTip')}`}
                        </span>
                        <Divider type="vertical" />
                        <span style={{ color: '#1890ff', fontSize: '13px' }}>
                            {t('modelBuilderEnhanced.supportedInfo', { structureCount: 11, shapeCount: 3 })}
                        </span>
                    </Space>
                </div>
            </Card>

            {/* Canal Canvas */}
            <Card
                title={`\u{1F3DE}\uFE0F ${t('modelBuilderEnhanced.visualizationTitle')}`}
                style={{ marginTop: 20 }}
                extra={
                    <Space>
                        {selectedStructure && (
                            <>
                                <Button
                                    type="primary"
                                    icon={<EditOutlined />}
                                    onClick={handleEditStructure}
                                    size="small"
                                >
                                    {t('modelBuilderEnhanced.editBtn')}
                                </Button>
                                <Button
                                    danger
                                    icon={<DeleteOutlined />}
                                    onClick={handleDeleteStructure}
                                    size="small"
                                >
                                    {t('modelBuilderEnhanced.deleteBtn')}
                                </Button>
                            </>
                        )}
                        <Button
                            type="default"
                            icon={<EyeOutlined />}
                            onClick={() => setShowGridModal(true)}
                        >
                            {t('modelBuilderEnhanced.gridPreview')}
                        </Button>
                        <Button
                            type="primary"
                            icon={<ExportOutlined />}
                            onClick={handleExportConfig}
                            disabled={structures.length === 0}
                        >
                            {t('modelBuilderEnhanced.exportConfig')}
                        </Button>
                    </Space>
                }
            >
                <div ref={containerRef} style={{ width: '100%', height: 350, position: 'relative' }}>
                    <canvas
                        ref={canvasRef}
                        onClick={handleCanvasClick}
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                        aria-label={t('modelBuilderEnhanced.visualizationTitle')}
                        role="img"
                        style={{
                            border: '2px solid #d9d9d9',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
                        }}
                    />
                </div>
                <div style={{ marginTop: 15, padding: '10px', background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: '4px' }}>
                    <Space split={<Divider type="vertical" />}>
                        <span>
                            {t('modelBuilderEnhanced.structuresAdded', { count: structures.length })}
                        </span>
                        {selectedStructure && (
                            <span style={{ color: '#1890ff' }}>
                                {t('modelBuilderEnhanced.selectedInfo', { name: selectedStructure.label, position: selectedStructure.position, category: selectedStructure.category })}
                            </span>
                        )}
                        <span>
                            {t('modelBuilderEnhanced.canalInfo', { shape: canalConfig.shape, length: canalConfig.length, width: canalConfig.width })}
                        </span>
                    </Space>
                </div>
            </Card>

            {/* Parameter Edit Modal */}
            <Modal
                title={t('modelBuilder.editStructure', { name: selectedStructure?.label })}
                open={showConfigModal}
                onCancel={() => setShowConfigModal(false)}
                onOk={() => {
                    if (selectedStructure) {
                        handleUpdateStructure(selectedStructure.params);
                    }
                }}
                width={600}
            >
                {selectedStructure && (
                    <Form layout="vertical">
                        {Object.entries(selectedStructure.params).map(([key, value]) => (
                            <Form.Item key={key} label={key}>
                                <InputNumber
                                    value={value as number}
                                    onChange={(val) => {
                                        setSelectedStructure({
                                            ...selectedStructure,
                                            params: { ...selectedStructure.params, [key]: val || 0 },
                                        });
                                    }}
                                    step={0.1}
                                    style={{ width: '100%' }}
                                />
                            </Form.Item>
                        ))}
                    </Form>
                )}
            </Modal>

            {/* Grid Preview Modal */}
            <Modal
                title={t('modelBuilderEnhanced.gridPreviewTitle')}
                open={showGridModal}
                onCancel={() => setShowGridModal(false)}
                footer={null}
                width={800}
            >
                <div style={{ padding: 20 }}>
                    <p><strong>{t('modelBuilderEnhanced.gridCount', { count: canalConfig.nx })}</strong></p>
                    <p><strong>{t('modelBuilderEnhanced.gridSpacing')}</strong> {(canalConfig.length / canalConfig.nx).toFixed(2)} m</p>
                    <p><strong>{t('modelBuilderEnhanced.timeStep')}</strong> {flowConfig.time_step} s {t('modelBuilderEnhanced.timeStepSuffix')}</p>
                    <div style={{ marginTop: 20, padding: 15, background: '#f0f2f5', borderRadius: 4 }}>
                        <p style={{ margin: 0, color: '#666' }}>
                            {`\u{1F4A1} ${t('modelBuilderEnhanced.gridTip')}`}
                        </p>
                    </div>
                </div>
            </Modal>
        </div>
    );
};

export default EnhancedDragModelBuilder;
