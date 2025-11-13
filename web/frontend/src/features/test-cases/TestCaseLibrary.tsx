/**
 * Test Case Library - 测试案例库
 * 展示和管理所有541个测试案例
 * 
 * Features:
 * - 分类浏览（9大类）
 * - 全文搜索
 * - 一键运行测试
 * - 查看分析报告
 * - 可视化结果展示
 */

import React, { useState, useEffect } from 'react';
import {
  Layout,
  Card,
  Input,
  Select,
  Button,
  Table,
  Tag,
  Space,
  Tabs,
  Badge,
  Drawer,
  Spin,
  message,
  Empty,
  Statistic,
  Row,
  Col,
  Typography,
  Divider,
  Modal,
  Collapse
} from 'antd';
import {
  SearchOutlined,
  PlayCircleOutlined,
  FileTextOutlined,
  FilterOutlined,
  BarChartOutlined,
  RocketOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import { Line, Scatter } from 'react-chartjs-2';
import './TestCaseLibrary.css';

const { Content, Sider } = Layout;
const { Search } = Input;
const { Option } = Select;
const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { Panel } = Collapse;

interface TestCase {
  metadata: {
    id: string;
    name: string;
    nameCN: string;
    category: string;
    subcategory: string;
    difficulty: string;
    tags: string[];
    author: string;
    version: string;
    references: string[];
  };
  config: Record<string, any>;
  expectedResults: Record<string, any>;
  validationCriteria: Record<string, any>;
  sourcePath: string;
}

interface TestReport {
  metadata: Record<string, any>;
  summary: { en: string; cn: string };
  analysis: Record<string, any>;
  metrics: Record<string, number>;
  validation: {
    passed: boolean;
    checks: Array<{
      name: string;
      nameCN: string;
      passed: boolean;
      value: string;
      threshold: string;
    }>;
  };
  visualizations: Array<{
    type: string;
    title: string;
    titleCN: string;
    xAxis: string;
    yAxis: string;
    data: any;
  }>;
  conclusions: { en: string[]; cn: string[] };
  markdown: string;
}

const TestCaseLibrary: React.FC = () => {
  // State
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [filteredCases, setFilteredCases] = useState<TestCase[]>([]);
  const [categories, setCategories] = useState<Record<string, number>>({});
  const [statistics, setStatistics] = useState<any>({});
  
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  const [selectedCase, setSelectedCase] = useState<TestCase | null>(null);
  const [caseDetailVisible, setCaseDetailVisible] = useState(false);
  
  const [runningCases, setRunningCases] = useState<Set<string>>(new Set());
  const [testReport, setTestReport] = useState<TestReport | null>(null);
  const [reportVisible, setReportVisible] = useState(false);
  
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState<'en' | 'cn'>('cn');

  // Load test cases on mount
  useEffect(() => {
    loadTestCases();
    loadStatistics();
  }, []);

  // Filter cases when filters change
  useEffect(() => {
    filterCases();
  }, [testCases, selectedCategory, selectedDifficulty, searchQuery]);

  const loadTestCases = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/test-cases?limit=1000');
      const data = await response.json();
      
      setTestCases(data.cases);
      setCategories(data.categories);
      
      message.success(`Loaded ${data.total} test cases / 加载了${data.total}个测试案例`);
    } catch (error) {
      message.error('Failed to load test cases / 加载测试案例失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const response = await fetch('/api/v1/test-cases/statistics');
      const data = await response.json();
      setStatistics(data);
    } catch (error) {
      console.error('Failed to load statistics:', error);
    }
  };

  const filterCases = () => {
    let filtered = [...testCases];

    // Category filter
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(c => c.metadata.category === selectedCategory);
    }

    // Difficulty filter
    if (selectedDifficulty !== 'all') {
      filtered = filtered.filter(c => c.metadata.difficulty === selectedDifficulty);
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(c =>
        c.metadata.name.toLowerCase().includes(query) ||
        c.metadata.nameCN.includes(searchQuery) ||
        c.metadata.category.toLowerCase().includes(query) ||
        c.metadata.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    setFilteredCases(filtered);
  };

  const handleSearch = async (value: string) => {
    if (!value) {
      setSearchQuery('');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`/api/v1/test-cases/search?q=${encodeURIComponent(value)}`);
      const data = await response.json();
      setFilteredCases(data.cases);
      setSearchQuery(value);
    } catch (error) {
      message.error('Search failed / 搜索失败');
    } finally {
      setLoading(false);
    }
  };

  const runTestCase = async (caseId: string) => {
    setRunningCases(prev => new Set(prev).add(caseId));
    
    try {
      // Start test
      const response = await fetch(`/api/v1/test-cases/run/${caseId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const result = await response.json();
      
      if (result.status === 'queued' || result.status === 'running') {
        message.success('Test queued / 测试已排队');
        
        // Simulate waiting for result (in production, use polling or WebSocket)
        setTimeout(async () => {
          await loadTestReport(result.resultId);
        }, 3000);
      }
    } catch (error) {
      message.error('Failed to run test / 运行测试失败');
      console.error(error);
    } finally {
      setRunningCases(prev => {
        const newSet = new Set(prev);
        newSet.delete(caseId);
        return newSet;
      });
    }
  };

  const loadTestReport = async (resultId: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/test-cases/report/${resultId}`);
      const report = await response.json();
      
      setTestReport(report);
      setReportVisible(true);
      message.success('Report generated / 报告已生成');
    } catch (error) {
      message.error('Failed to load report / 加载报告失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const viewCaseDetail = (testCase: TestCase) => {
    setSelectedCase(testCase);
    setCaseDetailVisible(true);
  };

  // Render functions
  const renderStatistics = () => (
    <Row gutter={16} style={{ marginBottom: 24 }}>
      <Col span={6}>
        <Card>
          <Statistic
            title="Total Cases / 总案例数"
            value={statistics.total || 0}
            prefix={<FileTextOutlined />}
            valueStyle={{ color: '#3f8600' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="Categories / 分类"
            value={Object.keys(categories).length}
            prefix={<FilterOutlined />}
            valueStyle={{ color: '#1890ff' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="Beginner / 初级"
            value={statistics.difficulty?.beginner || 0}
            valueStyle={{ color: '#52c41a' }}
          />
        </Card>
      </Col>
      <Col span={6}>
        <Card>
          <Statistic
            title="Advanced / 高级"
            value={statistics.difficulty?.advanced || 0}
            valueStyle={{ color: '#faad14' }}
          />
        </Card>
      </Col>
    </Row>
  );

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      'dam_break': 'red',
      'pressurized': 'blue',
      'lake_at_rest': 'cyan',
      'structures': 'green',
      'control': 'purple',
      'water_quality': 'orange',
      'network': 'geekblue',
      'benchmark': 'magenta',
      'general': 'default'
    };
    return colors[category] || 'default';
  };

  const getDifficultyColor = (difficulty: string): string => {
    const colors: Record<string, string> = {
      'beginner': 'green',
      'intermediate': 'blue',
      'advanced': 'orange'
    };
    return colors[difficulty] || 'default';
  };

  const columns = [
    {
      title: 'Name / 名称',
      dataIndex: ['metadata', 'name'],
      key: 'name',
      width: 250,
      render: (text: string, record: TestCase) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#888' }}>{record.metadata.nameCN}</div>
        </div>
      )
    },
    {
      title: 'Category / 分类',
      dataIndex: ['metadata', 'category'],
      key: 'category',
      width: 120,
      render: (category: string) => (
        <Tag color={getCategoryColor(category)}>{category}</Tag>
      )
    },
    {
      title: 'Difficulty / 难度',
      dataIndex: ['metadata', 'difficulty'],
      key: 'difficulty',
      width: 100,
      render: (difficulty: string) => (
        <Tag color={getDifficultyColor(difficulty)}>{difficulty}</Tag>
      )
    },
    {
      title: 'Tags / 标签',
      dataIndex: ['metadata', 'tags'],
      key: 'tags',
      width: 200,
      render: (tags: string[]) => (
        <>
          {tags.slice(0, 3).map(tag => (
            <Tag key={tag} style={{ fontSize: '11px' }}>{tag}</Tag>
          ))}
        </>
      )
    },
    {
      title: 'Actions / 操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: TestCase) => (
        <Space>
          <Button
            size="small"
            icon={<PlayCircleOutlined />}
            type="primary"
            onClick={() => runTestCase(record.metadata.id)}
            loading={runningCases.has(record.metadata.id)}
          >
            Run / 运行
          </Button>
          <Button
            size="small"
            icon={<FileTextOutlined />}
            onClick={() => viewCaseDetail(record)}
          >
            Detail / 详情
          </Button>
        </Space>
      )
    }
  ];

  const renderCaseDetail = () => (
    <Drawer
      title={
        <div>
          <div>{selectedCase?.metadata.name}</div>
          <div style={{ fontSize: '14px', fontWeight: 'normal', color: '#888' }}>
            {selectedCase?.metadata.nameCN}
          </div>
        </div>
      }
      placement="right"
      width={600}
      onClose={() => setCaseDetailVisible(false)}
      open={caseDetailVisible}
    >
      {selectedCase && (
        <div>
          <Collapse defaultActiveKey={['basic', 'config']}>
            <Panel header="Basic Information / 基本信息" key="basic">
              <Paragraph>
                <Text strong>Category / 分类: </Text>
                <Tag color={getCategoryColor(selectedCase.metadata.category)}>
                  {selectedCase.metadata.category}
                </Tag>
              </Paragraph>
              <Paragraph>
                <Text strong>Difficulty / 难度: </Text>
                <Tag color={getDifficultyColor(selectedCase.metadata.difficulty)}>
                  {selectedCase.metadata.difficulty}
                </Tag>
              </Paragraph>
              <Paragraph>
                <Text strong>Tags / 标签: </Text>
                {selectedCase.metadata.tags.map(tag => (
                  <Tag key={tag}>{tag}</Tag>
                ))}
              </Paragraph>
              <Paragraph>
                <Text strong>Source / 源文件: </Text>
                <Text code>{selectedCase.sourcePath}</Text>
              </Paragraph>
            </Panel>

            <Panel header="Configuration / 配置" key="config">
              <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
                {JSON.stringify(selectedCase.config, null, 2)}
              </pre>
            </Panel>

            <Panel header="Expected Results / 预期结果" key="expected">
              <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
                {JSON.stringify(selectedCase.expectedResults, null, 2)}
              </pre>
            </Panel>

            <Panel header="Validation Criteria / 验证标准" key="validation">
              <pre style={{ background: '#f5f5f5', padding: '12px', borderRadius: '4px' }}>
                {JSON.stringify(selectedCase.validationCriteria, null, 2)}
              </pre>
            </Panel>

            {selectedCase.metadata.references.length > 0 && (
              <Panel header="References / 参考文献" key="references">
                <ul>
                  {selectedCase.metadata.references.map((ref, idx) => (
                    <li key={idx}>{ref}</li>
                  ))}
                </ul>
              </Panel>
            )}
          </Collapse>

          <Divider />

          <Button
            type="primary"
            size="large"
            icon={<RocketOutlined />}
            block
            onClick={() => {
              setCaseDetailVisible(false);
              runTestCase(selectedCase.metadata.id);
            }}
          >
            Run This Test / 运行此测试
          </Button>
        </div>
      )}
    </Drawer>
  );

  const renderReport = () => (
    <Modal
      title={
        <div>
          <FileTextOutlined /> Analysis Report / 分析报告
        </div>
      }
      open={reportVisible}
      onCancel={() => setReportVisible(false)}
      width={1200}
      footer={[
        <Button key="close" onClick={() => setReportVisible(false)}>
          Close / 关闭
        </Button>,
        <Button
          key="download"
          type="primary"
          icon={<FileTextOutlined />}
          onClick={() => {
            // Download markdown
            const blob = new Blob([testReport?.markdown || ''], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'test-report.md';
            a.click();
          }}
        >
          Download / 下载
        </Button>
      ]}
    >
      {testReport && (
        <Tabs defaultActiveKey="summary">
          <TabPane tab="Summary / 摘要" key="summary">
            <Card>
              <Title level={4}>
                {testReport.validation.passed ? (
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                ) : (
                  <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
                )}{' '}
                {testReport.validation.passed ? 'PASSED / 通过' : 'FAILED / 失败'}
              </Title>
              
              <Paragraph>
                <Text strong>English:</Text><br />
                {testReport.summary.en}
              </Paragraph>
              
              <Paragraph>
                <Text strong>中文:</Text><br />
                {testReport.summary.cn}
              </Paragraph>

              <Divider />

              <Title level={5}>Metrics / 关键指标</Title>
              <Row gutter={16}>
                {Object.entries(testReport.metrics).map(([key, value]) => (
                  <Col span={8} key={key}>
                    <Statistic
                      title={key}
                      value={typeof value === 'number' ? value.toFixed(3) : value}
                      precision={3}
                    />
                  </Col>
                ))}
              </Row>
            </Card>
          </TabPane>

          <TabPane tab="Analysis / 分析" key="analysis">
            <Card>
              <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '4px', overflow: 'auto' }}>
                {JSON.stringify(testReport.analysis, null, 2)}
              </pre>
            </Card>
          </TabPane>

          <TabPane tab="Validation / 验证" key="validation">
            <Card>
              {testReport.validation.checks.map((check, idx) => (
                <div key={idx} style={{ marginBottom: '16px' }}>
                  <Badge
                    status={check.passed ? 'success' : 'error'}
                    text={
                      <span>
                        <Text strong>{check.name}</Text> / {check.nameCN}
                        <br />
                        <Text type="secondary">
                          Value: {check.value} | Threshold: {check.threshold}
                        </Text>
                      </span>
                    }
                  />
                </div>
              ))}
            </Card>
          </TabPane>

          <TabPane tab="Visualizations / 可视化" key="viz">
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              {testReport.visualizations.map((viz, idx) => (
                <Card key={idx} title={`${viz.title} / ${viz.titleCN}`}>
                  <div style={{ height: '300px' }}>
                    {/* Placeholder for charts - integrate with Chart.js or Plotly */}
                    <Empty description={`Chart: ${viz.type}`} />
                  </div>
                </Card>
              ))}
            </Space>
          </TabPane>

          <TabPane tab="Markdown" key="markdown">
            <Card>
              <div style={{ maxHeight: '600px', overflow: 'auto' }}>
                <ReactMarkdown>{testReport.markdown}</ReactMarkdown>
              </div>
            </Card>
          </TabPane>
        </Tabs>
      )}
    </Modal>
  );

  return (
    <Layout className="test-case-library">
      <Sider width={250} theme="light" style={{ padding: '16px' }}>
        <div style={{ marginBottom: '16px' }}>
          <Title level={4}>Filters / 筛选</Title>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <Text strong>Category / 分类</Text>
          <Select
            style={{ width: '100%', marginTop: '8px' }}
            value={selectedCategory}
            onChange={setSelectedCategory}
          >
            <Option value="all">All / 全部 ({testCases.length})</Option>
            {Object.entries(categories).map(([cat, count]) => (
              <Option key={cat} value={cat}>
                {cat} ({count})
              </Option>
            ))}
          </Select>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <Text strong>Difficulty / 难度</Text>
          <Select
            style={{ width: '100%', marginTop: '8px' }}
            value={selectedDifficulty}
            onChange={setSelectedDifficulty}
          >
            <Option value="all">All / 全部</Option>
            <Option value="beginner">Beginner / 初级</Option>
            <Option value="intermediate">Intermediate / 中级</Option>
            <Option value="advanced">Advanced / 高级</Option>
          </Select>
        </div>

        <Divider />

        <div>
          <Text strong>Top Tags / 热门标签</Text>
          <div style={{ marginTop: '8px' }}>
            {Object.entries(statistics.topTags || {}).slice(0, 10).map(([tag, count]) => (
              <Tag
                key={tag}
                style={{ marginBottom: '8px', cursor: 'pointer' }}
                onClick={() => handleSearch(tag)}
              >
                {tag} ({count})
              </Tag>
            ))}
          </div>
        </div>
      </Sider>

      <Content style={{ padding: '24px' }}>
        <div style={{ marginBottom: '24px' }}>
          <Title level={2}>
            <BarChartOutlined /> Test Case Library / 测试案例库
          </Title>
          <Text type="secondary">
            Browse and run 541+ test cases / 浏览并运行541+个测试案例
          </Text>
        </div>

        {renderStatistics()}

        <Card style={{ marginBottom: '16px' }}>
          <Search
            placeholder="Search test cases / 搜索测试案例"
            allowClear
            enterButton={<SearchOutlined />}
            size="large"
            onSearch={handleSearch}
            style={{ marginBottom: '16px' }}
          />

          <Space>
            <Text>
              Showing {filteredCases.length} / {testCases.length} cases
            </Text>
            <Button size="small" onClick={() => {
              setSelectedCategory('all');
              setSelectedDifficulty('all');
              setSearchQuery('');
            }}>
              Clear Filters / 清除筛选
            </Button>
          </Space>
        </Card>

        <Card>
          <Table
            columns={columns}
            dataSource={filteredCases}
            rowKey={(record) => record.metadata.id}
            loading={loading}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `Total ${total} cases / 共${total}个案例`
            }}
            scroll={{ x: 1000 }}
          />
        </Card>

        {renderCaseDetail()}
        {renderReport()}
      </Content>
    </Layout>
  );
};

export default TestCaseLibrary;


