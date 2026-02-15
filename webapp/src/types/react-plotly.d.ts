declare module 'react-plotly.js' {
  import { Component } from 'react';

  interface PlotParams {
    data: any[];
    layout?: any;
    config?: any;
    style?: React.CSSProperties;
    className?: string;
    useResizeHandler?: boolean;
    onInitialized?: (figure: any, graphDiv: any) => void;
    onUpdate?: (figure: any, graphDiv: any) => void;
    onHover?: (event: any) => void;
    onClick?: (event: any) => void;
    onSelected?: (event: any) => void;
    onRelayout?: (event: any) => void;
    revision?: number;
  }

  class Plot extends Component<PlotParams> {}
  export default Plot;
}
