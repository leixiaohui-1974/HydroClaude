# 🚀 HydroClaude Web 功能扩展计划

## 📊 现状分析

### 当前Web功能（v1.0）

**模板数量**: 6个基础模板
```
✅ Dam Break（溃坝）
✅ Reservoir（水库）
✅ Channel Flow（渠道流动）
✅ River Flood（河流洪水）
✅ Urban Drainage（城市排水）
✅ Complex River System（复杂河流）
```

**组件类型**: 基础组件
```
✅ Canal/Channel（渠道）
✅ Basic Structures（基础结构：闸门、堰、泵站）
✅ Boundaries（边界条件）
```

**功能范围**: 基础明渠流动仿真

---

## 🎯 扩展目标（v2.0）

### 目标1: 模板库扩展

**从6个→20个模板，覆盖所有主要测试案例**

### 目标2: 组件库扩展

**从3-4种→11种水工结构**

### 目标3: 高级功能

**添加控制系统、水质模拟、参数优化**

---

## 📋 详细扩展计划

### 阶段1: 模板库扩展（新增14个模板）

#### 1.1 溃坝专题（3个新模板）

```typescript
// template_dam_break_advanced.ts
export const DAM_BREAK_DRY_BED_TEMPLATE = {
  metadata: {
    id: 'dam-break-dry-bed',
    name: 'Dam Break - Dry Bed (Ritter Solution)',
    nameCN: '溃坝 - 干河床（Ritter解析解）',
    category: 'dam-break',
    difficulty: 'intermediate',
    tags: ['dam-break', 'dry-bed', 'riemann', 'analytical'],
    references: ['Ritter (1892)', 'Toro (2001)', 'LeVeque (2002)']
  },
  config: {
    // 左侧10m，右侧干床
    domainLength: 2000,
    duration: 60,
    initialConditions: {
      left_h: 10.0,
      right_h: 0.01  // 近似干床
    }
  },
  learningObjectives: [
    {
      objective: 'Understand Riemann problem and shock wave formation',
      objectiveCN: '理解Riemann问题和激波形成'
    },
    {
      objective: 'Learn about dry bed handling in numerical schemes',
      objectiveCN: '学习数值格式中的干床处理'
    }
  ]
};

export const DAM_BREAK_PARTIAL_TEMPLATE = {
  metadata: {
    id: 'dam-break-partial',
    name: 'Dam Break - Partial Dam Break',
    nameCN: '溃坝 - 部分溃坝',
    category: 'dam-break',
    difficulty: 'advanced',
    tags: ['dam-break', 'partial', 'gate-failure']
  },
  // 模拟闸门部分失效场景
};

export const DAM_BREAK_CASCADE_TEMPLATE = {
  metadata: {
    id: 'dam-break-cascade',
    name: 'Dam Break - Cascade Failure',
    nameCN: '溃坝 - 梯级溃坝',
    category: 'dam-break',
    difficulty: 'advanced',
    tags: ['dam-break', 'cascade', 'multiple-dams']
  },
  // 多个大坝连续失效
};
```

#### 1.2 有压管道专题（3个新模板）

```typescript
// template_pressurized.ts
export const PRESSURE_PIPE_WATER_HAMMER_TEMPLATE = {
  metadata: {
    id: 'pressure-water-hammer',
    name: 'Pressurized Flow - Water Hammer',
    nameCN: '有压流 - 水锤',
    category: 'pressurized',
    difficulty: 'intermediate',
    tags: ['pressurized', 'water-hammer', 'transient']
  },
  config: {
    pipeLength: 1000,
    diameter: 0.5,
    initialVelocity: 2.0,
    valveClosureTime: 2.0
  },
  learningObjectives: [
    {
      objective: 'Understand water hammer phenomenon in pipelines',
      objectiveCN: '理解管道中的水锤现象'
    },
    {
      objective: 'Learn about pressure surge protection',
      objectiveCN: '学习压力激增保护'
    }
  ]
};

export const PRESSURE_PIPE_VALVE_OPERATION_TEMPLATE = {
  metadata: {
    id: 'pressure-valve-operation',
    name: 'Pressurized Flow - Valve Operation',
    nameCN: '有压流 - 阀门操作',
    category: 'pressurized',
    difficulty: 'intermediate',
    tags: ['pressurized', 'valve', 'control']
  }
};

export const PRESSURE_PIPE_NETWORK_TEMPLATE = {
  metadata: {
    id: 'pressure-network',
    name: 'Pressurized Network - Hardy-Cross',
    nameCN: '有压管网 - Hardy-Cross',
    category: 'pressurized',
    difficulty: 'advanced',
    tags: ['pressurized', 'network', 'hardy-cross']
  }
};
```

