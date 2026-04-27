import React from 'react';
import { useNavigate, useParams, Routes, Route } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Upload, Code2, Play, CheckCircle2, Download } from 'lucide-react';
import { projectsApi } from '@/services/api';
import UploadStep from './workflow/UploadStep';
import TranslationStep from './workflow/TranslationStep';
import ExecutionStep from './workflow/ExecutionStep';
import ValidationStep from './workflow/ValidationStep';
import ReportStep from './workflow/ReportStep';

const steps = [
  { id: 'upload',      label: 'Upload',    fullLabel: 'Upload SAS Inputs',       icon: Upload,       path: 'upload' },
  { id: 'translation', label: 'Translate', fullLabel: 'SAS → R Translation',     icon: Code2,        path: 'translation' },
  { id: 'execution',   label: 'Execute',   fullLabel: 'Dual Runtime Execution',   icon: Play,         path: 'execution' },
  { id: 'validation',  label: 'Validate',  fullLabel: 'Output Reconciliation',    icon: CheckCircle2, path: 'validation' },
  { id: 'report',      label: 'Export',    fullLabel: 'Export R Script',          icon: Download,     path: 'report' },
];

const ProjectWorkflow: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.getById(projectId!),
    enabled: !!projectId,
  });

  const getFileName = (filePath?: string) =>
    filePath ? filePath.replace(/\\/g, '/').split('/').pop() ?? filePath : '';

  const getOriginalName = (filePath?: string) => {
    const stored = getFileName(filePath);
    if (!stored) return '';
    const m = stored.match(/^.+_(sas|dataset)_[0-9a-fA-F-]{36}_(.+)$/);
    return m?.[2] ?? stored;
  };

  const stripExt = (name?: string) => {
    if (!name) return '';
    const dot = name.lastIndexOf('.');
    return dot > 0 ? name.slice(0, dot) : name;
  };

  const getTooltipLines = (stepId: string): string[] => {
    if (!project) return ['Loading…'];
    switch (stepId) {
      case 'upload': {
        const sas = getOriginalName(project.sas_file_id);
        const ds = (project.dataset_files ?? []).map(getOriginalName);
        if (!sas && ds.length === 0) return ['No files uploaded yet'];
        const lines: string[] = [];
        if (sas) lines.push(`SAS file: ${sas}`);
        if (ds.length) lines.push(`Datasets: ${ds.join(', ')}`);
        return lines;
      }
      case 'translation': {
        const sas = getOriginalName(project.sas_file_id);
        const r = sas ? `${stripExt(sas)}_transformed.R` : 'transformed.R';
        return [
          sas ? `Input: ${sas}` : 'SAS file not uploaded yet',
          `Output: ${r}`,
        ];
      }
      case 'execution':
        return [
          'Runs SAS simulation + R script in parallel',
          'Captures logs and output from both runtimes',
        ];
      case 'validation':
        return [
          'Compares SAS vs R outputs numerically',
          'Reports match %, discrepancies, and issues',
        ];
      case 'report':
        return [
          'Download the generated .R file',
          'Review full validation summary',
        ];
      default:
        return [];
    }
  };

  const getCurrentStepIndex = () => {
    const path = window.location.pathname;
    const idx = steps.findIndex(s => path.includes(s.path));
    return idx === -1 ? 0 : idx;
  };

  const currentStepIndex = getCurrentStepIndex();

  const handleStepClick = (stepPath: string) => {
    if (!projectId) return;
    navigate(`/projects/${projectId}/${stepPath}`);
  };

  const statusConfig: Record<string, { label: string; cls: string }> = {
    validated:  { label: 'Completed',   cls: 'bg-emerald-100 text-emerald-700' },
    completed:  { label: 'Completed',   cls: 'bg-emerald-100 text-emerald-700' },
    executing:  { label: 'Running',     cls: 'bg-amber-100  text-amber-700'   },
    translating:{ label: 'Translating', cls: 'bg-blue-100   text-blue-700'    },
    uploaded:   { label: 'Uploaded',    cls: 'bg-violet-100 text-violet-700'  },
    pending:    { label: 'Pending',     cls: 'bg-slate-100  text-slate-500'   },
  };
  const pStatus = project?.status ?? 'pending';
  const { label: statusLabel, cls: statusCls } = statusConfig[pStatus] ?? { label: pStatus, cls: 'bg-slate-100 text-slate-500' };

  return (
    <div className="fade-in space-y-5">
      {/* Project header */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5 flex items-start justify-between gap-4">
        <div className="min-w-0">
          {project ? (
            <>
              <h1 className="text-xl font-extrabold text-slate-900 tracking-tight truncate">
                {project.name}
              </h1>
              {project.description && (
                <p className="text-sm text-slate-500 mt-1 truncate">{project.description}</p>
              )}
            </>
          ) : (
            <>
              <div className="h-6 w-48 bg-slate-200 rounded-lg animate-pulse mb-2" />
              <div className="h-4 w-32 bg-slate-100 rounded animate-pulse" />
            </>
          )}
        </div>
        {project && (
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold flex-shrink-0 ${statusCls}`}>
            {statusLabel}
          </span>
        )}
      </div>

      {/* Workflow stepper */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
        <div className="flex items-start">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isActive    = index === currentStepIndex;
            const isCompleted = index < currentStepIndex;

            return (
              <React.Fragment key={step.id}>
                {/* Step button */}
                <button
                  type="button"
                  onClick={() => handleStepClick(step.path)}
                  className="flex flex-col items-center gap-2 relative group cursor-pointer flex-shrink-0 focus:outline-none"
                >
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center transition-all shadow-sm ${
                      isActive
                        ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                        : isCompleted
                        ? 'bg-emerald-500 text-white hover:bg-emerald-600'
                        : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
                    }`}
                  >
                    <Icon className="w-[18px] h-[18px]" />
                  </div>
                  <span
                    className={`text-[11px] font-semibold text-center leading-tight select-none ${
                      isActive
                        ? 'text-blue-700'
                        : isCompleted
                        ? 'text-emerald-600'
                        : 'text-slate-400'
                    }`}
                  >
                    {step.label}
                  </span>

                  {/* Tooltip */}
                  <div
                    className={`pointer-events-none absolute top-full mt-2.5 w-56 bg-white border border-slate-200 rounded-xl shadow-xl p-3.5 text-left opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-40 ${
                      index === 0
                        ? 'left-0'
                        : index === steps.length - 1
                        ? 'right-0'
                        : 'left-1/2 -translate-x-1/2'
                    }`}
                  >
                    <p className="text-xs font-bold text-slate-900 mb-2">{step.fullLabel}</p>
                    {getTooltipLines(step.id).map((line, i) => (
                      <p key={i} className="text-xs text-slate-600 leading-relaxed break-words">
                        {line}
                      </p>
                    ))}
                  </div>
                </button>

                {/* Connector line */}
                {index < steps.length - 1 && (
                  <div className="flex-1 px-3 mt-5">
                    <div
                      className={`h-0.5 rounded-full transition-colors duration-300 ${
                        index < currentStepIndex ? 'bg-emerald-400' : 'bg-slate-200'
                      }`}
                    />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Step content */}
      <Routes>
        <Route path="upload"      element={<UploadStep />} />
        <Route path="translation" element={<TranslationStep />} />
        <Route path="execution"   element={<ExecutionStep />} />
        <Route path="validation"  element={<ValidationStep />} />
        <Route path="report"      element={<ReportStep />} />
        <Route path="*"           element={<UploadStep />} />
      </Routes>
    </div>
  );
};

export default ProjectWorkflow;
