import { useState } from 'react';
import { CodeEditor } from './components/CodeEditor';
import { DiffView } from './components/DiffView';
import { MergePanel } from './components/MergePanel';
import { ContextView } from './components/ContextView';
import {
  diffCode,
  mergeCode,
  getContext,
} from './services/api';
import type {
  DiffResponse,
  MergeResponse,
  ContextResponse,
  Language,
} from './services/api';
import './App.css';

const SAMPLES = {
  python: {
    base: `"""User management module."""

class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def get_display_name(self) -> str:
        return self.name

    def send_email(self, subject: str, body: str):
        print(f"Sending email to {self.email}")


def create_user(name: str, email: str) -> User:
    return User(name, email)
`,
    target: `"""User management module with authentication."""

class User:
    def __init__(self, name: str, email: str, role: str = "user"):
        self.name = name
        self.email = email
        self.role = role

    def get_display_name(self) -> str:
        return f"{self.name} ({self.role})"

    def send_email(self, subject: str, body: str):
        print(f"Sending email to {self.email}: {subject}")


def create_user(name: str, email: str, role: str = "user") -> User:
    return User(name, email, role)


def authenticate(user: User, password: str) -> bool:
    # New authentication function
    return True
`,
  },
  javascript: {
    base: `// User management module

class User {
  constructor(name, email) {
    this.name = name;
    this.email = email;
  }

  getDisplayName() {
    return this.name;
  }

  sendEmail(subject, body) {
    console.log(\`Sending email to \${this.email}\`);
  }
}

function createUser(name, email) {
  return new User(name, email);
}

export { User, createUser };
`,
    target: `// User management module with authentication

class User {
  constructor(name, email, role = "user") {
    this.name = name;
    this.email = email;
    this.role = role;
  }

  getDisplayName() {
    return \`\${this.name} (\${this.role})\`;
  }

  sendEmail(subject, body) {
    console.log(\`Sending email to \${this.email}: \${subject}\`);
  }

  hasPermission(permission) {
    return this.role === "admin" || permission === "read";
  }
}

function createUser(name, email, role = "user") {
  return new User(name, email, role);
}

async function authenticate(user, password) {
  // New authentication function
  return true;
}

export { User, createUser, authenticate };
`,
  },
};

