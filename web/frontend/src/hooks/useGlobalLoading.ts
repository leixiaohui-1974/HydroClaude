/**
 * Global Loading State Hook
 * 全局加载状态Hook
 *
 * v1.5.0 Feature: UI/UX Enhancement
 */

import { useState, useCallback, useRef } from 'react';
import { message } from 'antd';

interface LoadingTask {
  id: string;
  message?: string;
  timestamp: number;
}

/**
 * Global Loading Hook
 * 全局加载Hook
 *
 * Manages global loading state with support for multiple concurrent tasks
 */
export function useGlobalLoading() {
  const [tasks, setTasks] = useState<LoadingTask[]>([]);
  const taskIdCounter = useRef(0);

  /**
   * Start a loading task
   * 开始加载任务
   */
  const startLoading = useCallback((loadingMessage?: string): string => {
    const taskId = `task-${++taskIdCounter.current}-${Date.now()}`;

    setTasks(prev => [
      ...prev,
      {
        id: taskId,
        message: loadingMessage,
        timestamp: Date.now()
      }
    ]);

    return taskId;
  }, []);

  /**
   * Stop a loading task
   * 停止加载任务
   */
  const stopLoading = useCallback((taskId: string) => {
    setTasks(prev => prev.filter(task => task.id !== taskId));
  }, []);

  /**
   * Clear all loading tasks
   * 清除所有加载任务
   */
  const clearAllLoading = useCallback(() => {
    setTasks([]);
  }, []);

  /**
   * Execute async operation with loading
   * 执行异步操作并显示加载状态
   */
  const withLoading = useCallback(async <T,>(
    operation: () => Promise<T>,
    loadingMessage?: string
  ): Promise<T> => {
    const taskId = startLoading(loadingMessage);

    try {
      const result = await operation();
      stopLoading(taskId);
      return result;
    } catch (error) {
      stopLoading(taskId);
      throw error;
    }
  }, [startLoading, stopLoading]);

  // Is any task loading
  const isLoading = tasks.length > 0;

  // Get current loading message
  const currentMessage = tasks.length > 0 ? tasks[tasks.length - 1].message : undefined;

  return {
    isLoading,
    currentMessage,
    tasks,
    startLoading,
    stopLoading,
    clearAllLoading,
    withLoading
  };
}

/**
 * Enhanced notification utilities
 * 增强的通知工具
 */
export const notification = {
  /**
   * Show success message
   * 显示成功消息
   */
  success: (content: string, duration = 3) => {
    message.success(content, duration);
  },

  /**
   * Show error message
   * 显示错误消息
   */
  error: (content: string, duration = 5) => {
    message.error(content, duration);
  },

  /**
   * Show warning message
   * 显示警告消息
   */
  warning: (content: string, duration = 4) => {
    message.warning(content, duration);
  },

  /**
   * Show info message
   * 显示信息消息
   */
  info: (content: string, duration = 3) => {
    message.info(content, duration);
  },

  /**
   * Show loading message
   * 显示加载消息
   */
  loading: (content: string, duration = 0) => {
    return message.loading(content, duration);
  },

  /**
   * Destroy all messages
   * 销毁所有消息
   */
  destroy: () => {
    message.destroy();
  }
};

/**
 * Execute operation with loading and error handling
 * 执行操作并显示加载和错误处理
 */
export async function executeWithFeedback<T>(
  operation: () => Promise<T>,
  options: {
    loadingMessage?: string;
    successMessage?: string;
    errorMessage?: string;
    onError?: (error: Error) => void;
  } = {}
): Promise<T | null> {
  const {
    loadingMessage = '处理中...',
    successMessage,
    errorMessage = '操作失败',
    onError
  } = options;

  // Show loading
  const hideLoading = notification.loading(loadingMessage);

  try {
    // Execute operation
    const result = await operation();

    // Hide loading
    hideLoading();

    // Show success message if provided
    if (successMessage) {
      notification.success(successMessage);
    }

    return result;
  } catch (error) {
    // Hide loading
    hideLoading();

    // Show error message
    const errorMsg = error instanceof Error ? error.message : String(error);
    notification.error(`${errorMessage}: ${errorMsg}`);

    // Call error handler if provided
    if (onError && error instanceof Error) {
      onError(error);
    }

    return null;
  }
}
