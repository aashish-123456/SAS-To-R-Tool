import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin);

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  sas_code?: string;
  sas_file_id?: string;
  dataset_files?: string[];
  translation_id?: string;
  execution_id?: string;
  validation_id?: string;
  report_id?: string;
  generated_r_code_id?: string;
  validation_report_id?: string;
  // enriched fields added after translation / validation
  r_lines?: number;
  sas_lines?: number;
  warnings_count?: number;
  translated_at?: string;
  overall_confidence?: number;
  confidence_label?: string;
  issues_count?: { critical: number; major: number; minor: number };
  datasets_validated?: number;
  procedures_validated?: number;
}
export interface TranslationStatus { status: string; progress: number; r_code_preview?: string; warnings: string[]; engine_results?: Record<string, any>; }
export interface ValidationScenario {
  id: string;
  category: 'structural' | 'functional' | 'statistical' | 'execution' | 'semantic';
  name: string;
  description: string;
  sas_result: string;
  r_result: string;
  status: 'passed' | 'warning' | 'failed';
  impact: number;
  sas_code?: string;
  r_code?: string;
  detail?: string;
}
export interface ValidationIssue {
  severity: 'critical' | 'major' | 'minor';
  title: string;
  detail: string;
  suggestion: string;
  category: string;
}
export interface CategoryScore {
  name: string;
  display_name: string;
  score: number;
  weight: number;
  scenarios_passed: number;
  scenarios_total: number;
}
export interface ValidationEngine {
  name: string;
  description: string;
  status: 'completed' | 'warning' | 'failed';
  scenarios_passed: number;
  scenarios_total: number;
}
export interface ValidationResult {
  // backward-compat
  overall_match: number;
  structure_match: boolean;
  value_discrepancies: number;
  statistics: any;
  // rich semantic fields
  validation_id?: string;
  overall_confidence?: number;
  confidence_label?: string;
  datasets_validated?: number;
  datasets_matched?: number;
  datasets_mismatched?: number;
  procedures_validated?: number;
  procedures_matched?: number;
  procedures_mismatched?: number;
  issues?: ValidationIssue[];
  category_scores?: CategoryScore[];
  engines?: ValidationEngine[];
  scenarios?: ValidationScenario[];
  recommendations?: string[];
  sas_output_preview?: string;
  r_output_preview?: string;
}
export interface FeedbackRequest { project_id: string; translation_id: string; is_correct: boolean; corrections?: any; error_type?: string; user_notes?: string; }
export interface UserProfile { name: string; email: string; profile_photo?: string; }

export const projectsApi = {
  getAll: async (): Promise<Project[]> => (await api.get('/projects')).data,
  getById: async (id: string): Promise<Project> => (await api.get(`/projects/${id}`)).data,
  create: async (data: { name: string; description?: string }): Promise<Project> => (await api.post('/projects', data)).data,
  uploadFiles: async (projectId: string, sasCode: File, datasets?: File[]) => {
    const formData = new FormData();
    formData.append('sas_code', sasCode);
    if (datasets) datasets.forEach((file) => formData.append('datasets', file));
    return (await api.post(`/projects/${projectId}/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } })).data;
  },
  startTranslation: async (projectId: string) => (await api.post(`/projects/${projectId}/translate`)).data,
  getTranslationStatus: async (projectId: string): Promise<TranslationStatus> => (await api.get(`/projects/${projectId}/translation/status`)).data,
  startExecution: async (projectId: string) => (await api.post(`/projects/${projectId}/execute`)).data,
  getValidation: async (projectId: string): Promise<ValidationResult> => (await api.get(`/projects/${projectId}/validation`)).data,
  submitFeedback: async (feedback: FeedbackRequest) => (await api.post('/feedback', feedback)).data,
  autoCorrect: async (projectId: string) => (await api.post(`/auto-correct/${projectId}`)).data,
  getRCodeDownloadUrl: (projectId: string) => `${API_BASE_URL}/api/v1/projects/${projectId}/download/r-code`,
  getRCode: async (projectId: string): Promise<{ r_code: string }> => (await api.get(`/projects/${projectId}/r-code`)).data,
  getExecutionOutput: async (projectId: string) => (await api.get(`/projects/${projectId}/execution/output`)).data,
};

export const authApi = {
  signup: async (payload: { name: string; email: string; username: string; password: string }) => (await api.post('/auth/signup', payload)).data,
  login: async (payload: { username: string; password: string }) => (await api.post('/auth/login', payload)).data,
  verifyOtp: async (payload: { email: string; otp: string }) => (await api.post('/auth/verify-otp', payload)).data,
  forgotPassword: async (payload: { email: string }) => (await api.post('/auth/forgot-password', payload)).data,
  resetPassword: async (payload: { email: string; otp: string; new_password: string }) => (await api.post('/auth/reset-password', payload)).data,
  getProfile: async (): Promise<UserProfile> => (await api.get('/auth/me')).data,
  changePassword: async (payload: { current_password: string; new_password: string }) => (await api.post('/auth/change-password', payload)).data,
  logout: async () => (await api.post('/auth/logout')).data,
};

export default api;
