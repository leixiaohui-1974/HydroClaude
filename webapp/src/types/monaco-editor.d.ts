declare module 'monaco-editor' {
  export namespace editor {
    interface IStandaloneCodeEditor {
      getValue(): string;
      setValue(value: string): void;
      getAction(id: string): { run(): Promise<void> } | null;
      addCommand(keybinding: number, handler: () => void): void;
      [key: string]: any;
    }
  }
}