#### 1.3 水工结构专题（4个新模板）

```typescript
// template_structures.ts
export const MULTIPLE_GATES_TEMPLATE = {
  metadata: {
    id: 'multiple-gates-control',
    name: 'Multiple Gates - Coordinated Control',
    nameCN: '多闸门 - 协同控制',
    category: 'structures',
    difficulty: 'advanced',
    tags: ['gates', 'control', 'coordination']
  }
};

export const PUMP_STATION_TEMPLATE = {
  metadata: {
    id: 'pump-station-operation',
    name: 'Pump Station - Operation Optimization',
    nameCN: '泵站 - 运行优化',
    category: 'structures',
    difficulty: 'intermediate',
    tags: ['pump', 'optimization', 'energy']
  }
};

export const BRIDGE_HYDRAULICS_TEMPLATE = {
  metadata: {
    id: 'bridge-hydraulics',
    name: 'Bridge Hydraulics - Flow Constriction',
    nameCN: '桥梁水力学 - 流量收缩',
    category: 'structures',
    difficulty: 'intermediate',
    tags: ['bridge', 'constriction', 'backwater']
  }
};

export const CULVERT_DESIGN_TEMPLATE = {
  metadata: {
    id: 'culvert-design',
    name: 'Culvert Design - Capacity Analysis',
    nameCN: '涵洞设计 - 容量分析',
    category: 'structures',
    difficulty: 'intermediate',
    tags: ['culvert', 'design', 'capacity']
  }
};
```

#### 1.4 控制系统专题（2个新模板）

```typescript
// template_control.ts
export const PID_WATER_LEVEL_CONTROL_TEMPLATE = {
  metadata: {
    id: 'pid-water-level',
    name: 'PID Control - Water Level Regulation',
    nameCN: 'PID控制 - 水位调节',
    category: 'control',
    difficulty: 'advanced',
    tags: ['control', 'pid', 'regulation']
  },
  config: {
    controller: {
      type: 'PID',
      setpoint: 3.0,
      kp: 0.5,
      ki: 0.1,
      kd: 0.05
    }
  },
  learningObjectives: [
    {
      objective: 'Understand PID control principles in hydraulic systems',
      objectiveCN: '理解水力系统中的PID控制原理'
    },
    {
      objective: 'Learn controller tuning methods',
      objectiveCN: '学习控制器调优方法'
    }
  ]
};

export const MPC_PREDICTIVE_CONTROL_TEMPLATE = {
  metadata: {
    id: 'mpc-predictive',
    name: 'MPC Control - Predictive Control',
    nameCN: 'MPC控制 - 预测控制',
    category: 'control',
    difficulty: 'advanced',
    tags: ['control', 'mpc', 'optimization']
  },
  config: {
    controller: {
      type: 'MPC',
      horizon: 20,
      controlHorizon: 5,
      weights: {
        tracking: 10,
        effort: 1
      }
    }
  }
};
```

#### 1.5 水质模拟专题（2个新模板）

```typescript
// template_water_quality.ts
export const DISSOLVED_OXYGEN_TEMPLATE = {
  metadata: {
    id: 'water-quality-do',
    name: 'Water Quality - Dissolved Oxygen',
    nameCN: '水质 - 溶解氧',
    category: 'water-quality',
    difficulty: 'advanced',
    tags: ['water-quality', 'DO', 'BOD']
  },
  config: {
    waterQuality: {
      enableDO: true,
      enableBOD: true,
      temperature: 20,
      reaeration: true
    }
  }
};

export const NUTRIENTS_TRANSPORT_TEMPLATE = {
  metadata: {
    id: 'water-quality-nutrients',
    name: 'Water Quality - Nutrients Transport',
    nameCN: '水质 - 营养物质输运',
    category: 'water-quality',
    difficulty: 'advanced',
    tags: ['water-quality', 'nutrients', 'eutrophication']
  }
};
```

---

### 阶段2: 组件库扩展（新增7种结构）

#### 2.1 当前缺失的水工结构

