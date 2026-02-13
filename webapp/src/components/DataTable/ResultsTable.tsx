import React, { useState, useMemo } from 'react';
import { Table, Button, Space, Input, Select, message } from 'antd';
import { DownloadOutlined, SearchOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Option } = Select;

interface ResultsData {
  positions: number[];
  depths: number[];
  velocities: number[];
  froude_numbers?: number[];
  discharge?: number[];
  [key: string]: any;
}

interface ResultsTableProps {
  data: ResultsData;
  title?: string;
}

const ResultsTable: React.FC<ResultsTableProps> = ({ data, title: _title = '仿真结果数据' }) => {
  const [searchText, setSearchText] = useState('');
  const [filterVariable, setFilterVariable] = useState<string>('all');
  const [pageSize, setPageSize] = useState(10);

  // 转换数据为表格格式
  const tableData = useMemo(() => {
    if (!data || !data.positions) return [];

    return data.positions.map((pos, idx) => ({
      key: idx,
      position: pos,
      depth: data.depths?.[idx],
      velocity: data.velocities?.[idx],
      froude: data.froude_numbers?.[idx],
      discharge: data.discharge?.[idx],
    }));
  }, [data]);

  // 定义表格列
  const columns: ColumnsType<any> = [
    {
      title: '位置 (m)',
      dataIndex: 'position',
      key: 'position',
      width: 120,
      fixed: 'left',
      sorter: (a, b) => a.position - b.position,
      render: (val) => val?.toFixed(2),
    },
    {
      title: '水深 (m)',
      dataIndex: 'depth',
      key: 'depth',
      width: 120,
      sorter: (a, b) => (a.depth || 0) - (b.depth || 0),
      render: (val) => val?.toFixed(4),
    },
    {
      title: '流速 (m/s)',
      dataIndex: 'velocity',
      key: 'velocity',
      width: 120,
      sorter: (a, b) => (a.velocity || 0) - (b.velocity || 0),
      render: (val) => val?.toFixed(4),
    },
    {
      title: 'Froude数',
      dataIndex: 'froude',
      key: 'froude',
      width: 120,
      sorter: (a, b) => (a.froude || 0) - (b.froude || 0),
      render: (val) => val?.toFixed(4),
    },
    {
      title: '流量 (m³/s)',
      dataIndex: 'discharge',
      key: 'discharge',
      width: 120,
      sorter: (a, b) => (a.discharge || 0) - (b.discharge || 0),
      render: (val) => val?.toFixed(4),
    },
  ];

  // 导出CSV
  const exportToCSV = () => {
    if (!tableData || tableData.length === 0) {
      message.warning('暂无数据可导出');
      return;
    }

    try {
      // 构建CSV内容
      const headers = ['位置(m)', '水深(m)', '流速(m/s)', 'Froude数', '流量(m³/s)'];
      const csvContent = [
        headers.join(','),
        ...tableData.map(row => 
          [
            row.position?.toFixed(2),
            row.depth?.toFixed(4),
            row.velocity?.toFixed(4),
            row.froude?.toFixed(4),
            row.discharge?.toFixed(4),
          ].join(',')
        ),
      ].join('\n');

      // 创建下载链接
      const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `results_${Date.now()}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
      console.error(error);
    }
  };

  // 导出JSON
  const exportToJSON = () => {
    if (!data) {
      message.warning('暂无数据可导出');
      return;
    }

    try {
      const jsonContent = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonContent], { type: 'application/json' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `results_${Date.now()}.json`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      message.success('导出成功');
    } catch (error) {
      message.error('导出失败');
      console.error(error);
    }
  };

  return (
    <div>
      {/* 工具栏 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Input
            placeholder="搜索位置"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: 200 }}
          />
          <Select
            value={filterVariable}
            onChange={setFilterVariable}
            style={{ width: 150 }}
          >
            <Option value="all">所有变量</Option>
            <Option value="depth">水深</Option>
            <Option value="velocity">流速</Option>
            <Option value="froude">Froude数</Option>
          </Select>
        </Space>

        <Space>
          <Button icon={<DownloadOutlined />} onClick={exportToCSV}>
            导出CSV
          </Button>
          <Button icon={<DownloadOutlined />} onClick={exportToJSON}>
            导出JSON
          </Button>
        </Space>
      </div>

      {/* 数据表格 */}
      <Table
        columns={columns}
        dataSource={tableData}
        pagination={{
          pageSize,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条记录`,
          pageSizeOptions: ['10', '20', '50', '100'],
          onShowSizeChange: (_, size) => setPageSize(size),
        }}
        scroll={{ x: 600 }}
        size="small"
        bordered
      />
    </div>
  );
};

export default ResultsTable;
