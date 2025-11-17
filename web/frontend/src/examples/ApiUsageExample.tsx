/**
 * HydroClaude API 使用示例
 * 展示如何在React组件中调用后端API
 */

import React, { useState } from 'react';
import axios from 'axios';

// API基础地址
const API_BASE = 'http://localhost:8000';

// TypeScript类型定义
interface PumpRequest {
  pump: {
    flow_rate: number;
    head: number;
    num_pumps: number;
    pump_type: 'single' | 'parallel' | 'series';
  };
  upstream: { water_level: number };
  downstream: { elevation: number };
  operation: { duration: number };
}

interface SimulationResult {
  task_id: string;
  status: string;
  metrics: {
    avg_flow: number;
    avg_efficiency: number;
    avg_head: number;
    total_energy_kwh: number;
  };
}

export const ApiUsageExample: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 示例1: 泵站仿真
  const runPumpSimulation = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const request: PumpRequest = {
        pump: {
          flow_rate: 10.0,
          head: 15.0,
          num_pumps: 2,
          pump_type: 'parallel'
        },
        upstream: { water_level: 5.0 },
        downstream: { elevation: 20.0 },
        operation: { duration: 100.0 }
      };

      const response = await axios.post<SimulationResult>(
        `${API_BASE}/api/structures/pump`,
        request
      );

      setResult(response.data);
    } catch (err: any) {
      setError(err.message || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  // 示例2: 获取组件类型
  const getComponentTypes = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/structures/types`);
      console.log('支持的组件:', response.data);
      alert(`系统支持 ${response.data.total_components} 种组件`);
    } catch (err: any) {
      alert('获取失败: ' + err.message);
    }
  };

  // 示例3: 水轮机仿真
  const runTurbineSimulation = async () => {
    setLoading(true);
    setError(null);

    try {
      const request = {
        turbine: {
          type: 'francis',
          rated_power: 50.0,
          rated_head: 100.0,
          rated_flow: 60.0
        },
        operation: {
          head: 100.0,
          flow: 60.0
        }
      };

      const response = await axios.post(
        `${API_BASE}/api/structures/turbine`,
        request
      );

      console.log('水轮机仿真结果:', response.data);
      alert(`发电功率: ${response.data.metrics.power_MW} MW\n效率: ${response.data.metrics.efficiency * 100}%`);
    } catch (err: any) {
      setError(err.message || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>HydroClaude API 使用示例</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <h2>示例1: 泵站仿真</h2>
        <button 
          onClick={runPumpSimulation}
          disabled={loading}
          style={{
            padding: '10px 20px',
            backgroundColor: '#1890ff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? '运行中...' : '运行泵站仿真'}
        </button>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h2>示例2: 获取组件类型</h2>
        <button 
          onClick={getComponentTypes}
          style={{
            padding: '10px 20px',
            backgroundColor: '#52c41a',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          获取组件列表
        </button>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h2>示例3: 水轮机仿真 ⭐</h2>
        <button 
          onClick={runTurbineSimulation}
          disabled={loading}
          style={{
            padding: '10px 20px',
            backgroundColor: '#722ed1',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? '运行中...' : '运行水轮机仿真'}
        </button>
      </div>

      {error && (
        <div style={{
          padding: '15px',
          backgroundColor: '#fff1f0',
          border: '1px solid #ffa39e',
          borderRadius: '4px',
          color: '#cf1322',
          marginTop: '20px'
        }}>
          <strong>错误:</strong> {error}
        </div>
      )}

      {result && (
        <div style={{
          marginTop: '20px',
          padding: '15px',
          backgroundColor: '#f6ffed',
          border: '1px solid #b7eb8f',
          borderRadius: '4px'
        }}>
          <h3>仿真结果:</h3>
          <pre style={{ backgroundColor: '#fff', padding: '10px', borderRadius: '4px' }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}

      <div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f0f2f5', borderRadius: '8px' }}>
        <h3>代码示例:</h3>
        <pre style={{ backgroundColor: '#fff', padding: '15px', borderRadius: '4px', overflow: 'auto' }}>
{`// 泵站仿真
const response = await axios.post(
  'http://localhost:8000/api/structures/pump',
  {
    pump: {
      flow_rate: 10.0,
      head: 15.0,
      num_pumps: 2,
      pump_type: 'parallel'
    },
    upstream: { water_level: 5.0 },
    downstream: { elevation: 20.0 },
    operation: { duration: 100.0 }
  }
);

console.log(response.data);`}
        </pre>
      </div>
    </div>
  );
};

export default ApiUsageExample;
