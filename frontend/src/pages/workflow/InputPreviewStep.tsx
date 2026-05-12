import React, { useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { projectsApi } from '@/services/api';

const findSyntaxIssues = (code: string) => {
  const issues: string[] = [];
  const lines = code.split('\n');
  if (!/\brun\s*;/i.test(code)) issues.push('Missing RUN; statement.');
  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    if (/^(data|set|if|else|proc|where)\b/i.test(trimmed) && !trimmed.endsWith(';') && !/^data\s+\w+\s*;?$/i.test(trimmed)) {
      issues.push(`Possible missing semicolon at line ${idx + 1}.`);
    }
  });
  return issues;
};

const InputPreviewStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [codeText, setCodeText] = useState('');
  const state = location.state as { sasFile?: File; datasetFiles?: File[] } | null;

  const uploadMutation = useMutation({
    mutationFn: ({ sasCode, datasets }: { sasCode: File; datasets?: File[] }) => projectsApi.uploadFiles(projectId!, sasCode, datasets),
    onSuccess: () => navigate(`/projects/${projectId}/translation`),
  });

  React.useEffect(() => {
    const load = async () => {
      if (state?.sasFile) setCodeText(await state.sasFile.text());
    };
    load();
  }, [state]);

  const issues = useMemo(() => findSyntaxIssues(codeText), [codeText]);
  const canProceed = !!state?.sasFile && issues.length === 0;

  if (!state?.sasFile) {
    return <div className="text-sm text-red-600">No uploaded file found. Please go back to Upload step.</div>;
  }

  return (
    <div className="max-w-4xl">
      <div className="bg-white border border-gray-200 rounded-lg p-8 space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Input Preview and Syntax Check</h2>
          <p className="text-sm text-gray-600">Step 2 of 2: resolve SAS syntax issues before continuing.</p>
        </div>
        <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 text-xs overflow-auto max-h-96">{codeText || '# Empty file'}</pre>
        {issues.length > 0 ? (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="font-medium text-red-700 mb-2">Syntax or format issues found:</p>
            <ul className="list-disc list-inside text-sm text-red-700">
              {issues.map((issue, i) => <li key={i}>{issue}</li>)}
            </ul>
            <p className="text-sm text-red-700 mt-2">Please correct and re-upload from the previous screen.</p>
          </div>
        ) : (
          <p className="text-sm text-green-700">SAS code passed syntax pre-check.</p>
        )}
        <div className="flex gap-3">
          <button onClick={() => navigate(`/projects/${projectId}/upload`)} className="flex-1 px-4 py-3 border border-gray-300 rounded-lg">Back</button>
          <button
            onClick={() => uploadMutation.mutate({ sasCode: state.sasFile!, datasets: state?.datasetFiles?.length ? state.datasetFiles : undefined })}
            disabled={!canProceed || uploadMutation.isPending}
            className="flex-[2] px-4 py-3 bg-blue-600 text-white rounded-lg disabled:opacity-50"
          >
            {uploadMutation.isPending ? 'Uploading...' : 'Continue to Translation'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default InputPreviewStep;
