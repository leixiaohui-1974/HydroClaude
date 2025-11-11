/**
 * Component Palette
 * 组件面板 - 显示可拖拽的组件库
 */

import React, { useState } from 'react';
import { Collapse, Card, Tooltip } from 'antd';
import { componentCategories } from '../utils/componentTemplates';
import { ComponentTemplate } from '../types/model.types';
import './ComponentPalette.css';

const { Panel } = Collapse;

interface ComponentPaletteProps {
  onComponentDragStart: (template: ComponentTemplate, event: React.DragEvent) => void;
}

const ComponentPalette: React.FC<ComponentPaletteProps> = ({ onComponentDragStart }) => {
  const [activeKeys, setActiveKeys] = useState<string[]>(['canal', 'structures', 'boundaries']);

  const handleDragStart = (template: ComponentTemplate) => (event: React.DragEvent) => {
    // 设置拖拽数据
    event.dataTransfer.setData('application/reactflow', JSON.stringify(template));
    event.dataTransfer.effectAllowed = 'copy';

    // 调用父组件回调
    onComponentDragStart(template, event);
  };

  return (
    <div className="component-palette">
      <div className="palette-header">
        <h3>组件库</h3>
        <p>拖拽组件到画布</p>
      </div>

      <Collapse
        activeKey={activeKeys}
        onChange={(keys) => setActiveKeys(keys as string[])}
        bordered={false}
        className="palette-collapse"
      >
        {componentCategories.map(category => (
          <Panel
            header={
              <div className="category-header">
                <span className="category-icon">{category.icon}</span>
                <span className="category-name">{category.name}</span>
                <span className="category-count">({category.components.length})</span>
              </div>
            }
            key={category.id}
          >
            <div className="component-list">
              {category.components.map(component => (
                <Tooltip
                  key={component.id}
                  title={component.description}
                  placement="right"
                >
                  <Card
                    className="component-card"
                    size="small"
                    hoverable
                    draggable
                    onDragStart={handleDragStart(component)}
                  >
                    <div className="component-card-content">
                      <span className="component-icon">{component.icon}</span>
                      <span className="component-name">{component.name}</span>
                    </div>
                  </Card>
                </Tooltip>
              ))}
            </div>
          </Panel>
        ))}
      </Collapse>

      <div className="palette-footer">
        <small>提示: 拖拽组件到画布上添加</small>
      </div>
    </div>
  );
};

export default ComponentPalette;