```typescript
// 需要添加到ComponentPalette的新组件

export const NEW_STRUCTURES = {
  // 1. 桥梁
  bridge: {
    id: 'bridge',
    name: 'Bridge / 桥梁',
    icon: '🌉',
    type: NodeType.BRIDGE,
    defaultData: {
      openingWidth: 50,
      pierWidth: 2,
      deckElevation: 5.0,
      dischargeCoeff: 0.9
    }
  },
  
  // 2. 涵洞
  culvert: {
    id: 'culvert',
    name: 'Culvert / 涵洞',
    icon: '🚇',
    type: NodeType.CULVERT,
    defaultData: {
      diameter: 1.5,
      length: 50,
      inletElevation: 1.0,
      outletElevation: 0.8,
      manningN: 0.015
    }
  },
  
  // 3. 跌水
  drop: {
    id: 'drop',
    name: 'Drop Structure / 跌水',
    icon: '📉',
    type: NodeType.DROP,
    defaultData: {
      dropHeight: 2.0,
      width: 10.0,
      dischargeCoeff: 1.7
    }
  },
  
  // 4. 侧堰
  sideWeir: {
    id: 'side-weir',
    name: 'Side Weir / 侧堰',
    icon: '↪️',
    type: NodeType.SIDE_WEIR,
    defaultData: {
      length: 20.0,
      crestElevation: 2.0,
      dischargeCoeff: 1.7
    }
  },
  
  // 5. 阀门
  valve: {
    id: 'valve',
    name: 'Valve / 阀门',
    icon: '🔧',
    type: NodeType.VALVE,
    defaultData: {
      diameter: 1.0,
      openingDegree: 100, // 0-100%
      lossCoeff: 0.5
    }
  },
  
  // 6. 径向闸门
  radialGate: {
    id: 'radial-gate',
    name: 'Radial Gate / 径向闸门',
    icon: '🌐',
    type: NodeType.RADIAL_GATE,
    defaultData: {
      radius: 8.0,
      width: 10.0,
      opening: 5.0,
      dischargeCoeff: 0.8
    }
  },
  
  // 7. 充气坝
  inflatableDam: {
    id: 'inflatable-dam',
    name: 'Inflatable Dam / 充气坝',
    icon: '🎈',
    type: NodeType.INFLATABLE_DAM,
    defaultData: {
      length: 50.0,
      maxHeight: 3.0,
      currentHeight: 2.0,
      dischargeCoeff: 1.5
    }
  }
};
```

---

### 阶段3: 高级功能添加

#### 3.1 控制系统配置界面

```typescript
// ControlSystemPanel.tsx
interface ControlSystemPanelProps {
  modelId: string;
  structures: Structure[];
}

export const ControlSystemPanel: React.FC<ControlSystemPanelProps> = ({
  modelId,
  structures
}) => {
  const [controllerType, setControllerType] = useState<'PID' | 'MPC'>('PID');
  const [targetVariable, setTargetVariable] = useState<'water_level' | 'flow_rate'>('water_level');
  const [setpoint, setSetpoint] = useState<number>(3.0);
  
  return (
    <Card title="Control System Configuration">
      <Form layout="vertical">
        <Form.Item label="Controller Type">
          <Select value={controllerType} onChange={setControllerType}>
            <Option value="PID">PID Controller</Option>
            <Option value="MPC">Model Predictive Control</Option>
          </Select>
        </Form.Item>
        
        <Form.Item label="Controlled Variable">
          <Select value={targetVariable} onChange={setTargetVariable}>
            <Option value="water_level">Water Level</Option>
            <Option value="flow_rate">Flow Rate</Option>
          </Select>
        </Form.Item>
        
        <Form.Item label="Setpoint">
          <InputNumber value={setpoint} onChange={setSetpoint} />
        </Form.Item>
        
        {controllerType === 'PID' && (
          <>
            <Form.Item label="Kp (Proportional Gain)">
              <InputNumber />
            </Form.Item>
            <Form.Item label="Ki (Integral Gain)">
              <InputNumber />
            </Form.Item>
            <Form.Item label="Kd (Derivative Gain)">
              <InputNumber />
            </Form.Item>
          </>
        )}
        
        {controllerType === 'MPC' && (
          <>
            <Form.Item label="Prediction Horizon">
              <InputNumber min={5} max={50} />
            </Form.Item>
            <Form.Item label="Control Horizon">
              <InputNumber min={1} max={20} />
            </Form.Item>
          </>
        )}
      </Form>
    </Card>
  );
};
```

