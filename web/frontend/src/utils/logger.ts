/**
 * Logger Utility
 *
 * Provides centralized logging with different severity levels.
 * In production, errors can be sent to monitoring services like Sentry.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  [key: string]: any;
}

class Logger {
  private isDevelopment: boolean;
  private enableSentry: boolean;

  constructor() {
    this.isDevelopment = import.meta.env.DEV;
    this.enableSentry = import.meta.env.VITE_ENABLE_SENTRY === 'true';
  }

  /**
   * Log debug information (development only)
   */
  debug(message: string, context?: LogContext): void {
    if (this.isDevelopment) {
      console.debug(`[DEBUG] ${message}`, context || '');
    }
  }

  /**
   * Log informational messages (development only)
   */
  info(message: string, context?: LogContext): void {
    if (this.isDevelopment) {
      console.info(`[INFO] ${message}`, context || '');
    }
  }

  /**
   * Log warning messages
   */
  warn(message: string, context?: LogContext): void {
    console.warn(`[WARN] ${message}`, context || '');

    // In production with Sentry enabled, could send warnings
    if (!this.isDevelopment && this.enableSentry) {
      // TODO: Integrate with Sentry
      // Sentry.captureMessage(message, 'warning');
    }
  }

  /**
   * Log error messages and send to monitoring service
   */
  error(message: string, error?: Error, context?: LogContext): void {
    console.error(`[ERROR] ${message}`, error || '', context || '');

    // In production with Sentry enabled, send errors to monitoring
    if (!this.isDevelopment && this.enableSentry) {
      // TODO: Integrate with Sentry
      // Sentry.captureException(error || new Error(message), {
      //   extra: context
      // });
    }
  }

  /**
   * Log API errors with specific formatting
   */
  apiError(endpoint: string, status: number, message: string, context?: LogContext): void {
    const errorMessage = `API Error [${status}] ${endpoint}: ${message}`;
    this.error(errorMessage, undefined, {
      endpoint,
      status,
      ...context
    });
  }

  /**
   * Log performance metrics
   */
  performance(metric: string, duration: number, context?: LogContext): void {
    if (this.isDevelopment) {
      console.log(`[PERF] ${metric}: ${duration.toFixed(2)}ms`, context || '');
    }
  }
}

// Export singleton instance
export const logger = new Logger();

// Export type for external use
export type { LogLevel, LogContext };
