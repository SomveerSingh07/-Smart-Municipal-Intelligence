export interface Complaint {
  id: number;
  tracking_id: string;
  text: string;
  language: string;
  category: string;
  category_confidence: number;
  category_reason?: string;
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
  priority_confidence: number;
  priority_reasons: string[];
  status: 'Submitted' | 'Assigned' | 'In Progress' | 'Resolved' | 'Closed';
  latitude?: number;
  longitude?: number;
  address_text?: string;
  citizen_name?: string;
  citizen_phone?: string;
  department_name?: string;
  cluster_size?: number;
  sla_due_at?: string;
  created_at: string;
}

export interface KPISummary {
  total_complaints: number;
  open_complaints: number;
  resolved_complaints: number;
  overdue_complaints: number;
  avg_resolution_hours: number;
  sla_compliance_rate: number;
  duplicate_clusters_count: number;
}

export interface RAGCitation {
  document_title: string;
  page: number;
  section?: string;
  snippet: string;
}

export interface RAGResponse {
  answer: string;
  confidence: number;
  citations: RAGCitation[];
  has_sufficient_info: boolean;
}
