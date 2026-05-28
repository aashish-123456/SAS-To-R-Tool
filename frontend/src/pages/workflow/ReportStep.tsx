import React, { useState, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Download, Code2, ArrowLeft, Copy, CheckCheck, Sparkles,
  Package, FileCode2, BookOpen, AlertTriangle, CheckCircle2,
  BarChart2, Shield, ChevronDown, ChevronRight, Terminal,
  XCircle, Info, RefreshCw, ArrowRight,
} from 'lucide-react';
import { projectsApi } from '@/services/api';

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreColor(n: number) {
  if (n >= 95) return 'text-green-600';
  if (n >= 80) return 'text-blue-600';
  if (n >= 60) return 'text-yellow-600';
  return 'text-red-600';
}
function barColor(n: number) {
  if (n >= 95) return 'bg-green-500';
  if (n >= 80) return 'bg-blue-500';
  if (n >= 60) return 'bg-yellow-400';
  return 'bg-red-500';
}
function severityIcon(s: string) {
  if (s === 'critical') return <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />;
  if (s === 'major')    return <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0" />;
  return <Info className="w-4 h-4 text-blue-500 flex-shrink-0" />;
}
function severityBg(s: string) {
  if (s === 'critical') return 'bg-red-50 border-red-200';
  if (s === 'major')    return 'bg-yellow-50 border-yellow-200';
  return 'bg-blue-50 border-blue-200';
}

// Extract library() calls from R code
function extractPackages(code: string): string[] {
  const matches = code.matchAll(/library\s*\(\s*(\w+)\s*\)/g);
  const pkgs = new Set<string>();
  for (const m of matches) pkgs.add(m[1]);
  return [...pkgs];
}

// Count non-empty lines
function countLines(code: string) {
  return code.split('\n').filter(l => l.trim()).length;
}



// ── Sub-components ────────────────────────────────────────────────────────────

