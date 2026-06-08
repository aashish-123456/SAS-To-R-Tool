import React, { useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { CheckCircle2, Wrench, AlertTriangle, ArrowLeft, ArrowRight, Code2 } from 'lucide-react';
import { projectsApi } from '@/services/api';

interface ValidationReport {
  complexity: { level: number; label: string; score: number; badge: string };
  constructs: string[];
  autoFixes: { code: string; description: string; count: number }[];
  warnings: { message: string }[];
  overallStatus: 'ready' | 'auto_fixed' | 'manual_review_required';
  linesOfCode: number;
  nonBlankLines: number;
  fixedCode: string;
}

const InputPreviewStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as {
    sasFile?: File;
    datasetFiles?: File[];
    datasetEnabled?: boolean;
    validationReport?: ValidationReport;
    pathCorrectedCode?: string;
    alreadyUploaded?: boolean;
  } | null;

  const [showFull, setShowFull] = useState(false);
  const navigatingRef = React.useRef(false);

  const report = state?.validationReport;
  // Always use the auto-fixed code from the validation report; fall back to raw file text only if
  // the user navigated here without going through UploadStep (edge case).
  const [rawText, setRawText] = useState('');
  React.useEffect(() => {
    if (!report?.fixedCode && state?.sasFile) {
      state.sasFile.text().then(setRawText);
    }
  }, [state, report]);

  // Prefer path-corrected code (PROC IMPORT paths patched to server locations)
  const codeToDisplay = state?.pathCorrectedCode ?? report?.fixedCode ?? rawText;

  const uploadMutation = useMutation({
    mutationFn: ({ sasCode, datasets }: { sasCode: File; datasets?: File[] }) =>
      projectsApi.uploadFiles(projectId!, sasCode, datasets),
    onSuccess: () => navigate(`/projects/${projectId}/translation`),
    // On failure still proceed — the backend may already have the files from
    // the UploadStep's preliminary upload. Translation can still run.
    onError: () => navigate(`/projects/${projectId}/translation`),
  });

  if (!state?.sasFile) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-6 text-sm text-red-600">
        No uploaded file found. Please go back to the Upload step.
      </div>
    );
  }

  const handleContinue = () => {
    if (navigatingRef.current) return;  // guard against double-click
    navigatingRef.current = true;

    // Always upload codeToDisplay so the backend (and translation) use the exact
    // code shown in this preview — including auto-fixes and path corrections.
    // When alreadyUploaded, datasets are already on the server; the backend
    // re-uses them for DATAFILE= path patching without requiring a re-upload.
    const blob = new Blob([codeToDisplay], { type: 'text/plain' });
    const fixedFile = new File([blob], state.sasFile!.name, { type: 'text/plain' });
    uploadMutation.mutate({
      sasCode: fixedFile,
      datasets: !state.alreadyUploaded && state.datasetEnabled && state.datasetFiles?.length
        ? state.datasetFiles
        : undefined,
    });
  };

  const lines = codeToDisplay.split('\n');
  const displayLines = showFull ? lines : lines.slice(0, 50);

  return (
    <div className="space-y-5 max-w-4xl">

      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0">
            <Code2 className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-lg font-extrabold text-slate-900 leading-tight">Input Validation Preview</h2>
            <p className="text-sm text-slate-500 mt-0.5">
              Review the validated and auto-corrected SAS code before it is sent for translation.
            </p>
          </div>
        </div>
      </div>

      {/* Validation summary banner */}
      {report && (
        <div className={`rounded-xl border p-4 ${
          report.overallStatus === 'auto_fixed'
            ? 'border-blue-200 bg-blue-50/50'
            : 'border-emerald-200 bg-emerald-50/50'
        }`}>
          <div className="flex items-center gap-3 flex-wrap">
            {report.overallStatus === 'auto_fixed'
              ? <Wrench className="w-4 h-4 text-blue-600 flex-shrink-0" />
              : <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />}
            <span className={`text-sm font-bold ${report.overallStatus === 'auto_fixed' ? 'text-blue-700' : 'text-emerald-700'}`}>
              {report.overallStatus === 'auto_fixed'
                ? `${report.autoFixes.length} auto-fix(es) applied — code is ready for translation`
                : 'Validation passed — code is ready for translation'}
            </span>
            <span className={`ml-auto text-xs font-bold px-2.5 py-1 rounded-full border ${report.complexity.badge}`}>
              Level {report.complexity.level} · {report.complexity.label}
            </span>
          </div>

          {report.autoFixes.length > 0 && (
            <ul className="mt-3 space-y-1 pl-7">
              {report.autoFixes.map(fix => (
                <li key={fix.code} className="text-xs text-slate-600">
                  <span className="font-semibold text-blue-600 mr-1">✓</span>
                  {fix.description} ({fix.count}×)
                </li>
              ))}
            </ul>
          )}

          {report.warnings.length > 0 && (
            <div className="mt-2.5 pl-7 flex items-center gap-1.5">
              <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0" />
              <span className="text-xs text-amber-700">
                {report.warnings.length} advisory notice(s) — review after translation
              </span>
            </div>
          )}
        </div>
      )}

      {/* Code preview with line numbers */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <p className="text-xs font-bold text-slate-600 uppercase tracking-wide">
            {state.sasFile.name}
            {report && <span className="font-normal text-slate-400 ml-2">· {report.nonBlankLines} code lines</span>}
          </p>
          {lines.length > 50 && (
            <button
              onClick={() => setShowFull(v => !v)}
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors"
            >
              {showFull ? 'Collapse' : `Show all ${lines.length} lines`}
            </button>
          )}
        </div>
        <div className="overflow-auto max-h-[500px]">
          <table className="w-full text-xs font-mono border-collapse">
            <tbody>
              {displayLines.map((line, i) => (
                <tr key={i} className="hover:bg-slate-50/60">
                  <td className="select-none pl-4 pr-3 py-0.5 text-right text-slate-300 border-r border-slate-100 w-12 align-top">
                    {i + 1}
                  </td>
                  <td className="pl-4 pr-6 py-0.5 text-slate-800 whitespace-pre">{line || ' '}</td>
                </tr>
              ))}
              {!showFull && lines.length > 50 && (
                <tr>
                  <td colSpan={2} className="pl-4 py-2.5 text-xs text-slate-400 italic border-t border-slate-100">
                    … {lines.length - 50} more lines hidden — click "Show all" above
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>


      {/* Navigation */}
      <div className="flex gap-3">
        <button
          onClick={() => navigate(`/projects/${projectId}/upload`)}
          className="flex items-center gap-2 px-5 py-3 border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Upload
        </button>
        <button
          onClick={handleContinue}
          disabled={uploadMutation.isPending}
          className="flex-1 flex items-center justify-center gap-2 px-5 py-3.5 bg-[#1f4368] hover:bg-[#1a3654] text-white text-sm font-bold rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          {uploadMutation.isPending ? 'Uploading…' : 'Continue to Translation'}
          {!uploadMutation.isPending && <ArrowRight className="w-4 h-4" />}
        </button>
      </div>

    </div>
  );
};

export default InputPreviewStep;