#### 3.2 水质模拟配置界面

```typescript
// WaterQualityPanel.tsx
export const WaterQualityPanel: React.FC = () => {
  const [enableWQ, setEnableWQ] = useState(false);
  const [parameters, setParameters] = useState({
    dissolvedOxygen: true,
    BOD: true,
    temperature: 20,
    nutrients: false,
    phytoplankton: false
  });
  
  return (
    <Card title="Water Quality Module">
      <Form layout="vertical">
        <Form.Item label="Enable Water Quality Simulation">
          <Switch checked={enableWQ} onChange={setEnableWQ} />
        </Form.Item>
        
        {enableWQ && (
          <>
            <Divider />
            <h4>Parameters to Simulate</h4>
            
            <Checkbox.Group>
              <Checkbox value="DO">Dissolved Oxygen (DO)</Checkbox>
              <Checkbox value="BOD">Biochemical Oxygen Demand (BOD)</Checkbox>
              <Checkbox value="nutrients">Nutrients (N, P)</Checkbox>
              <Checkbox value="phytoplankton">Phytoplankton</Checkbox>
            </Checkbox.Group>
            
            <Form.Item label="Water Temperature (°C)">
              <InputNumber min={0} max={40} value={20} />
            </Form.Item>
            
            <Form.Item label="Initial DO Concentration (mg/L)">
              <InputNumber min={0} max={15} value={8} />
            </Form.Item>
          </>
        )}
      </Form>
    </Card>
  );
};
```

#### 3.3 参数优化界面

```typescript
// ParameterOptimizationPanel.tsx
export const ParameterOptimizationPanel: React.FC = () => {
  const [optimizationType, setOptimizationType] = useState<'calibration' | 'design'>('calibration');
  
  return (
    <Card title="Parameter Optimization">
      <Form layout="vertical">
        <Form.Item label="Optimization Type">
          <Radio.Group value={optimizationType} onChange={(e) => setOptimizationType(e.target.value)}>
            <Radio value="calibration">Parameter Calibration (校准)</Radio>
            <Radio value="design">Design Optimization (设计优化)</Radio>
          </Radio.Group>
        </Form.Item>
        
        {optimizationType === 'calibration' && (
          <>
            <Form.Item label="Parameters to Calibrate">
              <Checkbox.Group>
                <Checkbox value="manning_n">Manning's n</Checkbox>
                <Checkbox value="discharge_coeff">Discharge Coefficient</Checkbox>
                <Checkbox value="initial_depth">Initial Depth</Checkbox>
              </Checkbox.Group>
            </Form.Item>
            
            <Form.Item label="Observed Data File">
              <Upload>
                <Button icon={<UploadOutlined />}>Upload CSV</Button>
              </Upload>
            </Form.Item>
            
            <Form.Item label="Optimization Algorithm">
              <Select defaultValue="pso">
                <Option value="pso">Particle Swarm Optimization</Option>
                <Option value="genetic">Genetic Algorithm</Option>
                <Option value="gradient">Gradient Descent</Option>
              </Select>
            </Form.Item>
          </>
        )}
      </Form>
      
      <Button type="primary" block>
        Start Optimization
      </Button>
    </Card>
  );
};
```

---

### 阶段4: 测试案例展示页面

