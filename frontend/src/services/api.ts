import axios from 'axios';

const API_BASE = 'http://localhost:8001';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export type Language = 'python' | 'javascript' | null;

export interface ParseResponse {
  success: boolean;
  data: {
    source: string;
    nodes: Record<string, NodeInfo>;
    imports: string[];
  };
  detected_language: string;
}

export interface NodeInfo {
  name: string;
  node_type: string;
  start_line: number;
  end_line: number;
  source: string;
  signature: string;
  parent: string | null;
  dependencies: string[];
  children: string[];
}

export interface DiffResponse {
  success: boolean;
  data: {
    changes: ChangeInfo[];
    added_count: number;
    removed_count: number;
    modified_count: number;
    unchanged_count: number;
    summary: {
      total_changes: number;
      has_conflicts: boolean;
    };
  };
  detected_language: string;
}

export interface ChangeInfo {
  name: string;
  change_type: 'added' | 'removed' | 'modified' | 'unchanged';
  base_node: NodeInfo | null;
  target_node: NodeInfo | null;
}

export interface ContextResponse {
  success: boolean;
  data: {
    contexts: MergeContextInfo[];
    total_tokens_estimate: number;
    context_count: number;
  };
  detected_language: string;
}

export interface MergeContextInfo {
  change: ChangeInfo;
  related_nodes: NodeInfo[];
  import_context: string[];
}

export interface MergeResponse {
  success: boolean;
  data: {
    success: boolean;
    merged_code: string;
    decisions: MergeDecision[];
    conflicts_resolved: number;
    auto_merged: number;
    error: string | null;
  };
}

export interface MergeDecision {
  node_name: string;
  action: string;
  merged_code: string | null;
  reason: string;
}

export const parseCode = async (code: string, language?: Language): Promise<ParseResponse> => {
  const response = await api.post<ParseResponse>('/parse', { code, language });
  return response.data;
};

export const diffCode = async (
  baseCode: string,
  targetCode: string,
  language?: Language
): Promise<DiffResponse> => {
  const response = await api.post<DiffResponse>('/diff', {
    base_code: baseCode,
    target_code: targetCode,
    language,
  });
  return response.data;
};

export const getContext = async (
  baseCode: string,
  targetCode: string,
  language?: Language,
  includeUnchanged = false
): Promise<ContextResponse> => {
  const response = await api.post<ContextResponse>('/context', {
    base_code: baseCode,
    target_code: targetCode,
    language,
    include_unchanged: includeUnchanged,
  });
  return response.data;
};

export const mergeCode = async (
  baseCode: string,
  targetCode: string,
  strategy: 'smart' | 'llm_all' | 'auto' = 'auto',
  language?: Language,
  awsRegion?: string,
  awsAccessKey?: string,
  awsSecretKey?: string,
  awsSessionToken?: string,
  bedrockModelId?: string,
  verifySSL: boolean = true
): Promise<MergeResponse> => {
  const response = await api.post<MergeResponse>('/merge', {
    base_code: baseCode,
    target_code: targetCode,
    strategy,
    language,
    aws_region: awsRegion,
    aws_access_key: awsAccessKey,
    aws_secret_key: awsSecretKey,
    aws_session_token: awsSessionToken,
    bedrock_model_id: bedrockModelId,
    verify_ssl: verifySSL,
  });
  return response.data;
};

export default api;