const MetricCard: React.FC<{
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  value: React.ReactNode;
  sub?: string;
}> = ({ icon, iconBg, label, value, sub }) => (
  <div className="bg-white border border-gray-200 rounded-xl p-5">
    <div className={`w-10 h-10 ${iconBg} rounded-lg flex items-center justify-center mb-3`}>
      {icon}
    </div>
    <p className="text-xs text-gray-500 mb-1">{label}</p>
    <p className="text-2xl font-bold text-gray-900">{value}</p>
    {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
  </div>
);

const ScoreBar: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="mb-3">
    <div className="flex justify-between items-center mb-1">
      <span className="text-sm text-gray-700">{label}</span>
      <span className={`text-sm font-semibold ${scoreColor(value)}`}>{value}%</span>
    </div>
    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${barColor(value)}`} style={{ width: `${value}%`, transition: 'width 0.6s ease' }} />
    </div>
  </div>
);

// ── Main Component ────────────────────────────────────────────────────────────

type TabId = 'script' | 'validation' | 'packages' | 'deployment';

const ReportStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabId>('script');
  const [copied, setCopied] = useState(false);
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [expandIssues, setExpandIssues] = useState(true);

  // Fetch R code
  const { data: codeData, isLoading: codeLoading } = useQuery({
    queryKey: ['r-code', projectId],
    queryFn: async () => {
      try {
        const full = await projectsApi.getRCode(projectId!);
        return { r_code: full.r_code, isPreview: false };
      } catch {
        const status = await projectsApi.getTranslationStatus(projectId!);
        return { r_code: status.r_code_preview || '', isPreview: true };
      }
    },
    enabled: !!projectId,
  });

  // Fetch validation
  const { data: validation } = useQuery({
    queryKey: ['validation', projectId],
    queryFn: () => projectsApi.getValidation(projectId!),
    enabled: !!projectId,
    staleTime: 30_000,
  });

  const rCode  = codeData?.r_code ?? '';
  const packages = useMemo(() => extractPackages(rCode), [rCode]);
  const lineCount = useMemo(() => countLines(rCode), [rCode]);
  const confidence = validation?.overall_confidence ?? validation?.overall_match ?? 0;
  const confLabel  = validation?.confidence_label ?? (confidence >= 90 ? 'High Confidence' : 'Medium Confidence');

  const handleCopy = () => {
    navigator.clipboard.writeText(rCode).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleDownload = () => {
    if (!projectId) return;
    window.open(projectsApi.getRCodeDownloadUrl(projectId), '_blank');
  };

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'script',     label: 'R Script',              icon: <FileCode2 className="w-4 h-4" /> },
    { id: 'validation', label: 'Validation Summary',    icon: <Shield className="w-4 h-4" /> },
    { id: 'packages',   label: 'Package Dependencies',  icon: <Package className="w-4 h-4" /> },
    { id: 'deployment', label: 'Deployment Notes',      icon: <BookOpen className="w-4 h-4" /> },
  ];

  const issuesBySeverity = useMemo(() => ({
    critical: (validation?.issues ?? []).filter(i => i.severity === 'critical'),
    major:    (validation?.issues ?? []).filter(i => i.severity === 'major'),
    minor:    (validation?.issues ?? []).filter(i => i.severity === 'minor'),
  }), [validation]);

  return (
    <div className="max-w-7xl space-y-5">

      {/* ── Header ── */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-[#1f4368] rounded-xl flex items-center justify-center">
              <Code2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-gray-900">Export R Script</h1>
                <Sparkles className="w-5 h-5 text-[#1f4368]" />
              </div>
              <p className="text-sm text-gray-500">
                Production-ready translated R script — reviewed, validated, and ready for deployment.
              </p>
            </div>
          </div>
          {/* SAS → R diagram */}
          <div className="hidden md:flex items-center gap-2 text-sm">
            <div className="w-10 h-10 bg-[#1a3654] rounded-lg flex items-center justify-center text-white font-bold text-xs">SAS</div>
            <ArrowRight className="w-4 h-4 text-gray-400" />
            <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center text-white font-bold text-xs">R</div>
          </div>
        </div>
        <div className="flex gap-3 mt-4">
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-2 bg-[#1f4368] text-white rounded-lg text-sm hover:bg-[#1a3654] font-medium"
          >
            <Download className="w-4 h-4" />
            Download R Script
          </button>
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
          >
            {copied ? <CheckCheck className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            {copied ? 'Copied!' : 'Copy to Clipboard'}
          </button>
          <button
            onClick={() => navigate(`/projects/${projectId}/translate`)}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
          >
            <RefreshCw className="w-4 h-4" />
            Re-run Translation
          </button>
        </div>
      </div>

      {/* ── Summary cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={<BarChart2 className="w-5 h-5 text-[#1f4368]" />}
          iconBg="bg-[#eef3f8]"
          label="Translation Confidence"
          value={<span className={scoreColor(confidence)}>{confidence.toFixed(1)}%</span>}
          sub={confLabel}
        />
        <MetricCard
          icon={<FileCode2 className="w-5 h-5 text-green-600" />}
          iconBg="bg-green-50"
          label="Lines of Code"
          value={lineCount}
          sub="Non-empty lines"
        />
        <MetricCard
          icon={<Package className="w-5 h-5 text-purple-600" />}
          iconBg="bg-purple-50"
          label="R Packages Required"
          value={packages.length}
          sub={packages.length ? packages.slice(0, 2).join(', ') + (packages.length > 2 ? '…' : '') : 'Base R only'}
        />
        <MetricCard
          icon={<Shield className="w-5 h-5 text-blue-600" />}
          iconBg="bg-blue-50"
          label="Issues Detected"
          value={
            <span className={(validation?.issues ?? []).length === 0 ? 'text-green-600' : 'text-yellow-600'}>
              {(validation?.issues ?? []).length}
            </span>
          }
          sub={`${issuesBySeverity.critical.length} critical · ${issuesBySeverity.major.length} major · ${issuesBySeverity.minor.length} minor`}
        />
      </div>

      {/* ── Tabs panel ── */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {/* Tab headers */}
        <div className="border-b border-gray-200 px-4">
          <div className="flex gap-1 overflow-x-auto">
            {tabs.map(t => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-2 px-4 py-3.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === t.id
                    ? 'border-[#1f4368] text-[#1f4368]'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="p-5">

          {/* ── Tab: R Script ── */}
          {activeTab === 'script' && (
            <div>
              {/* Code viewer toolbar */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-700">generated_script.R</span>
                  {codeData?.isPreview && (
                    <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-700 border border-yellow-200 rounded-full">
                      Preview only
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showLineNumbers}
                      onChange={e => setShowLineNumbers(e.target.checked)}
                      className="rounded"
                    />
                    Line numbers
                  </label>
                  <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 px-3 py-1.5 border border-gray-200 rounded-lg text-xs text-gray-600 hover:bg-gray-50"
                  >
                    {copied ? <CheckCheck className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                  <button
                    onClick={handleDownload}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1f4368] text-white rounded-lg text-xs hover:bg-[#1a3654]"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                </div>
              </div>

              {/* Code block */}
              <div className="bg-gray-950 rounded-xl overflow-hidden border border-gray-800">
                {/* Window controls */}
                <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-900 border-b border-gray-800">
                  <span className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="w-3 h-3 rounded-full bg-yellow-500" />
                  <span className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="ml-3 text-xs text-gray-500 font-mono">generated_script.R</span>
                </div>
                <div className="overflow-auto max-h-[520px]">
                  {codeLoading ? (
                    <div className="p-6 text-sm text-gray-400">Loading R code…</div>
                  ) : rCode ? (
                    <table className="w-full text-xs font-mono">
                      <tbody>
                        {rCode.split('\n').map((line, i) => (
                          <tr key={i} className="hover:bg-gray-900/60">
                            {showLineNumbers && (
                              <td className="select-none text-right pr-4 pl-4 py-0.5 text-gray-600 border-r border-gray-800 w-10 min-w-[2.5rem]">
                                {i + 1}
                              </td>
                            )}
                            <td className="pl-4 pr-4 py-0.5">
                              {line.trimStart().startsWith('#') ? (
                                <span className="text-green-400">{line}</span>
                              ) : (
                                <span className="text-gray-200">{line}</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="p-6 text-sm text-gray-500">No R code available yet. Run translation first.</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── Tab: Validation Summary ── */}
          {activeTab === 'validation' && (
            <div className="space-y-6">
              {/* Score circles row */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {(validation?.category_scores ?? []).map(cs => (
                  <div key={cs.name} className="bg-gray-50 border border-gray-200 rounded-xl p-4 text-center">
                    <p className={`text-2xl font-bold ${scoreColor(cs.score)}`}>{cs.score.toFixed(0)}%</p>
                    <p className="text-xs text-gray-500 mt-1 leading-tight">{cs.display_name}</p>
                    <p className="text-xs text-gray-400">{cs.scenarios_passed}/{cs.scenarios_total} passed</p>
                  </div>
                ))}
                {!validation?.category_scores?.length && (
                  <div className="col-span-5 text-center py-8 text-gray-400">
                    <Shield className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Validation data not loaded. Navigate through the Validation step first.</p>
                  </div>
                )}
              </div>

              {/* Score bars */}
              {(validation?.category_scores ?? []).length > 0 && (
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
                  <h3 className="font-semibold text-gray-900 mb-4">Score Breakdown</h3>
                  {(validation?.category_scores ?? []).map(cs => (
                    <ScoreBar key={cs.name} label={cs.display_name} value={Math.round(cs.score)} />
                  ))}
                </div>
              )}

              {/* Issues */}
              <div>
                <button
                  className="flex items-center gap-2 w-full mb-3"
                  onClick={() => setExpandIssues(!expandIssues)}
                >
                  <h3 className="font-semibold text-gray-900">
                    Issues ({(validation?.issues ?? []).length})
                  </h3>
                  {expandIssues
                    ? <ChevronDown className="w-4 h-4 text-gray-400" />
                    : <ChevronRight className="w-4 h-4 text-gray-400" />}
                </button>
                {expandIssues && (
                  (validation?.issues ?? []).length === 0 ? (
                    <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-xl">
                      <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                      <p className="text-sm text-green-800 font-medium">No issues — translation passed all validation checks.</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {(validation?.issues ?? []).map((issue, i) => (
                        <div key={i} className={`border rounded-xl p-4 ${severityBg(issue.severity)}`}>
                          <div className="flex items-start gap-3">
                            {severityIcon(issue.severity)}
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold text-gray-900">{issue.title}</p>
                              <p className="text-xs text-gray-600 mt-0.5">{issue.detail}</p>
                              {issue.suggestion && (
                                <p className="text-xs text-gray-500 mt-1.5 italic">
                                  <span className="font-medium">Fix:</span> {issue.suggestion}
                                </p>
                              )}
                            </div>
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                              issue.severity === 'critical' ? 'text-red-700 bg-red-100 border-red-300' :
                              issue.severity === 'major'    ? 'text-yellow-700 bg-yellow-100 border-yellow-300' :
                                                             'text-blue-700 bg-blue-100 border-blue-300'
                            }`}>
                              {issue.severity.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )
                )}
              </div>

              {/* Recommendations */}
              {(validation?.recommendations ?? []).length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-[#1f4368]" />
                    AI Recommendations
                  </h3>
                  <div className="space-y-2">
                    {(validation?.recommendations ?? []).map((rec, i) => (
                      <div key={i} className="flex items-start gap-3 bg-[#eef3f8] border border-[#ccdce9] rounded-xl p-4">
                        <span className="w-5 h-5 bg-[#1f4368] rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-0.5">
                          {i + 1}
                        </span>
                        <p className="text-sm text-slate-900">{rec}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ── Tab: Package Dependencies ── */}
          {activeTab === 'packages' && (
            <div className="space-y-5">
              {packages.length === 0 ? (
                <div className="flex items-center gap-3 p-5 bg-green-50 border border-green-200 rounded-xl">
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                  <p className="text-sm text-green-800 font-medium">No external packages required — pure base R translation.</p>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    {packages.map(pkg => (
                      <div key={pkg} className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-3">
                        <div className="w-8 h-8 bg-[#eef3f8] rounded-lg flex items-center justify-center">
                          <Package className="w-4 h-4 text-[#1f4368]" />
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-gray-900">{pkg}</p>
                          <p className="text-xs text-gray-400">R Package</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Install snippet */}
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-gray-600" />
                      Install All Packages
                    </h3>
                    <div className="bg-gray-950 rounded-xl overflow-hidden border border-gray-800">
                      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-900 border-b border-gray-800">
                        <span className="text-xs text-gray-500 font-mono">install.R</span>
                        <button
                          onClick={() => navigator.clipboard.writeText(
                            `install.packages(c(${packages.map(p => `"${p}"`).join(', ')}))`
                          )}
                          className="text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1"
                        >
                          <Copy className="w-3 h-3" /> Copy
                        </button>
                      </div>
                      <pre className="text-sm text-green-300 p-4 font-mono whitespace-pre-wrap">
{`# Install required packages\ninstall.packages(c(\n${packages.map(p => `  "${p}"`).join(',\n')}\n))\n\n# Load packages\n${packages.map(p => `library(${p})`).join('\n')}`}
                      </pre>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Tab: Deployment Notes ── */}
          {activeTab === 'deployment' && (
            <div className="space-y-5">
              <div className="bg-[#eef3f8] border border-[#ccdce9] rounded-xl p-5">
                <h3 className="font-semibold text-slate-900 mb-1 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#1f4368]" />
                  Script is ready for deployment
                </h3>
                <p className="text-sm text-[#1a3050]">
                  The translated R script has passed semantic equivalence validation with a confidence of{' '}
                  <strong>{confidence.toFixed(1)}%</strong>. Follow the steps below to run it in your environment.
                </p>
              </div>

              {[
                {
                  step: '1',
                  title: 'Install R (≥ 4.0)',
                  desc: 'Download and install R from https://www.r-project.org/ if not already present.',
                  code: null,
                },
                {
                  step: '2',
                  title: 'Install Required Packages',
                  desc: packages.length
                    ? `The script requires: ${packages.join(', ')}`
                    : 'No external packages are needed — the script uses base R only.',
                  code: packages.length
                    ? `install.packages(c(${packages.map(p => `"${p}"`).join(', ')}))`
                    : null,
                },
                {
                  step: '3',
                  title: 'Place Data Files',
                  desc: 'If your SAS program read external CSV or dataset files, place them in the same directory as the R script or update the path in the read.csv() calls.',
                  code: null,
                },
                {
                  step: '4',
                  title: 'Run the Script',
                  desc: 'Execute the script from RStudio, VS Code with R extension, or directly via Rscript in the terminal.',
                  code: 'Rscript generated_script.R',
                },
                {
                  step: '5',
                  title: 'Verify Output',
                  desc: 'Compare the R output against the SAS output in the Execution Center to confirm semantic equivalence.',
                  code: null,
                },
              ].map(item => (
                <div key={item.step} className="flex gap-4">
                  <div className="w-8 h-8 bg-[#1f4368] rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0 mt-0.5">
                    {item.step}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-gray-900 mb-1">{item.title}</h4>
                    <p className="text-sm text-gray-600 mb-2">{item.desc}</p>
                    {item.code && (
                      <div className="bg-gray-950 rounded-lg px-4 py-2.5 border border-gray-800">
                        <code className="text-sm text-green-300 font-mono">{item.code}</code>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

        </div>
      </div>

      {/* ── Action bar ── */}
      <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-5 py-4">
        <button
          onClick={() => navigate(`/projects/${projectId}/validation`)}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Validation
        </button>
        <div className="flex gap-3">
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
          >
            {copied ? <CheckCheck className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
            {copied ? 'Copied!' : 'Copy Script'}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-5 py-2 bg-[#1f4368] text-white rounded-lg text-sm hover:bg-[#1a3654] font-medium"
          >
            <Download className="w-4 h-4" />
            Export R Script
          </button>
        </div>
      </div>

    </div>
  );
};

export default ReportStep;
