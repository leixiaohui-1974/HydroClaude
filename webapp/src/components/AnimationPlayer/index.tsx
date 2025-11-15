import React, { useState, useEffect, useRef } from 'react';
import { Card, Slider, Button, Space, InputNumber, Select } from 'antd';
import {
  PlayCircleOutlined,
  PauseOutlined,
  StepForwardOutlined,
  StepBackwardOutlined,
  FastForwardOutlined,
  FastBackwardOutlined,
} from '@ant-design/icons';

const { Option } = Select;

interface AnimationPlayerProps {
  totalFrames: number;
  currentFrame: number;
  onFrameChange: (frame: number) => void;
  fps?: number;
  children?: React.ReactNode;
}

const AnimationPlayer: React.FC<AnimationPlayerProps> = ({
  totalFrames,
  currentFrame,
  onFrameChange,
  fps = 10,
  children,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // 播放控制
  useEffect(() => {
    if (isPlaying) {
      const interval = 1000 / (fps * speed);
      intervalRef.current = setInterval(() => {
        onFrameChange((currentFrame + 1) % totalFrames);
      }, interval);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isPlaying, currentFrame, totalFrames, fps, speed, onFrameChange]);

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleStepForward = () => {
    setIsPlaying(false);
    onFrameChange(Math.min(currentFrame + 1, totalFrames - 1));
  };

  const handleStepBackward = () => {
    setIsPlaying(false);
    onFrameChange(Math.max(currentFrame - 1, 0));
  };

  const handleJumpToStart = () => {
    setIsPlaying(false);
    onFrameChange(0);
  };

  const handleJumpToEnd = () => {
    setIsPlaying(false);
    onFrameChange(totalFrames - 1);
  };

  const handleSliderChange = (value: number) => {
    setIsPlaying(false);
    onFrameChange(value);
  };

  return (
    <Card>
      {/* 显示区域 */}
      <div style={{ minHeight: 400, marginBottom: 16 }}>
        {children}
      </div>

      {/* 控制面板 */}
      <div>
        {/* 进度条 */}
        <div style={{ marginBottom: 16 }}>
          <Slider
            min={0}
            max={totalFrames - 1}
            value={currentFrame}
            onChange={handleSliderChange}
            tooltip={{
              formatter: (value) => `帧 ${value} / ${totalFrames - 1}`,
            }}
          />
        </div>

        {/* 控制按钮 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Button
              icon={<FastBackwardOutlined />}
              onClick={handleJumpToStart}
              disabled={currentFrame === 0}
            >
              开始
            </Button>
            <Button
              icon={<StepBackwardOutlined />}
              onClick={handleStepBackward}
              disabled={currentFrame === 0}
            />
            <Button
              type="primary"
              icon={isPlaying ? <PauseOutlined /> : <PlayCircleOutlined />}
              onClick={handlePlayPause}
            >
              {isPlaying ? '暂停' : '播放'}
            </Button>
            <Button
              icon={<StepForwardOutlined />}
              onClick={handleStepForward}
              disabled={currentFrame === totalFrames - 1}
            />
            <Button
              icon={<FastForwardOutlined />}
              onClick={handleJumpToEnd}
              disabled={currentFrame === totalFrames - 1}
            >
              结束
            </Button>
          </Space>

          <Space>
            <span>帧数:</span>
            <InputNumber
              min={0}
              max={totalFrames - 1}
              value={currentFrame}
              onChange={(value) => value !== null && handleSliderChange(value)}
              style={{ width: 100 }}
            />
            <span>/ {totalFrames - 1}</span>
            
            <span style={{ marginLeft: 16 }}>速度:</span>
            <Select value={speed} onChange={setSpeed} style={{ width: 100 }}>
              <Option value={0.25}>0.25x</Option>
              <Option value={0.5}>0.5x</Option>
              <Option value={1}>1x</Option>
              <Option value={2}>2x</Option>
              <Option value={4}>4x</Option>
            </Select>
          </Space>
        </div>
      </div>
    </Card>
  );
};

export default AnimationPlayer;