function App() {
  const [language, setLanguage] = useState<'python' | 'javascript'>('javascript');
  const [baseCode, setBaseCode] = useState(SAMPLES.javascript.base);
  const [targetCode, setTargetCode] = useState(SAMPLES.javascript.target);
  const [mergedCode, setMergedCode] = useState('');

  const [diff, setDiff] = useState<DiffResponse | null>(null);
  const [context, setContext] = useState<ContextResponse | null>(null);
  const [mergeResult, setMergeResult] = useState<MergeResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<'smart' | 'llm_all' | 'auto'>('auto');
  const [awsRegion, setAwsRegion] = useState('us-east-1');
  const [awsAccessKey, setAwsAccessKey] = useState('');
  const [awsSecretKey, setAwsSecretKey] = useState('');
  const [awsSessionToken, setAwsSessionToken] = useState('');
  const [bedrockModelId, setBedrockModelId] = useState('anthropic.claude-3-haiku-20240307-v1:0');
  const [verifySSL, setVerifySSL] = useState(true);

  const handleLanguageChange = (newLang: 'python' | 'javascript') => {
    setLanguage(newLang);
    setBaseCode(SAMPLES[newLang].base);
    setTargetCode(SAMPLES[newLang].target);
    setMergedCode('');
    setDiff(null);
    setContext(null);
    setMergeResult(null);
  };

  const handleCompare = async () => {
    setLoading(true);
    setError(null);
    try {
      const [diffResult, contextResult] = await Promise.all([
        diffCode(baseCode, targetCode, language as Language),
        getContext(baseCode, targetCode, language as Language),
      ]);
      setDiff(diffResult);
      setContext(contextResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compare');
    } finally {
      setLoading(false);
    }
  };

  const handleMerge = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await mergeCode(
        baseCode,
        targetCode,
        strategy,
        language as Language,
        awsRegion || undefined,
        awsAccessKey || undefined,
        awsSecretKey || undefined,
        awsSessionToken || undefined,
        bedrockModelId || undefined,
        verifySSL
      );
      setMergeResult(result);
      if (result.data.merged_code) {
        setMergedCode(result.data.merged_code);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to merge');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>AST Merge Tool</h1>
        <p>Intelligent code merging using Abstract Syntax Trees + AWS Bedrock</p>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="controls">
        <div className="control-group">
          <label>Language:</label>
          <select
            value={language}
            onChange={(e) => handleLanguageChange(e.target.value as 'python' | 'javascript')}
          >
            <option value="javascript">JavaScript</option>
            <option value="python">Python</option>
          </select>
        </div>

        <div className="control-group">
          <label>Strategy:</label>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value as typeof strategy)}
          >
            <option value="auto">Auto (no LLM)</option>
            <option value="smart">Smart (Bedrock for conflicts)</option>
            <option value="llm_all">Bedrock All</option>
          </select>
        </div>

        {strategy !== 'auto' && (
          <>
            <div className="control-group">
              <label>AWS Region:</label>
              <input
                type="text"
                value={awsRegion}
                onChange={(e) => setAwsRegion(e.target.value)}
                placeholder="us-east-1"
              />
            </div>
            <div className="control-group">
              <label>Model:</label>
              <select
                value={bedrockModelId}
                onChange={(e) => setBedrockModelId(e.target.value)}
              >
                <option value="anthropic.claude-3-haiku-20240307-v1:0">Claude 3 Haiku</option>
                <option value="anthropic.claude-3-sonnet-20240229-v1:0">Claude 3 Sonnet</option>
                <option value="anthropic.claude-3-5-sonnet-20240620-v1:0">Claude 3.5 Sonnet</option>
                <option value="anthropic.claude-v2">Claude v2</option>
                <option value="anthropic.claude-instant-v1">Claude Instant</option>
              </select>
            </div>
            <div className="control-group">
              <label>Access Key:</label>
              <input
                type="text"
                value={awsAccessKey}
                onChange={(e) => setAwsAccessKey(e.target.value)}
                placeholder="AKIA..."
              />
            </div>
            <div className="control-group">
              <label>Secret Key:</label>
              <input
                type="password"
                value={awsSecretKey}
                onChange={(e) => setAwsSecretKey(e.target.value)}
                placeholder="Secret key"
              />
            </div>
            <div className="control-group">
              <label>Session Token:</label>
              <input
                type="password"
                value={awsSessionToken}
                onChange={(e) => setAwsSessionToken(e.target.value)}
                placeholder="Optional (for temp creds)"
              />
            </div>
            <div className="control-group">
              <label>
                <input
                  type="checkbox"
                  checked={verifySSL}
                  onChange={(e) => setVerifySSL(e.target.checked)}
                />
                {' '}Verify SSL
              </label>
            </div>
          </>
        )}

        <div className="control-buttons">
          <button onClick={handleCompare} disabled={loading}>
            Compare
          </button>
          <button onClick={handleMerge} disabled={loading} className="primary">
            Merge
          </button>
        </div>
      </div>

      <div className="editor-grid">
        <CodeEditor
          value={baseCode}
          onChange={setBaseCode}
          title="Base Version"
          language={language}
        />
        <CodeEditor
          value={targetCode}
          onChange={setTargetCode}
          title="Target Version"
          language={language}
        />
      </div>

      <div className="results-grid">
        <div className="result-panel">
          <DiffView diff={diff} />
          <ContextView context={context} />
        </div>
        <div className="result-panel">
          <MergePanel result={mergeResult} loading={loading} />
        </div>
      </div>

      {mergedCode && (
        <div className="merged-output">
          <CodeEditor
            value={mergedCode}
            onChange={setMergedCode}
            title="Merged Result"
            height="500px"
            language={language}
          />
        </div>
      )}
    </div>
  );
}

export default App;
