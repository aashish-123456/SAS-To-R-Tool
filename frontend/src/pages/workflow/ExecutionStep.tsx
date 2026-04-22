import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Play, ArrowRight } from 'lucide-react';
import { projectsApi } from '@/services/api';

const ExecutionStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [sasLogs, setSasLogs] = useState<string[]>([]);
  const [rLogs, setRLogs] = useState<string[]>([]);

  const executionMutation = useMutation({
    mutationFn: () => projectsApi.startExecution(projectId!),
    onSuccess: () => {
      // Simulate log streaming for demo
      simulateLogs();
    },
  });

  useEffect(() => {
    executionMutation.mutate();
  }, [projectId]);

  const simulateLogs = () => {
    const sasLogMessages = [
      'NOTE: Starting SAS execution...',
      'NOTE: Reading dataset WORK.EXAMPLE',
      'NOTE: PROCEDURE SORT used',
      'NOTE: 5 observations read',
      'NOTE: SAS execution completed successfully',
    ];

    const rLogMessages = [
      '> Starting R execution...',
      '> Loading dplyr package',
      '> Reading dataset: example',
      '> Applying arrange(desc(Salary))',
      '> 5 observations processed',
      '> R execution completed successfully',
    ];

    sasLogMessages.forEach((msg, i) => {
      setTimeout(() => setSasLogs((prev) => [...prev, msg]), i * 800);
    });

    rLogMessages.forEach((msg, i) => {
      setTimeout(() => setRLogs((prev) => [...prev, msg]), i * 800);
    });
  };

  const isComplete = sasLogs.length >= 5 && rLogs.length >= 6;

  return (
    <div className="max-w-6xl">
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
            <Play className="w-6 h-6 text-green-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Executing SAS and R in Parallel
            </h2>
            <p className="text-sm text-gray-600">
              Running both programs to compare outputs
            </p>
          </div>
        </div>

        {/* Execution Logs */}
        <div className="grid grid-cols-2 gap-6 mb-8">
          {/* SAS Logs */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-3 h-3 bg-blue-500 rounded-full" />
              <h3 className="font-medium text-gray-900">SAS Execution</h3>
            </div>
            <div className="bg-gray-900 text-gray-100 rounded-lg p-4 h-64 overflow-y-auto font-mono text-sm">
              {sasLogs.map((log, index) => (
                <div key={index} className="mb-1 fade-in">
                  {log}
                </div>
              ))}
              {sasLogs.length > 0 && sasLogs.length < 5 && (
                <div className="text-gray-400 animate-pulse">▊</div>
              )}
            </div>
          </div>

          {/* R Logs */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-3 h-3 bg-purple-500 rounded-full" />
              <h3 className="font-medium text-gray-900">R Execution</h3>
            </div>
            <div className="bg-gray-900 text-gray-100 rounded-lg p-4 h-64 overflow-y-auto font-mono text-sm">
              {rLogs.map((log, index) => (
                <div key={index} className="mb-1 fade-in">
                  {log}
                </div>
              ))}
              {rLogs.length > 0 && rLogs.length < 6 && (
                <div className="text-gray-400 animate-pulse">▊</div>
              )}
            </div>
          </div>
        </div>

        {/* Status */}
        {isComplete && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-green-800 font-medium">
              ✓ Both programs executed successfully!
            </p>
            <p className="text-sm text-green-700 mt-1">
              Proceeding to validation to compare outputs...
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/projects/${projectId}/translation`)}
            disabled={!isComplete}
            className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Back
          </button>
          <button
            onClick={() => navigate(`/projects/${projectId}/validation`)}
            disabled={!isComplete}
            className="flex-[2] flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isComplete ? (
              <>
                Continue to Validation
                <ArrowRight className="w-5 h-5" />
              </>
            ) : (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Executing...
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExecutionStep;
