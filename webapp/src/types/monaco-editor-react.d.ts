declare module '@monaco-editor/react' {
  import * as React from 'react';

  export type OnMount = (editor: any, monaco: any) => void;
  export type OnChange = (value: string | undefined, ev: any) => void;

  interface EditorProps {
    height?: string | number;
    width?: string | number;
    defaultLanguage?: string;
    defaultValue?: string;
    value?: string;
    language?: string;
    theme?: string;
    options?: Record<string, any>;
    onChange?: OnChange;
    onMount?: OnMount;
    [key: string]: any;
  }

  const Editor: React.FC<EditorProps>;
  export default Editor;
}
