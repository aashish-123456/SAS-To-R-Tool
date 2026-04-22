import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Download, Code } from 'lucide-react';
import { projectsApi } from '@/services/api';

const ReportStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['r-code', projectId],
    queryFn: async () => {
      try {
        const fullCode = await projectsApi.getRCode(projectId!);
        return { r_code: fullCode.r_code, isPreview: false };
      } catch {
        const status = await projectsApi.getTranslationStatus(projectId!);
        return {
          r_code: status.r_code_preview || '',
          isPreview: true,
        };
      }
    },
    enabled: !!projectId,
  });
  const { data: validation } = useQuery({
    queryKey: ['validation-report', projectId],
    queryFn: () => projectsApi.getValidation(projectId!),
    enabled: !!projectId,
  });

  const exportRScript = () => {
    if (!projectId) return;
    const downloadUrl = projectsApi.getRCodeDownloadUrl(projectId);
    window.open(downloadUrl, '_blank');
  };

  return (
    <div className="max-w-4xl">
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
            <Code className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Generated R Code</h2>
            <p className="text-sm text-gray-600">Preview the transformed script and export it.</p>
          </div>
        </div>

        <div className="mb-8">
          <div className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto min-h-[320px]">
            {isLoading ? (
              <div className="text-sm text-gray-400">Loading generated R code...</div>
            ) : isError ? (
              <div className="text-sm text-red-300">
                Unable to load generated R code. Please go back and run translation first.
              </div>
            ) : (
              <div>
                {data?.isPreview && (
                  <p className="text-xs text-yellow-300 mb-3">
                    Showing preview code. Restart backend to enable full code view endpoint.
                  </p>
                )}
                <pre className="text-sm font-mono whitespace-pre-wrap">
                  <code>{data?.r_code || '# No R code available yet'}</code>
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Validation Report */}
        <div className="mb-8">
          <h3 className="text-base font-semibold text-gray-900 mb-3">Validation Report</h3>
          <div className="space-y-3">
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="font-medium text-gray-900">Overall Match Rate</span>
                <span className="text-green-800 font-semibold">
                  {validation ? `${validation.overall_match.toFixed(1)}%` : 'N/A'}
                </span>
              </div>
            </div>
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="font-medium text-gray-900">Structure Match</span>
                <span className="text-gray-700">
                  {validation ? (validation.structure_match ? 'Pass' : 'Fail') : 'N/A'}
                </span>
              </div>
            </div>
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="flex justify-between items-center">
                <span className="font-medium text-gray-900">Value Discrepancies</span>
                <span className="text-gray-700">
                  {validation ? `${validation.value_discrepancies} differences found` : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Issues */}
        <div className="mb-8">
          <h3 className="text-base font-semibold text-gray-900 mb-3">Warnings and Mismatches</h3>
          {!validation?.issues || validation.issues.length === 0 ? (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
              No warnings or mismatches detected.
            </div>
          ) : (
            <div className="space-y-3">
              {validation.issues.map((issue, index) => {
                const severityStyles =
                  issue.severity === 'error'
                    ? 'bg-red-50 border-red-200 text-red-900'
                    : issue.severity === 'warning'
                    ? 'bg-yellow-50 border-yellow-200 text-yellow-900'
                    : 'bg-blue-50 border-blue-200 text-blue-900';

                return (
                  <div key={`${issue.title}-${index}`} className={`p-4 border rounded-lg ${severityStyles}`}>
                    <p className="font-medium">{issue.title}</p>
                    <p className="text-sm mt-1">{issue.detail}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/projects/${projectId}/validation`)}
            className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Back
          </button>
          <button
            onClick={exportRScript}
            className="flex-[2] flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Export R Code
            <Download className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReportStep;
