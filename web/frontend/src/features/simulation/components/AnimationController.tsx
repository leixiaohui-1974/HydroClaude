import { useState, useEffect, useRef, memo } from 'react';
import { Button, Space, Select, Switch, Typography, Tooltip, Slider } from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StepBackwardOutlined,
  StepForwardOutlined,
  ReloadOutlined,
  FastForwardOutlined,
  FastBackwardOutlined
} from '@ant-design/icons';

const { Text } = Typography;

interface AnimationControllerProps {
  totalFrames: number;
  currentFrame: number;
  onFrameChange: (frame: number) => void;
  autoPlay?: boolean;
  defaultSpeed?: number;
}

/**
 * AnimationController Component
 *
 * Provides controls for animating through simulation time steps:
 * - Play/Pause/Stop
 * - Frame stepping (forward/backward)
 * - Playback speed control (0.5x - 10x)
 * - Loop toggle
 * - Frame counter and progress
 *
 * @param totalFrames - Total number of frames in the animation
 * @param currentFrame - Current frame index (0-based)
 * @param onFrameChange - Callback when frame changes
 * @param autoPlay - Auto-start playback on mount (default: false)
 * @param defaultSpeed - Default playback speed (default: 1)
 */
const AnimationController = ({
  totalFrames,
  currentFrame,
  onFrameChange,
  autoPlay = false,
  defaultSpeed = 1
}: AnimationControllerProps) => {
  const [isPlaying, setIsPlaying] = useState(autoPlay);
  const [playbackSpeed, setPlaybackSpeed] = useState(defaultSpeed);
  const [loop, setLoop] = useState(true);
  const intervalRef = useRef<number | null>(null);

  // Auto-play logic with requestAnimationFrame for smooth animation
  useEffect(() => {
    if (isPlaying) {
      const fps = 30; // Target 30 FPS
      const frameTime = (1000 / fps) / playbackSpeed;
      let lastTime = Date.now();

      const animate = () => {
        const now = Date.now();
        const elapsed = now - lastTime;

        if (elapsed >= frameTime) {
          lastTime = now - (elapsed % frameTime);

          // Advance frame
          if (currentFrame < totalFrames - 1) {
            onFrameChange(currentFrame + 1);
          } else if (loop) {
            onFrameChange(0);
          } else {
            setIsPlaying(false);
            return;
          }
        }

        intervalRef.current = requestAnimationFrame(animate);
      };

      intervalRef.current = requestAnimationFrame(animate);
    }

    return () => {
      if (intervalRef.current !== null) {
        cancelAnimationFrame(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isPlaying, currentFrame, totalFrames, playbackSpeed, loop, onFrameChange]);

  const handlePlay = () => setIsPlaying(true);

  const handlePause = () => setIsPlaying(false);

  const handleStop = () => {
    setIsPlaying(false);
    onFrameChange(0);
  };

  const handleStepBackward = () => {
    onFrameChange(Math.max(0, currentFrame - 1));
  };

  const handleStepForward = () => {
    onFrameChange(Math.min(totalFrames - 1, currentFrame + 1));
  };

  const handleSkipBackward = () => {
    const skipAmount = Math.max(1, Math.floor(totalFrames / 10));
    onFrameChange(Math.max(0, currentFrame - skipAmount));
  };

  const handleSkipForward = () => {
    const skipAmount = Math.max(1, Math.floor(totalFrames / 10));
    onFrameChange(Math.min(totalFrames - 1, currentFrame + skipAmount));
  };

  const handleSliderChange = (value: number) => {
    onFrameChange(value);
  };

  const progress = totalFrames > 0 ? (currentFrame / (totalFrames - 1)) * 100 : 0;

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* Main Controls */}
      <Space wrap style={{ width: '100%', justifyContent: 'center' }}>
        <Tooltip title="快退10%">
          <Button
            icon={<FastBackwardOutlined />}
            onClick={handleSkipBackward}
            disabled={currentFrame === 0}
            size="small"
            aria-label="快退10%"
          />
        </Tooltip>

        <Tooltip title="上一帧">
          <Button
            icon={<StepBackwardOutlined />}
            onClick={handleStepBackward}
            disabled={currentFrame === 0}
            aria-label="上一帧"
          />
        </Tooltip>

        {isPlaying ? (
          <Tooltip title="暂停">
            <Button
              icon={<PauseCircleOutlined />}
              onClick={handlePause}
              type="primary"
              size="large"
              aria-label="暂停"
            >
              暂停
            </Button>
          </Tooltip>
        ) : (
          <Tooltip title="播放">
            <Button
              icon={<PlayCircleOutlined />}
              onClick={handlePlay}
              type="primary"
              size="large"
              disabled={currentFrame === totalFrames - 1 && !loop}
              aria-label="播放"
            >
              播放
            </Button>
          </Tooltip>
        )}

        <Tooltip title="重置到第一帧">
          <Button
            icon={<ReloadOutlined />}
            onClick={handleStop}
            aria-label="重置"
          >
            重置
          </Button>
        </Tooltip>

        <Tooltip title="下一帧">
          <Button
            icon={<StepForwardOutlined />}
            onClick={handleStepForward}
            disabled={currentFrame === totalFrames - 1}
            aria-label="下一帧"
          />
        </Tooltip>

        <Tooltip title="快进10%">
          <Button
            icon={<FastForwardOutlined />}
            onClick={handleSkipForward}
            disabled={currentFrame === totalFrames - 1}
            size="small"
            aria-label="快进10%"
          />
        </Tooltip>
      </Space>

      {/* Frame Slider */}
      <div style={{ width: '100%', padding: '0 10px' }}>
        <Slider
          min={0}
          max={totalFrames - 1}
          value={currentFrame}
          onChange={handleSliderChange}
          tooltip={{
            formatter: (value) => `帧 ${(value || 0) + 1}/${totalFrames}`
          }}
          marks={{
            0: '开始',
            [totalFrames - 1]: '结束'
          }}
        />
      </div>

      {/* Settings */}
      <Space wrap style={{ width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <Text>播放速度:</Text>
          <Select
            value={playbackSpeed}
            onChange={setPlaybackSpeed}
            style={{ width: 100 }}
            size="small"
            options={[
              { label: '0.25x', value: 0.25 },
              { label: '0.5x', value: 0.5 },
              { label: '1x', value: 1 },
              { label: '2x', value: 2 },
              { label: '5x', value: 5 },
              { label: '10x', value: 10 },
              { label: '20x', value: 20 }
            ]}
          />
        </Space>

        <Space>
          <Text>循环播放:</Text>
          <Switch checked={loop} onChange={setLoop} size="small" />
        </Space>

        <Text type="secondary">
          帧 <Text strong>{currentFrame + 1}</Text> / {totalFrames} ({progress.toFixed(1)}%)
        </Text>
      </Space>

      {/* Status Bar */}
      {isPlaying && (
        <div style={{
          background: '#e6f7ff',
          border: '1px solid #91d5ff',
          borderRadius: 4,
          padding: '4px 12px',
          textAlign: 'center'
        }}>
          <Text type="secondary">
            🎬 正在播放... 速度: {playbackSpeed}x {loop && '(循环)'}
          </Text>
        </div>
      )}
    </Space>
  );
};

// Memoize to prevent unnecessary re-renders when props haven't changed
// Note: onFrameChange callback should be memoized by parent component
export default memo(AnimationController);