```typescript
// TestCaseLibrary.tsx
export const TestCaseLibrary: React.FC = () => {
  const testCategories = [
    {
      category: 'Dam Break',
      categoryCN: '溃坝',
      count: 13,
      cases: [
        { name: 'Ritter Analytical Solution', file: 'test_dam_break.py', status: 'passed' },
        { name: 'SWASHES Benchmark', file: 'test_dam_break_swashes.py', status: 'passed' },
        // ... 更多案例
      ]
    },
    {
      category: 'Pressurized Flow',
      categoryCN: '有压流',
      count: 5,
      cases: [
        { name: 'Water Hammer Validation', file: 'water_hammer_validation.py', status: 'passed' },
        { name: 'Hardy-Cross Network', file: 'hardy_cross_validation.py', status: 'passed' },
        // ... 更多案例
      ]
    },
    // ... 其他分类
  ];
  
  return (
    <div className="test-case-library">
      <PageHeader
        title="Test Case Library"
        subTitle={`Total: 544 test cases`}
      />
      
      <Collapse defaultActiveKey={['dam-break']}>
        {testCategories.map(category => (
          <Panel
            key={category.category}
            header={`${category.categoryCN} / ${category.category} (${category.count} cases)`}
          >
            <Table
              dataSource={category.cases}
              columns={[
                { title: 'Test Name', dataIndex: 'name', key: 'name' },
                { title: 'File', dataIndex: 'file', key: 'file' },
                { 
                  title: 'Status', 
                  dataIndex: 'status', 
                  key: 'status',
                  render: (status) => (
                    <Badge 
                      status={status === 'passed' ? 'success' : 'error'} 
                      text={status}
                    />
                  )
                },
                {
                  title: 'Actions',
                  key: 'actions',
                  render: (_, record) => (
                    <Space>
                      <Button size="small">View Code</Button>
                      <Button size="small" type="primary">Run Test</Button>
                      <Button size="small">View Results</Button>
                    </Space>
                  )
                }
              ]}
            />
          </Panel>
        ))}
      </Collapse>
    </div>
  );
};
```

---

## 📅 实施时间表

### 第1周：模板库扩展
- 实现14个新模板
- 测试所有模板的正确性
- 编写模板文档

### 第2周：组件库扩展
- 添加7种新水工结构到ComponentPalette
- 实现每种结构的PropertyPanel
- 测试拖拽和配置功能

### 第3周：控制系统界面
- 实现ControlSystemPanel
- 集成PID控制器配置
- 集成MPC控制器配置
- 后端API支持

### 第4周：水质模拟界面
- 实现WaterQualityPanel
- 支持DO/BOD/Nutrients配置
- 后端API支持

### 第5周：参数优化界面
- 实现ParameterOptimizationPanel
- 支持参数校准功能
- 支持设计优化功能

### 第6周：测试案例展示页面
- 实现TestCaseLibrary
- 分类展示所有544个测试案例
- 一键运行测试功能

### 第7-8周：测试与完善
- 全面测试所有新功能
- 修复bug
- 性能优化
- 文档编写

---

## 🎯 成功指标

### 功能完整性
- ✅ 模板数量: 20+ （目标达成）
- ✅ 水工结构: 11种全部支持
- ✅ 控制系统: PID + MPC
- ✅ 水质模拟: DO/BOD/Nutrients
- ✅ 参数优化: 校准 + 设计

### 用户体验
- ✅ 所有新功能均有完整文档
- ✅ 每个模板有详细说明和学习目标
- ✅ 拖拽操作流畅
- ✅ 配置界面清晰易用

### 测试覆盖
- ✅ 前端组件单元测试覆盖率 > 80%
- ✅ 集成测试覆盖所有新功能
- ✅ E2E测试覆盖主要用户流程

---

## 🚀 预期成果

### 扩展后的系统能力

```
模板库:
- 从 6个 → 20+个
- 覆盖所有主要测试案例类型

组件库:
- 从 4种 → 11种水工结构
- 完整支持所有核心算法

功能范围:
- 基础仿真 → 高级控制 + 水质 + 优化
- 达到商业软件功能完整性

用户体验:
- Web界面功能与算法能力匹配
- 544个测试案例可视化展示
- 一键运行示例和查看结果
```

### 商业价值

```
✅ 功能完整性: 对标HEC-RAS + SWMM
✅ 易用性: 超越商业软件（Web界面）
✅ 教学价值: 544个测试案例作为教学资源
✅ 研究价值: 先进算法 + 开放架构
✅ 商业价值: 完整的商业软件功能
```

---

## ✨ 最终愿景

**打造世界一流的Web端水力学仿真平台**

- 算法: 国际领先（Godunov FVM + WENO3）
- 功能: 商业完整（11种结构 + 控制 + 水质）
- 界面: 现代易用（拖拽建模 + 实时仿真）
- 资源: 丰富开放（544个测试案例 + 20+模板）
- 生态: 开放创新（Web API + 插件系统）

**成为水力学领域的"Simulink" + "HEC-RAS" + "SWMM"的完美结合！**

---

**编制日期**: 2025年11月13日
**预计完成**: 2025年12月底（8周）
**投资回报**: 极高（填补Web端商业水力学软件空白）


