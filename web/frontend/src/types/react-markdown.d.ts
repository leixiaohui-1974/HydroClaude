declare module 'react-markdown' {
  import { FC, ReactNode } from 'react';

  interface ReactMarkdownProps {
    children: string;
    className?: string;
    remarkPlugins?: any[];
    rehypePlugins?: any[];
    components?: Record<string, any>;
  }

  const ReactMarkdown: FC<ReactMarkdownProps>;
  export default ReactMarkdown;
}
