import Editor from '@monaco-editor/react';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
  title: string;
  readOnly?: boolean;
  height?: string;
  language?: 'python' | 'javascript';
}

export function CodeEditor({ value, onChange, title, readOnly = false, height = "400px", language = "javascript" }: CodeEditorProps) {
  return (
    <div className="code-editor">
      <div className="editor-header">
        <h3>{title}</h3>
      </div>
      <Editor
        height={height}
        width="100%"
        language={language}
        theme="vs-dark"
        value={value}
        onChange={(v) => onChange(v || '')}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          wordWrap: 'on',
        }}
      />
    </div>
  );
}
