import type { ContextResponse } from '../services/api';

interface ContextViewProps {
  context: ContextResponse | null;
}

export function ContextView({ context }: ContextViewProps) {
  if (!context) {
    return null;
  }

  const { data } = context;

  return (
    <div className="context-view">
      <div className="context-header">
        <h4>LLM Context Preview</h4>
        <span className="token-estimate">
          ~{data.total_tokens_estimate} tokens estimated
        </span>
      </div>

      <div className="context-summary">
        <p>
          {data.context_count} change(s) extracted for merge context.
          This is what will be sent to the LLM instead of the full files.
        </p>
      </div>

      <div className="context-items">
        {data.contexts.slice(0, 5).map((ctx, idx) => (
          <div key={idx} className="context-item">
            <div className="context-item-header">
              <span className={`change-type ${ctx.change.change_type}`}>
                {ctx.change.change_type}
              </span>
              <span className="change-name">{ctx.change.name}</span>
            </div>

            {ctx.related_nodes.length > 0 && (
              <div className="related-context">
                <small>Related: {ctx.related_nodes.map(n => n.name).join(', ')}</small>
              </div>
            )}

            {ctx.import_context.length > 0 && (
              <div className="import-context">
                <small>Imports: {ctx.import_context.join(', ')}</small>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
