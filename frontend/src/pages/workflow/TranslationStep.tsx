import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Code, ArrowRight, AlertCircle, Sparkles, Download } from 'lucide-react';
import { projectsApi } from '@/services/api';

const TranslationStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [autoStarted, setAutoStarted] = useState(false);
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.getById(projectId!),
    enabled: !!projectId,
  });

  // Start translation
  const startTranslationMutation = useMutation({
    mutationFn: () => projectsApi.startTranslation(projectId!),
    onSuccess: () => {
      setAutoStarted(true);
    },
  });

  // Poll translation status
  const { data: status } = useQuery({
    queryKey: ['translation-status', projectId],
    queryFn: () => projectsApi.getTranslationStatus(projectId!),
    enabled: autoStarted,
    refetchInterval: (query) => {
      return query.state.data?.status === 'completed' ? false : 2000;
    },
  });

  // Auto-start translation when component mounts
  useEffect(() => {
    if (!autoStarted && projectId) {
      startTranslationMutation.mutate();
    }
  }, [projectId, autoStarted]);

  const handleContinue = () => {
    navigate(`/projects/${projectId}/execution`);
  };

  const isCompleted = status?.status === 'completed';
  const isFailed = status?.status === 'failed';

  const { data: rCodeData } = useQuery({
    queryKey: ['translation-r-code', projectId, isCompleted],
    queryFn: async () => {
      try {
        const fullCode = await projectsApi.getRCode(projectId!);
        return fullCode.r_code;
      } catch {
        return status?.r_code_preview || '';
      }
    },
    enabled: !!projectId && !!isCompleted,
  });

  const handleExportRCode = () => {
    if (!projectId) return;
    const downloadUrl = projectsApi.getRCodeDownloadUrl(projectId);
    window.open(downloadUrl, '_blank');
  };

  return (
    <div className="max-w-4xl">
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        {/* Header with ML Badge */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
            <Code className="w-6 h-6 text-blue-600" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900">
              Translating SAS to R
            </h2>
            <div className="flex items-center gap-2 mt-1">
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span className="text-sm text-purple-600 font-medium">
                AI-Powered with Reinforcement Learning
              </span>
            </div>
          </div>
        </div>

        {/* Progress */}
        <div className="mb-8">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-700">
              {isCompleted
                ? 'Translation complete!'
                : isFailed
                ? 'Translation failed'
                : 'Analyzing SAS code and generating R...'}
            </span>
            <span className="text-gray-600">{status?.progress || 0}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isCompleted
                  ? 'bg-green-500'
                  : isFailed
                  ? 'bg-red-500'
                  : 'bg-blue-600'
              }`}
              style={{ width: `${status?.progress || 0}%` }}
            />
          </div>
        </div>

        {/* Translation steps info */}
        <div className="bg-blue-50 rounded-lg p-6 mb-8">
          <h3 className="font-medium text-gray-900 mb-3">Translation Process:</h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>
                <strong>Step 1:</strong> Parsing SAS code and creating abstract syntax tree
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>
                <strong>Step 2:</strong> Applying ML-enhanced mappings from previous translations
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>
                <strong>Step 3:</strong> Generating optimized R code with learned patterns
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-0.5">•</span>
              <span>
                <strong>Step 4:</strong> Validating generated code structure
              </span>
            </li>
          </ul>
        </div>

        {/* Side-by-side SAS and R Preview */}
        {(project?.sas_code || status?.r_code_preview || rCodeData) && (
          <div className="mb-8">
            <h3 className="font-medium text-gray-900 mb-3">SAS Input vs Generated R Code:</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">SAS Input</p>
                <div className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto min-h-[260px]">
                  <pre className="text-sm font-mono whitespace-pre-wrap">
                    <code>{project?.sas_code || '# SAS input not available yet'}</code>
                  </pre>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Generated R Code</p>
                <div className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto min-h-[260px]">
                  <pre className="text-sm font-mono whitespace-pre-wrap">
                    <code>{rCodeData || status?.r_code_preview || '# R code not available yet'}</code>
                  </pre>
                </div>
              </div>
            </div>
            <div className="mt-3">
              <button
                onClick={handleExportRCode}
                disabled={!isCompleted}
                className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
              >
                Export R Code
                <Download className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Warnings */}
        {status?.warnings && status.warnings.length > 0 && (
          <div className="mb-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
              <div>
                <h3 className="font-medium text-yellow-900 mb-2">Warnings:</h3>
                <ul className="space-y-1">
                  {status.warnings.map((warning, index) => (
                    <li key={index} className="text-sm text-yellow-800">
                      • {warning}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/projects/${projectId}/upload`)}
            disabled={!isCompleted && !isFailed}
            className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Back
          </button>
          <button
            onClick={handleContinue}
            disabled={!isCompleted}
            className="flex-[2] flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isCompleted ? (
              <>
                Continue to Execution
                <ArrowRight className="w-5 h-5" />
              </>
            ) : (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Translating...
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TranslationStep;
