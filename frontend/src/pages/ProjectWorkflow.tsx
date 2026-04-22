import React from 'react';
import { useNavigate, useParams, Routes, Route } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Upload, Code, Play, CheckCircle, FileText } from 'lucide-react';
import { projectsApi } from '@/services/api';
import UploadStep from './workflow/UploadStep';
import TranslationStep from './workflow/TranslationStep';
import ExecutionStep from './workflow/ExecutionStep';
import ValidationStep from './workflow/ValidationStep';
import ReportStep from './workflow/ReportStep';

const ProjectWorkflow: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.getById(projectId!),
    enabled: !!projectId,
  });

  const steps = [
    { id: 'upload', label: 'Upload SAS Inputs', icon: Upload, path: 'upload' },
    { id: 'translation', label: 'SAS to R Transformation', icon: Code, path: 'translation' },
    { id: 'execution', label: 'Dual Runtime Execution', icon: Play, path: 'execution' },
    { id: 'validation', label: 'Output Reconciliation', icon: CheckCircle, path: 'validation' },
    { id: 'report', label: 'Export R Script', icon: FileText, path: 'report' },
  ];

  const getFileName = (filePath?: string) => {
    if (!filePath) return '';
    const normalizedPath = filePath.replace(/\\/g, '/');
    const segments = normalizedPath.split('/');
    return segments[segments.length - 1] || filePath;
  };

  const getOriginalUploadedFileName = (filePath?: string) => {
    const storedName = getFileName(filePath);
    if (!storedName) return '';

    // Backend format: {project_id}_{file_type}_{uuid}_{original_filename}
    // Show only the original uploaded filename in UI tooltips.
    const match = storedName.match(/^.+_(sas|dataset)_[0-9a-fA-F-]{36}_(.+)$/);
    return match?.[2] || storedName;
  };

  const getBaseNameWithoutExtension = (fileName?: string) => {
    if (!fileName) return '';
    const lastDot = fileName.lastIndexOf('.');
    return lastDot > 0 ? fileName.slice(0, lastDot) : fileName;
  };

  const getStepTooltipLines = (stepId: string) => {
    if (!project) return ['Loading project details...'];

    switch (stepId) {
      case 'upload': {
        const sasFileName = getOriginalUploadedFileName(project.sas_file_id);
        const datasetFiles = project.dataset_files ?? [];
        const datasetNames = datasetFiles.map((datasetPath) => getOriginalUploadedFileName(datasetPath));

        if (!sasFileName && datasetNames.length === 0) {
          return ['No files uploaded yet'];
        }

        const lines = [];
        if (sasFileName) {
          lines.push(`SAS file: ${sasFileName}`);
        }
        if (datasetNames.length > 0) {
          lines.push(`Datasets: ${datasetNames.join(', ')}`);
        }
        return lines;
      }
      case 'translation':
        {
          const sasFileName = getOriginalUploadedFileName(project.sas_file_id);
          const rFileName = sasFileName
            ? `${getBaseNameWithoutExtension(sasFileName)}_transformed.R`
            : 'transformed_output.R';

          return [
            sasFileName
              ? `Input: ${sasFileName}`
              : 'Input SAS file not uploaded yet',
            `Output: ${rFileName}`,
            'Content: Converted R script with equivalent SAS logic',
          ];
        }
      case 'execution':
        return [
          'Runs uploaded SAS inputs and generated R script in parallel',
          'Content: Runtime logs, row/column checks, and execution summary',
        ];
      case 'validation':
        return [
          'Compares SAS vs R outputs for structure and values',
          'Content: Match %, discrepancy summary, and statistical checks',
        ];
      case 'report':
        return [
          'File: transformed_output.R',
          'Content: Export and download transformed R script',
        ];
      default:
        return ['No details available'];
    }
  };

  const getCurrentStepIndex = () => {
    const path = window.location.pathname;
    const stepIndex = steps.findIndex(s => path.includes(s.path));
    return stepIndex === -1 ? 0 : stepIndex;
  };

  const currentStepIndex = getCurrentStepIndex();

  const handleStepClick = (stepPath: string) => {
    if (!projectId) return;

    if (stepPath === 'upload') {
      const selected = window.prompt(
        'Choose upload section:\n1 for SAS Code\n2 for SAS Dataset',
        '1'
      );

      if (selected === '2') {
        navigate(`/projects/${projectId}/upload?uploadType=dataset`);
        return;
      }
      navigate(`/projects/${projectId}/upload?uploadType=sas`);
      return;
    }

    navigate(`/projects/${projectId}/${stepPath}`);
  };

  return (
    <div className="fade-in">
      {/* Project Header */}
      <div className="mb-8 bg-white/90 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm p-6">
        <h1 className="text-2xl font-semibold text-slate-900 mb-2 tracking-tight">
          {project?.name || 'Loading...'}
        </h1>
        <p className="text-slate-600">
          {project?.description || 'Project workflow'}
        </p>
      </div>

      {/* Workflow Steps */}
      <div className="mb-8 bg-white/90 backdrop-blur-sm border border-slate-200 rounded-xl shadow-sm p-5">
        <div className="pb-2">
          <div className="flex items-start justify-between gap-2">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isActive = index === currentStepIndex;
            const isCompleted = index < currentStepIndex;

            return (
              <React.Fragment key={step.id}>
                <button
                  type="button"
                  onClick={() => handleStepClick(step.path)}
                  className="flex-1 min-w-0 flex flex-col items-center relative group bg-transparent border-0 p-0 cursor-pointer"
                >
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center mb-2 transition-colors shadow-sm ring-1 ${
                      isActive
                        ? 'bg-blue-600 text-white ring-blue-200'
                        : isCompleted
                        ? 'bg-emerald-500 text-white ring-emerald-200'
                        : 'bg-slate-200 text-slate-500 ring-slate-200'
                    }`}
                  >
                    <Icon className="w-6 h-6" />
                  </div>
                  <span
                    className={`text-sm font-medium ${
                      isActive ? 'text-blue-600' : isCompleted ? 'text-emerald-600' : 'text-slate-500'
                    } text-center leading-tight text-xs md:text-sm px-1 break-words`}
                  >
                    {step.label}
                  </span>
                  <div
                    className={`pointer-events-none absolute top-full mt-2 w-72 rounded-lg border border-gray-200 bg-white p-3 text-left shadow-lg opacity-0 transition-opacity group-hover:opacity-100 z-20 ${
                      index === 0
                        ? 'left-0'
                        : index === steps.length - 1
                        ? 'right-0'
                        : 'left-1/2 -translate-x-1/2'
                    }`}
                  >
                    <p className="text-xs font-semibold text-gray-900 mb-2">Step Details</p>
                    {getStepTooltipLines(step.id).map((line) => (
                      <p key={line} className="text-xs text-gray-700 mb-1 last:mb-0 break-words">
                        {line}
                      </p>
                    ))}
                  </div>
                </button>

                {index < steps.length - 1 && (
                  <div className="flex-1 h-1 mx-4 mt-6">
                    <div
                      className={`h-full rounded ${
                        index < currentStepIndex ? 'bg-emerald-500' : 'bg-slate-200'
                      }`}
                    />
                  </div>
                )}
              </React.Fragment>
            );
          })}
          </div>
        </div>
      </div>

      {/* Step Content */}
      <Routes>
        <Route path="upload" element={<UploadStep />} />
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
