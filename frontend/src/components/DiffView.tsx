import type { DiffResponse, ChangeInfo } from '../services/api';

interface DiffViewProps {
  diff: DiffResponse | null;
  onSelectChange?: (change: ChangeInfo) => void;
}

export function DiffView({ diff, onSelectChange }: DiffViewProps) {
  if (!diff) {
    return (
      <div className="diff-view empty">
        <p>Click "Compare" to see differences</p>
      </div>
    );
  }

  const { data } = diff;

  const getChangeIcon = (type: string) => {
    switch (type) {
      case 'added': return '+';
      case 'removed': return '-';
      case 'modified': return '~';
      default: return '=';
    }
  };

  const getChangeClass = (type: string) => {
    switch (type) {
      case 'added': return 'change-added';
      case 'removed': return 'change-removed';
      case 'modified': return 'change-modified';
      default: return 'change-unchanged';
    }
  };

  return (
    <div className="diff-view">
      <div className="diff-summary">
        <span className="stat added">+{data.added_count} added</span>
        <span className="stat removed">-{data.removed_count} removed</span>
        <span className="stat modified">~{data.modified_count} modified</span>
        <span className="stat unchanged">={data.unchanged_count} unchanged</span>
      </div>

      <div className="diff-changes">
        {data.changes
          .filter(c => c.change_type !== 'unchanged')
          .map((change, idx) => (
            <div
              key={idx}
              className={`change-item ${getChangeClass(change.change_type)}`}
              onClick={() => onSelectChange?.(change)}
            >
              <span className="change-icon">{getChangeIcon(change.change_type)}</span>
              <span className="change-name">{change.name}</span>
              <span className="change-type">
                {(change.base_node || change.target_node)?.node_type}
              </span>
            </div>
          ))}
      </div>

      {data.summary.has_conflicts && (
        <div className="conflict-warning">
          Conflicts detected - LLM merge recommended
        </div>
      )}
    </div>
  );
}
