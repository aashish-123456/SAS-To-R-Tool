import React from 'react';
import { useNavigate, useParams, Routes, Route } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Upload, Code2, Play, CheckCircle2, Download } from 'lucide-react';
import { projectsApi } from '@/services/api';
import UploadStep from './workflow/UploadStep';
import InputPreviewStep from './workflow/InputPreviewStep';
import TranslationStep from './workflow/TranslationStep';
import ExecutionStep from './workflow/ExecutionStep';
import ValidationStep from './workflow/ValidationStep';
import ReportStep from './workflow/ReportStep';

const steps = [
  { id: 'upload', label: 'Upload', fullLabel: 'Upload SAS Inputs', icon: Upload, path: 'upload' },
  { id: 'preview', label: 'Preview', fullLabel: 'Input Validation Preview', icon: Code2, path: 'preview-input' },
  { id: 'translation', label: 'Translate', fullLabel: 'SAS to R Translation', icon: Code2, path: 'translation' },
  { id: 'execution', label: 'Execute', fullLabel: 'Dual Runtime Execution', icon: Play, path: 'execution' },
  { id: 'validation', label: 'Validate', fullLabel: 'Output Reconciliation', icon: CheckCircle2, path: 'validation' },
  { id: 'report', label: 'Export', fullLabel: 'Export R Script', icon: Download, path: 'report' },
];

const ProjectWorkflow: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: project } = useQuery({ queryKey: ['project', projectId], queryFn: () => projectsApi.getById(projectId!), enabled: !!projectId });

  const getCurrentStepIndex = () => {
    const path = window.location.pathname;
    const idx = steps.findIndex((s) => path.includes(s.path));
    return idx === -1 ? 0 : idx;
  };
  const currentStepIndex = getCurrentStepIndex();

  return (
    <div className="fade-in space-y-5">
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight truncate">{project?.name || 'Project Workflow'}</h1>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
        <div className="flex items-start">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isActive = index === currentStepIndex;
            const isCompleted = index < currentStepIndex;
            return (
              <React.Fragment key={step.id}>
                <button type="button" onClick={() => navigate(`/projects/${projectId}/${step.path}`)} className="flex flex-col items-center gap-2 relative group cursor-pointer flex-shrink-0 focus:outline-none">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all shadow-sm ${isActive ? 'bg-[#1f4368] text-white ring-4 ring-[#ccdce9]' : isCompleted ? 'bg-emerald-500 text-white hover:bg-emerald-600' : 'bg-slate-100 text-slate-400 hover:bg-slate-200'}`}>
                    <Icon className="w-[18px] h-[18px]" />
                  </div>
                  <span className={`text-[11px] font-semibold text-center leading-tight select-none ${isActive ? 'text-[#1f4368]' : isCompleted ? 'text-emerald-600' : 'text-slate-400'}`}>
                    {step.label}
                  </span>
                </button>
                {index < steps.length - 1 && (
                  <div className="flex-1 px-3 mt-5">
                    <div className={`h-0.5 rounded-full transition-colors duration-300 ${index < currentStepIndex ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      <Routes>
        <Route path="upload" element={<UploadStep />} />
        <Route path="preview-input" element={<InputPreviewStep />} />
        <Route path="translation" element={<TranslationStep />} />
        <Route path="execution" element={<ExecutionStep />} />
        <Route path="validation" element={<ValidationStep />} />
        <Route path="report" element={<ReportStep />} />
        <Route path="*" element={<UploadStep />} />
      </Routes>
    </div>
  );
};

export default ProjectWorkflow;
