import type { MergeResponse, MergeDecision } from '../services/api';

interface MergePanelProps {
  result: MergeResponse | null;
  loading: boolean;
}

export function MergePanel({ result, loading }: MergePanelProps) {
  if (loading) {
    return (
      <div className="merge-panel loading">
        <div className="spinner"></div>
        <p>Merging code...</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="merge-panel empty">
        <p>Click "Merge" to combine the code versions</p>
      </div>
    );
  }

  const { data } = result;

  const getActionClass = (action: string) => {
    switch (action) {
      case 'keep_base': return 'action-base';
      case 'keep_target': return 'action-target';
      case 'merge': return 'action-merge';
      case 'remove': return 'action-remove';
      default: return '';
    }
  };

  const getActionLabel = (action: string) => {
    switch (action) {
      case 'keep_base': return 'Kept Base';
      case 'keep_target': return 'Kept Target';
      case 'merge': return 'LLM Merged';
      case 'remove': return 'Removed';
      default: return action;
    }
  };

  return (
    <div className="merge-panel">
      <div className="merge-stats">
        <span className="stat">Auto-merged: {data.auto_merged}</span>
        <span className="stat">Conflicts resolved: {data.conflicts_resolved}</span>
      </div>

      {data.error && (
        <div className="merge-error">
          Error: {data.error}
        </div>
      )}

      <div className="merge-decisions">
        <h4>Merge Decisions</h4>
        {data.decisions
          .filter(d => d.action !== 'keep_base' || d.reason !== 'Unchanged')
          .slice(0, 20)
          .map((decision: MergeDecision, idx: number) => (
            <div key={idx} className={`decision-item ${getActionClass(decision.action)}`}>
              <span className="decision-name">{decision.node_name}</span>
              <span className="decision-action">{getActionLabel(decision.action)}</span>
              <span className="decision-reason">{decision.reason}</span>
            </div>
          ))}
      </div>
    </div>
  );
}
