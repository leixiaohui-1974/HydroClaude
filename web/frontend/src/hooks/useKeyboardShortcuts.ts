/**
 * Keyboard Shortcuts Hook
 * 键盘快捷键Hook
 *
 * v1.5.0 Feature: UI/UX Enhancement
 */

import { useEffect, useCallback, useRef } from 'react';

/**
 * Keyboard shortcut configuration
 * 快捷键配置
 */
export interface ShortcutConfig {
  /**
   * Key combination (e.g., 'ctrl+s', 'meta+n', 'esc')
   * 键组合
   */
  key: string;

  /**
   * Handler function
   * 处理函数
   */
  handler: (event: KeyboardEvent) => void;

  /**
   * Description for display
   * 描述（用于显示）
   */
  description?: string;

  /**
   * Prevent default browser behavior
   * 阻止浏览器默认行为
   */
  preventDefault?: boolean;

  /**
   * Only active when condition is true
   * 仅在条件为真时激活
   */
  enabled?: boolean;
}

/**
 * Parse key combination string
 * 解析键组合字符串
 */
function parseKeyCombo(combo: string): {
  ctrl: boolean;
  shift: boolean;
  alt: boolean;
  meta: boolean;
  key: string;
} {
  const parts = combo.toLowerCase().split('+');
  const modifiers = {
    ctrl: false,
    shift: false,
    alt: false,
    meta: false,
    key: ''
  };

  parts.forEach(part => {
    if (part === 'ctrl' || part === 'control') {
      modifiers.ctrl = true;
    } else if (part === 'shift') {
      modifiers.shift = true;
    } else if (part === 'alt') {
      modifiers.alt = true;
    } else if (part === 'meta' || part === 'cmd' || part === 'command') {
      modifiers.meta = true;
    } else {
      modifiers.key = part;
    }
  });

  return modifiers;
}

/**
 * Check if event matches key combination
 * 检查事件是否匹配键组合
 */
function matchesKeyCombo(event: KeyboardEvent, combo: string): boolean {
  const parsed = parseKeyCombo(combo);
  const eventKey = event.key.toLowerCase();

  // Check modifiers
  if (parsed.ctrl !== event.ctrlKey) return false;
  if (parsed.shift !== event.shiftKey) return false;
  if (parsed.alt !== event.altKey) return false;
  if (parsed.meta !== event.metaKey) return false;

  // Check key
  // Handle special keys
  const specialKeys: Record<string, string> = {
    'escape': 'escape',
    'esc': 'escape',
    'space': ' ',
    'enter': 'enter',
    'return': 'enter',
    'tab': 'tab',
    'backspace': 'backspace',
    'delete': 'delete',
    'arrowup': 'arrowup',
    'arrowdown': 'arrowdown',
    'arrowleft': 'arrowleft',
    'arrowright': 'arrowright'
  };

  const normalizedKey = specialKeys[parsed.key] || parsed.key;
  return eventKey === normalizedKey;
}

/**
 * Keyboard Shortcuts Hook
 * 键盘快捷键Hook
 *
 * @param shortcuts - Array of shortcut configurations
 * @param deps - Dependency array (optional)
 *
 * @example
 * ```tsx
 * useKeyboardShortcuts([
 *   {
 *     key: 'ctrl+s',
 *     handler: () => saveModel(),
 *     description: 'Save model',
 *     preventDefault: true
 *   },
 *   {
 *     key: 'esc',
 *     handler: () => closeModal(),
 *     enabled: isModalOpen
 *   }
 * ]);
 * ```
 */
export function useKeyboardShortcuts(
  shortcuts: ShortcutConfig[],
  deps: React.DependencyList = []
): void {
  // Store shortcuts in ref to avoid recreating listener
  const shortcutsRef = useRef<ShortcutConfig[]>(shortcuts);

  // Update ref when shortcuts change
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts, ...deps]);

  // Keyboard event handler
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Don't trigger shortcuts when typing in input fields
    const target = event.target as HTMLElement;
    if (
      target.tagName === 'INPUT' ||
      target.tagName === 'TEXTAREA' ||
      target.isContentEditable
    ) {
      // Allow Esc to work even in input fields
      if (event.key !== 'Escape') {
        return;
      }
    }

    // Check each shortcut
    for (const shortcut of shortcutsRef.current) {
      // Skip if disabled
      if (shortcut.enabled === false) {
        continue;
      }

      // Check if key matches
      if (matchesKeyCombo(event, shortcut.key)) {
        // Prevent default if specified
        if (shortcut.preventDefault !== false) {
          event.preventDefault();
        }

        // Call handler
        shortcut.handler(event);
        break; // Only handle first match
      }
    }
  }, []);

  // Register global listener
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);
}

/**
 * Get platform-specific modifier key name
 * 获取平台特定的修饰键名称
 */
export function getModifierKeyName(): string {
  // Detect macOS
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  return isMac ? 'Cmd' : 'Ctrl';
}

/**
 * Format shortcut for display
 * 格式化快捷键用于显示
 *
 * @example
 * formatShortcut('ctrl+s') => 'Ctrl+S' (Windows/Linux)
 * formatShortcut('ctrl+s') => 'Cmd+S' (macOS)
 */
export function formatShortcut(combo: string): string {
  const parsed = parseKeyCombo(combo);
  const parts: string[] = [];

  if (parsed.ctrl || parsed.meta) {
    parts.push(getModifierKeyName());
  }
  if (parsed.shift) {
    parts.push('Shift');
  }
  if (parsed.alt) {
    parts.push('Alt');
  }

  // Capitalize key
  const keyDisplay = parsed.key.charAt(0).toUpperCase() + parsed.key.slice(1);
  parts.push(keyDisplay);

  return parts.join('+');
}

/**
 * Default application shortcuts
 * 默认应用快捷键
 */
export const DEFAULT_SHORTCUTS = {
  SAVE: 'ctrl+s',
  EXPORT: 'ctrl+e',
  NEW: 'ctrl+n',
  OPEN: 'ctrl+o',
  UNDO: 'ctrl+z',
  REDO: 'ctrl+y',
  CLOSE: 'esc',
  PLAY_PAUSE: 'space',
  HELP: 'f1'
} as const;
