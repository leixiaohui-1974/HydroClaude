import React, { useRef, useEffect } from 'react';
import { message } from 'antd';
import Editor, { OnMount } from '@monaco-editor/react';
import type { editor } from 'monaco-editor';
import type { SimulationConfig } from '@/services/simulations';

interface JsonEditorProps {
  config: SimulationConfig;
  onChange: (config: SimulationConfig) => void;
  height?: string;
}

const JsonEditor: React.FC<JsonEditorProps> = ({ 
  config, 
  onChange, 
  height = 'calc(100vh - 240px)' 
}) => {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // 配置JSON验证
    monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
      validate: true,
      schemas: [
        {
          uri: 'http://hydroclaude.com/schemas/simulation-config.json',
          fileMatch: ['*'],
          schema: {
            type: 'object',
            properties: {
              simulation: {
                type: 'object',
                properties: {
                  type: { type: 'string', enum: ['steady', 'unsteady'] },
                  mode: { type: 'string', enum: ['single_canal', 'network'] },
                },
                required: ['type', 'mode'],
              },
              canal: {
                type: 'object',
                properties: {
                  length: { type: 'number', minimum: 1 },
                  width: { type: 'number', minimum: 0.1 },
                  slope: { type: 'number', minimum: 0.0001 },
                  manning_n: { type: 'number', minimum: 0.01, maximum: 0.1 },
                },
                required: ['length', 'width', 'slope', 'manning_n'],
              },
              solver: {
                type: 'object',
                properties: {
                  method: { type: 'string', enum: ['hydrostatic', 'godunov', 'simple'] },
                },
                required: ['method'],
              },
              boundary_conditions: {
                type: 'object',
                required: ['upstream', 'downstream'],
              },
            },
            required: ['simulation', 'canal', 'solver', 'boundary_conditions'],
          },
        },
      ],
    });

    // 自动格式化
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      editor.getAction('editor.action.formatDocument')?.run();
    });
  };

  const handleEditorChange = (value: string | undefined) => {
    if (!value) return;

    try {
      const parsedConfig = JSON.parse(value);
      onChange(parsedConfig);
    } catch (error) {
      // JSON解析错误，不更新配置（等待用户修复）
      console.error('JSON parse error:', error);
    }
  };

  // 当外部配置更新时，更新编辑器内容
  useEffect(() => {
    if (editorRef.current) {
      const currentValue = editorRef.current.getValue();
      const newValue = JSON.stringify(config, null, 2);
      
      // 只有当内容不同时才更新（避免循环更新）
      if (currentValue !== newValue) {
        try {
          const parsedCurrent = JSON.parse(currentValue);
          if (JSON.stringify(parsedCurrent) !== JSON.stringify(config)) {
            editorRef.current.setValue(newValue);
          }
        } catch {
          // 如果当前值无法解析，直接更新
          editorRef.current.setValue(newValue);
        }
      }
    }
  }, [config]);

  return (
    <Editor
      height={height}
      defaultLanguage="json"
      defaultValue={JSON.stringify(config, null, 2)}
      onChange={handleEditorChange}
      onMount={handleEditorDidMount}
      options={{
        minimap: { enabled: true },
        fontSize: 14,
        lineNumbers: 'on',
        renderWhitespace: 'selection',
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 2,
        wordWrap: 'on',
        formatOnPaste: true,
        formatOnType: true,
      }}
      theme="vs-dark"
    />
  );
};

export default JsonEditor;
