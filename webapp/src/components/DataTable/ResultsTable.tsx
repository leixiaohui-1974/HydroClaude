import React, { useState, useMemo } from 'react';
import { Table, Button, Space, Input, Select, message } from 'antd';
import { DownloadOutlined, SearchOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
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

const ResultsTable: React.FC<ResultsTableProps> = ({ data, title: _title }) => {
  const { t } = useTranslation();
  const [searchText, setSearchText] = useState('');
  const [filterVariable, setFilterVariable] = useState<string>('all');
  const [pageSize, setPageSize] = useState(10);

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

  const columns: ColumnsType<any> = [
    {
      title: t('dataTable.positionM'),
      dataIndex: 'position',
      key: 'position',
      width: 120,
      fixed: 'left',
      sorter: (a, b) => a.position - b.position,
      render: (val) => val?.toFixed(2),
    },
    {
      title: t('dataTable.depthM'),
      dataIndex: 'depth',
      key: 'depth',
      width: 120,
      sorter: (a, b) => (a.depth || 0) - (b.depth || 0),
      render: (val) => val?.toFixed(4),
    },
    {
      title: t('dataTable.velocityMs'),
      dataIndex: 'velocity',
      key: 'velocity',
      width: 120,
      sorter: (a, b) => (a.velocity || 0) - (b.velocity || 0),
      render: (val) => val?.toFixed(4),
    },
    {
      title: t('dataTable.froudeNumber'),
      dataIndex: 'froude',
      key: 'froude',
      width: 120,
      sorter: (a, b) => (a.froude || 0) - (b.froude || 0),
      render: (val) => val?.toFixed(4),
    },
    {
      title: t('dataTable.dischargeM3s'),
      dataIndex: 'discharge',
      key: 'discharge',
      width: 120,
      sorter: (a, b) => (a.discharge || 0) - (b.discharge || 0),
      render: (val) => val?.toFixed(4),
    },
  ];

  const exportToCSV = () => {
    if (!tableData || tableData.length === 0) {
      message.warning(t('dataTable.noDataToExport'));
      return;
    }

    try {
      const headers = ['Position(m)', 'Depth(m)', 'Velocity(m/s)', 'Froude', 'Discharge(m³/s)'];
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

      const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', `results_${Date.now()}.csv`);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      message.success(t('dataTable.exportSuccess'));
    } catch {
      message.error(t('dataTable.exportFailed'));
    }
  };

  const exportToJSON = () => {
    if (!data) {
      message.warning(t('dataTable.noDataToExport'));
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

      message.success(t('dataTable.exportSuccess'));
    } catch {
      message.error(t('dataTable.exportFailed'));
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Input
            placeholder={t('dataTable.searchPosition')}
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
            <Option value="all">{t('dataTable.allVariables')}</Option>
            <Option value="depth">{t('dataTable.depth')}</Option>
            <Option value="velocity">{t('dataTable.velocity')}</Option>
            <Option value="froude">{t('dataTable.froudeNumber')}</Option>
          </Select>
        </Space>

        <Space>
          <Button icon={<DownloadOutlined />} onClick={exportToCSV}>
            {t('dataTable.exportCSV')}
          </Button>
          <Button icon={<DownloadOutlined />} onClick={exportToJSON}>
            {t('dataTable.exportJSON')}
          </Button>
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={tableData}
        pagination={{
          pageSize,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => t('dataTable.totalRecords', { total }),
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
