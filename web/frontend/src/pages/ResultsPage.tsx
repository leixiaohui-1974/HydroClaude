import { Card, Typography, Empty, Space } from 'antd'

const { Title } = Typography

const ResultsPage = () => {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card>
        <Title level={2}>📈 结果分析</Title>
        <p>查看仿真结果，生成可视化图表</p>
      </Card>

      <Card>
        <Empty
          description="暂无仿真结果"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    </Space>
  )
}

export default ResultsPage
