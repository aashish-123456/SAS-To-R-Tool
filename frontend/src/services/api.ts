import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin);

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
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
}

export interface TranslationStatus {
  status: string;
  progress: number;
  r_code_preview?: string;
  warnings: string[];
}

export interface ValidationResult {
  overall_match: number;
  structure_match: boolean;
  value_discrepancies: number;
  statistics: any;
  issues?: Array<{
    severity: 'warning' | 'error' | 'info';
    title: string;
    detail: string;
  }>;
}

export interface FeedbackRequest {
  project_id: string;
  translation_id: string;
  is_correct: boolean;
  corrections?: any;
  error_type?: string;
  user_notes?: string;
}

// Projects API
export const projectsApi = {
  getAll: async (): Promise<Project[]> => {
    const response = await api.get('/projects');
    return response.data;
  },

  getById: async (id: string): Promise<Project> => {
    const response = await api.get(`/projects/${id}`);
    return response.data;
  },

  create: async (data: { name: string; description?: string }): Promise<Project> => {
    const response = await api.post('/projects', data);
    return response.data;
  },

  uploadFiles: async (projectId: string, sasCode: File, datasets?: File[]) => {
    const formData = new FormData();
    formData.append('sas_code', sasCode);
    if (datasets) {
      datasets.forEach((file) => {
        formData.append('datasets', file);
      });
    }

    const response = await api.post(`/projects/${projectId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  startTranslation: async (projectId: string) => {
    const response = await api.post(`/projects/${projectId}/translate`);
    return response.data;
  },

  getTranslationStatus: async (projectId: string): Promise<TranslationStatus> => {
    const response = await api.get(`/projects/${projectId}/translation/status`);
    return response.data;
  },

  startExecution: async (projectId: string): Promise<{
    job_id: string;
    status: string;
    message: string;
    sas_output: { status: string; logs: string[]; output: string };
    r_output: { status: string; logs: string[]; output: string; r_available: boolean };
  }> => {
    const response = await api.post(`/projects/${projectId}/execute`);
    return response.data;
  },

  getValidation: async (projectId: string): Promise<ValidationResult> => {
    const response = await api.get(`/projects/${projectId}/validation`);
    return response.data;
  },

  submitFeedback: async (feedback: FeedbackRequest) => {
    const response = await api.post('/feedback', feedback);
    return response.data;
  },

  autoCorrect: async (projectId: string) => {
    const response = await api.post(`/auto-correct/${projectId}`);
    return response.data;
  },

  getRCodeDownloadUrl: (projectId: string) => {
    return `${API_BASE_URL}/api/v1/projects/${projectId}/download/r-code`;
  },

  getRCode: async (projectId: string): Promise<{ r_code: string }> => {
    const response = await api.get(`/projects/${projectId}/r-code`);
    return response.data;
  },

  getExecutionOutput: async (projectId: string): Promise<{
    sas_output: { status: string; output: string; logs: string[]; datasets: any };
    r_output: { status: string; output: string; logs: string[]; r_available: boolean; errors?: string };
  }> => {
    const response = await api.get(`/projects/${projectId}/execution/output`);
    return response.data;
  },
};

export default api;
