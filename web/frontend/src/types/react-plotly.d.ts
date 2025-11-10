declare module 'react-plotly.js' {
  import { Component } from 'react';
  import { PlotParams } from 'plotly.js';

  interface PlotProps extends Partial<PlotParams> {
    data: Partial<PlotParams['data']>;
    layout?: Partial<PlotParams['layout']>;
    config?: Partial<PlotParams['config']>;
    frames?: Partial<PlotParams['frames']>;
    onInitialized?: (figure: any, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: any, graphDiv: HTMLElement) => void;
    onPurge?: (figure: any, graphDiv: HTMLElement) => void;
    onError?: (err: any) => void;
    style?: React.CSSProperties;
    className?: string;
    useResizeHandler?: boolean;
    divId?: string;
  }

  export default class Plot extends Component<PlotProps> {}
}
