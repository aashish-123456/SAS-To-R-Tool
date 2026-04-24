import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Play, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';
import { projectsApi } from '@/services/api';

interface OutputPanel {
  status: string;
  logs: string[];
  output: string;
  r_available?: boolean;
}

const ExecutionStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [sasPanel, setSasPanel] = useState<OutputPanel | null>(null);
  const [rPanel, setRPanel] = useState<OutputPanel | null>(null);
  const [activeTab, setActiveTab] = useState<'logs' | 'output'>('logs');

  const executionMutation = useMutation({
    mutationFn: () => projectsApi.startExecution(projectId!),
    onSuccess: (data) => {
      setSasPanel(data.sas_output);
      setRPanel(data.r_output);
      // Auto-switch to output comparison tab once results are in
      setActiveTab('output');
    },
  });

  useEffect(() => {
    executionMutation.mutate();
  }, [projectId]);

  const isComplete = !!sasPanel && !!rPanel;
  const hasError =
    rPanel?.status === 'error' || rPanel?.status === 'timeout';
  const rNotInstalled = rPanel?.r_available === false;

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
              Executing SAS (Simulated) and R in Parallel
            </h2>
            <p className="text-sm text-gray-600">
              Running both programs to compare outputs
            </p>
          </div>
        </div>

        {/* Loading state */}
        {executionMutation.isPending && (
          <div className="flex items-center gap-3 py-12 justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            <span className="text-gray-600">Executing code — this may take a moment…</span>
          </div>
        )}

        {/* Mutation error */}
        {executionMutation.isError && !isComplete && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium text-red-900">Execution failed</p>
              <p className="text-sm text-red-800 mt-1">
                {(executionMutation.error as any)?.response?.data?.detail ||
                  'Could not reach the backend. Make sure the server is running.'}
              </p>
            </div>
          </div>
        )}

        {/* Results */}
        {isComplete && (
          <>
            {/* R not installed notice */}
            {rNotInstalled && (
              <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="font-medium text-amber-900">R is not installed</p>
                  <p className="text-sm text-amber-800 mt-1">
                    Install R from{' '}
                    <span className="font-mono text-amber-900">https://www.r-project.org/</span>{' '}
                    to run and verify the generated R code. The R code was generated correctly
                    and is shown below.
                  </p>
                </div>
              </div>
            )}

            {/* Tab switcher */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setActiveTab('logs')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'logs'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Execution Logs
              </button>
              <button
                onClick={() => setActiveTab('output')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === 'output'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Output Comparison
              </button>
            </div>

            {/* LOGS tab */}
            {activeTab === 'logs' && (
              <div className="grid grid-cols-2 gap-6 mb-6">
                {/* SAS logs */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 bg-blue-500 rounded-full" />
                    <h3 className="font-medium text-gray-900">SAS Execution (Simulated)</h3>
                    <span className="text-xs text-gray-500 ml-auto">
                      {sasPanel.status === 'success' ? '✓ OK' : '✗ Error'}
                    </span>
                  </div>
                  <div className="bg-gray-900 text-gray-100 rounded-lg p-4 h-72 overflow-y-auto font-mono text-xs">
                    {sasPanel.logs.map((line, i) => (
                      <div key={i} className="mb-0.5 whitespace-pre-wrap">{line}</div>
                    ))}
                    {sasPanel.logs.length === 0 && (
                      <span className="text-gray-500">(no output)</span>
                    )}
                  </div>
                </div>

                {/* R logs */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-3 h-3 rounded-full ${rNotInstalled ? 'bg-amber-400' : 'bg-purple-500'}`} />
                    <h3 className="font-medium text-gray-900">R Execution</h3>
                    <span className="text-xs text-gray-500 ml-auto">
                      {rNotInstalled
                        ? '⚠ Not installed'
                        : rPanel.status === 'success'
                        ? '✓ OK'
                        : '✗ Error'}
                    </span>
                  </div>
                  <div className={`rounded-lg p-4 h-72 overflow-y-auto font-mono text-xs ${
                    rNotInstalled ? 'bg-amber-950 text-amber-100' : 'bg-gray-900 text-gray-100'
                  }`}>
                    {rPanel.logs.map((line, i) => (
                      <div key={i} className="mb-0.5 whitespace-pre-wrap">{line}</div>
                    ))}
                    {rPanel.logs.length === 0 && (
                      <span className="text-gray-500">(no output)</span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* OUTPUT tab */}
            {activeTab === 'output' && (
              <div className="grid grid-cols-2 gap-6 mb-6">
                {/* SAS output */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 bg-blue-500 rounded-full" />
                    <h3 className="font-medium text-gray-900">SAS Output (Simulated)</h3>
                  </div>
                  <div className="bg-blue-950 text-blue-100 rounded-lg p-4 h-96 overflow-y-auto font-mono text-xs">
                    {sasPanel.output != null && sasPanel.output !== '' ? (
                      <pre className="whitespace-pre-wrap">{sasPanel.output}</pre>
                    ) : (
                      <span className="text-blue-400">
                        No output produced. Ensure your SAS code includes DATALINES or upload a dataset file.
                      </span>
                    )}
                  </div>
                </div>

                {/* R output */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-3 h-3 rounded-full ${rNotInstalled ? 'bg-amber-400' : 'bg-purple-500'}`} />
                    <h3 className="font-medium text-gray-900">
                      R Output {rNotInstalled ? '(not executed)' : '(actual)'}
                    </h3>
                  </div>
                  <div className={`rounded-lg p-4 h-96 overflow-y-auto font-mono text-xs ${
                    rNotInstalled
                      ? 'bg-amber-950 text-amber-100'
                      : hasError
                      ? 'bg-red-950 text-red-100'
                      : 'bg-purple-950 text-purple-100'
                  }`}>
                    {rPanel.output != null && rPanel.output !== '' ? (
                      <pre className="whitespace-pre-wrap">{rPanel.output}</pre>
                    ) : rNotInstalled ? (
                      <span className="text-amber-400">
                        R is not installed – install R from https://www.r-project.org/ to see real output here.
                      </span>
                    ) : (
                      <span className="text-gray-400">No output produced</span>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Success banner */}
            <div className={`mb-6 p-4 rounded-lg border ${
              hasError && !rNotInstalled
                ? 'bg-yellow-50 border-yellow-200'
                : 'bg-green-50 border-green-200'
            }`}>
              <div className="flex items-center gap-2">
                {hasError && !rNotInstalled ? (
                  <AlertCircle className="w-5 h-5 text-yellow-600" />
                ) : (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                )}
                <p className={`font-medium ${
                  hasError && !rNotInstalled ? 'text-yellow-800' : 'text-green-800'
                }`}>
                  {hasError && !rNotInstalled
                    ? 'R execution encountered errors – review R output tab.'
                    : rNotInstalled
                    ? 'SAS simulation complete. Install R to run R code.'
                    : 'Both programs executed successfully!'}
                </p>
              </div>
              <p className={`text-sm mt-1 ${
                hasError && !rNotInstalled ? 'text-yellow-700' : 'text-green-700'
              }`}>
                Proceed to validation to compare outputs in detail.
              </p>
            </div>
          </>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => navigate(`/projects/${projectId}/translation`)}
            className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
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
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                Executing…
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ExecutionStep;
