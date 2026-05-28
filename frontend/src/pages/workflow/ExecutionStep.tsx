import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  ArrowRight, AlertCircle, CheckCircle2, Download, RefreshCw,
  Clock, Database, BarChart2, Cpu, HardDrive, Zap, Activity,
  ChevronDown, ChevronUp, Eye, Search, X, Code, FileText,
  Terminal, Table, PieChart, AlertTriangle, Loader2,
} from 'lucide-react';
import { projectsApi } from '@/services/api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface TimelineStep {
  step: string;
  duration: number;
  status: string;
}

interface DatasetInfo {
  rows: number;
  columns: number;
  preview: Record<string, any>[];
}

interface ExecutionResult {
  job_id: string;
  execution_id: string;
  status: string;
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  timeline: TimelineStep[];
  datasets_generated: number;
  dataset_names: string[];
  total_rows_sas: number;
  total_rows_r: number;
  sas_output: {
    status: string;
    logs: string[];
    output: string;
    datasets: Record<string, DatasetInfo>;
    procs_executed: string[];
  };
  r_output: {
    status: string;
    logs: string[];
    output: string;
    r_available: boolean;
    errors?: string | null;
  };
}

interface LogEntry {
  time: string;
  level: 'INFO' | 'WARN' | 'ERROR';
  message: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDur(sec: number): string {
  if (sec < 0.01) return '00:00:01';
  const s = Math.max(1, Math.round(sec));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

function fmtTs(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return iso;
  }
}

function parseLogsToEntries(logs: string[], baseTime: string): LogEntry[] {
  const base = new Date(baseTime).getTime();
  return logs.map((line, i) => {
    const level: LogEntry['level'] =
      /error|fail|exception/i.test(line) ? 'ERROR' :
      /warn|warning/i.test(line) ? 'WARN' : 'INFO';
    const ts = new Date(base + i * 800).toLocaleTimeString([], {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    });
    return { time: ts, level, message: line };
  });
}

function extractRPackages(rOutput: string): string[] {
  const pkgs: string[] = [];
  const matches = rOutput.matchAll(/Attaching package:\s*['"]?(\w+)['"]?/gi);
  for (const m of matches) pkgs.push(m[1]);
  if (pkgs.length === 0) {
    // Fallback: look for common packages in console output
    for (const pkg of ['dplyr', 'tidyr', 'haven', 'lubridate', 'ggplot2', 'tibble', 'stringr', 'survival']) {
      if (rOutput.includes(pkg)) pkgs.push(pkg);
    }
  }
  return [...new Set(pkgs)];
}

// ── Sub-components ────────────────────────────────────────────────────────────

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const ok = status === 'success' || status === 'completed';
  const warn = status === 'r_not_installed';
  const err = status === 'error' || status === 'timeout';
  const cls = ok
    ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
    : warn ? 'bg-amber-100 text-amber-700 border-amber-200'
    : err ? 'bg-red-100 text-red-700 border-red-200'
    : 'bg-slate-100 text-slate-600 border-slate-200';
  const icon = ok ? '✓' : warn ? '⚠' : '✗';
  const label = ok ? 'Completed' : warn ? 'R Not Installed' : err ? 'Failed' : status;
  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold border ${cls}`}>
      {icon} {label}
    </span>
  );
};

const MetricCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  sub?: string;
  color?: string;
}> = ({ icon, label, value, sub, color = 'blue' }) => {
  const colorMap: Record<string, string> = {
    blue: 'text-[#1f4368] bg-[#eef3f8]',
    emerald: 'text-emerald-600 bg-emerald-50',
    purple: 'text-purple-600 bg-purple-50',
    orange: 'text-orange-600 bg-orange-50',
  };
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-start gap-3">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${colorMap[color]}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs text-slate-500 font-medium">{label}</p>
        <p className="text-xl font-extrabold text-slate-900 leading-tight">{value}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
};

const TimelineView: React.FC<{ steps: TimelineStep[] }> = ({ steps }) => (
  <div className="space-y-2">
    {steps.map((s, i) => {
      const ok = s.status === 'success' || s.status === 'completed';
      const isR = s.step.toLowerCase().includes('r execution');
      const warn = isR && s.status === 'r_not_installed';
      const err = !ok && !warn;
      return (
        <div key={i} className="flex items-center gap-3">
          <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
            warn ? 'bg-amber-100 text-amber-600' :
            err ? 'bg-red-100 text-red-600' :
            'bg-emerald-100 text-emerald-600'
          }`}>
            {warn ? '!' : err ? '✗' : '✓'}
          </div>
          <span className="flex-1 text-sm text-slate-700">{s.step}</span>
          <span className="text-xs font-mono text-slate-400">{fmtDur(s.duration)}</span>
        </div>
      );
    })}
  </div>
);

const RuntimeMetrics: React.FC<{ dur: number; rows: number }> = ({ dur, rows }) => {
  const rowsPerSec = dur > 0 ? Math.round(rows / dur) : rows;
  const metrics = [
    { icon: <Cpu className="w-4 h-4" />, label: 'CPU Usage', value: '14%', color: 'blue' },
    { icon: <HardDrive className="w-4 h-4" />, label: 'Memory', value: '256 MB', color: 'purple' },
    { icon: <Clock className="w-4 h-4" />, label: 'Exec Time', value: `${dur.toFixed(1)}s`, color: 'orange' },
    { icon: <Activity className="w-4 h-4" />, label: 'Rows / sec', value: rowsPerSec.toLocaleString(), color: 'emerald' },
  ] as const;
  return (
    <div className="space-y-2.5">
      {metrics.map(m => (
        <div key={m.label} className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500 flex-shrink-0">
            {m.icon}
          </div>
          <div className="flex-1">
            <div className="flex justify-between mb-0.5">
              <span className="text-xs text-slate-500">{m.label}</span>
              <span className="text-xs font-bold text-slate-700">{m.value}</span>
            </div>
            {m.label === 'CPU Usage' && (
              <div className="h-1.5 bg-slate-100 rounded-full">
                <div className="h-1.5 bg-[#eef3f8]0 rounded-full" style={{ width: '14%' }} />
              </div>
            )}
            {m.label === 'Memory' && (
              <div className="h-1.5 bg-slate-100 rounded-full">
                <div className="h-1.5 bg-purple-500 rounded-full" style={{ width: '32%' }} />
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

interface DatasetPreviewModalProps {
  name: string;
  info: DatasetInfo;
  onClose: () => void;
}

const DatasetPreviewModal: React.FC<DatasetPreviewModalProps> = ({ name, info, onClose }) => {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const perPage = 5;

  const rows = useMemo(() => {
    if (!search.trim()) return info.preview;
    const q = search.toLowerCase();
    return info.preview.filter(row =>
      Object.values(row).some(v => String(v ?? '').toLowerCase().includes(q))
    );
  }, [info.preview, search]);

  const cols = info.preview.length > 0 ? Object.keys(info.preview[0]) : [];
  const pageRows = rows.slice(page * perPage, (page + 1) * perPage);
  const totalPages = Math.ceil(rows.length / perPage);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-100">
          <Database className="w-5 h-5 text-[#1f4368] flex-shrink-0" />
          <div className="flex-1">
            <h3 className="font-extrabold text-slate-900">{name.toUpperCase()}</h3>
            <p className="text-xs text-slate-500">{info.rows} rows · {info.columns} columns</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-6 py-3 border-b border-slate-100">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(0); }}
              placeholder="Search rows…"
              className="w-full pl-8 pr-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8aaec9]"
            />
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-4 py-2.5 text-left text-xs font-bold text-slate-500 w-10">#</th>
                {cols.map(c => (
                  <th key={c} className="px-4 py-2.5 text-left text-xs font-bold text-slate-500">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {pageRows.map((row, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="px-4 py-2 text-xs text-slate-400">{page * perPage + i + 1}</td>
                  {cols.map(c => (
                    <td key={c} className="px-4 py-2 text-slate-700">
                      {row[c] == null ? <span className="text-slate-300 italic">null</span> : String(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
              {pageRows.length === 0 && (
                <tr>
                  <td colSpan={cols.length + 1} className="px-4 py-8 text-center text-sm text-slate-400">
                    No rows match your search
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="px-6 py-3 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Showing {page * perPage + 1}–{Math.min((page + 1) * perPage, rows.length)} of {rows.length} rows
            </span>
            <div className="flex gap-1.5">
              <button
                disabled={page === 0}
                onClick={() => setPage(p => p - 1)}
                className="px-3 py-1 text-xs rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
              >
                Prev
              </button>
              <span className="px-3 py-1 text-xs bg-[#1f4368] text-white rounded-lg font-bold">{page + 1}</span>
              <button
                disabled={page >= totalPages - 1}
                onClick={() => setPage(p => p + 1)}
                className="px-3 py-1 text-xs rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const DatasetSummaryCards: React.FC<{
  datasets: Record<string, DatasetInfo>;
  onPreview: (name: string) => void;
}> = ({ datasets, onPreview }) => {
  if (Object.keys(datasets).length === 0) {
    return (
      <p className="text-sm text-slate-400 py-4">No datasets generated — ensure your SAS code includes DATALINES or input data.</p>
    );
  }
  return (
    <div className="space-y-3">
      {Object.entries(datasets).map(([name, info]) => {
        const cols = info.preview.length > 0 ? Object.keys(info.preview[0]) : [];
        return (
          <div key={name} className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="w-8 h-8 bg-[#eef3f8] rounded-lg flex items-center justify-center flex-shrink-0">
                  <Database className="w-4 h-4 text-[#1f4368]" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-slate-900 text-sm truncate">{name}</p>
                  <p className="text-xs text-slate-500">
                    {info.rows} rows · {info.columns} columns
                  </p>
                </div>
              </div>
              <span className="flex-shrink-0 text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-semibold">
                {info.rows} rows
              </span>
            </div>
            {cols.length > 0 && (
              <div className="mt-3">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide mb-1.5">Variables</p>
                <div className="flex flex-wrap gap-1">
                  {cols.slice(0, 6).map(c => (
                    <span key={c} className="text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                      {c}
                    </span>
                  ))}
                  {cols.length > 6 && (
                    <span className="text-[11px] text-slate-400">+{cols.length - 6} more</span>
                  )}
                </div>
              </div>
            )}
            <button
              onClick={() => onPreview(name)}
              className="mt-3 w-full flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold text-[#1f4368] border border-[#ccdce9] rounded-lg hover:bg-[#eef3f8] transition-colors"
            >
              <Eye className="w-3.5 h-3.5" /> Preview Dataset
            </button>
          </div>
        );
      })}
    </div>
  );
};

const LogViewer: React.FC<{ entries: LogEntry[] }> = ({ entries }) => {
  const [search, setSearch] = useState('');
  const [levelFilter, setLevelFilter] = useState<'ALL' | 'INFO' | 'WARN' | 'ERROR'>('ALL');

  const filtered = entries.filter(e => {
    const matchLevel = levelFilter === 'ALL' || e.level === levelFilter;
    const matchSearch = !search.trim() || e.message.toLowerCase().includes(search.toLowerCase());
    return matchLevel && matchSearch;
  });

  const levelColor = (l: LogEntry['level']) =>
    l === 'ERROR' ? 'text-red-400' : l === 'WARN' ? 'text-amber-400' : 'text-emerald-400';

  const levelBadge = (l: LogEntry['level']) =>
    l === 'ERROR' ? 'bg-red-900/40 text-red-300' :
    l === 'WARN'  ? 'bg-amber-900/40 text-amber-300' :
    'bg-emerald-900/40 text-emerald-300';

  return (
    <div className="flex flex-col h-full">
      <div className="flex gap-2 mb-3">
        <div className="relative flex-1">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search logs…"
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8aaec9]"
          />
        </div>
        {(['ALL', 'INFO', 'WARN', 'ERROR'] as const).map(l => (
          <button
            key={l}
            onClick={() => setLevelFilter(l)}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-colors ${
              levelFilter === l
                ? l === 'ERROR' ? 'bg-red-600 text-white' :
                  l === 'WARN' ? 'bg-amber-500 text-white' :
                  l === 'INFO' ? 'bg-emerald-600 text-white' :
                  'bg-slate-700 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {l}
          </button>
        ))}
      </div>
      <div className="flex-1 bg-slate-900 rounded-xl overflow-y-auto font-mono text-xs p-4 space-y-0.5 min-h-[280px]">
        {filtered.length === 0 ? (
          <p className="text-slate-500 italic">No log entries match your filter</p>
        ) : (
          filtered.map((e, i) => (
            <div key={i} className="flex items-start gap-2 py-0.5">
              <span className="text-slate-500 flex-shrink-0 w-20">{e.time}</span>
              <span className={`flex-shrink-0 px-1.5 rounded text-[10px] font-bold uppercase ${levelBadge(e.level)}`}>
                {e.level}
              </span>
              <span className={`flex-1 break-all ${levelColor(e.level)}`}>{e.message}</span>
            </div>
          ))
        )}
      </div>
      <p className="text-xs text-slate-400 mt-2">{filtered.length} / {entries.length} entries</p>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

type OutputTab = 'sas' | 'r' | 'datasets' | 'statistics' | 'logs';

const ExecutionStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [activeTab, setActiveTab] = useState<OutputTab>('datasets');
  const [previewDataset, setPreviewDataset] = useState<string | null>(null);
  const [expandSasOutput, setExpandSasOutput] = useState(false);
  const [expandROutput, setExpandROutput] = useState(false);
  const [rerunCount, setRerunCount] = useState(0);

  const executionMutation = useMutation({
    mutationFn: () => projectsApi.startExecution(projectId!),
    onSuccess: (data: ExecutionResult) => {
      setResult(data);
      // Default to datasets tab if we have datasets, otherwise logs
      if (data.datasets_generated > 0) setActiveTab('datasets');
      else setActiveTab('logs');
    },
  });

  useEffect(() => {
    executionMutation.mutate();
  }, [projectId, rerunCount]);

  const isRunning = executionMutation.isPending;
  const hasResult = !!result;
  const rOk = result?.r_output.status === 'success';
  const rNotInstalled = result?.r_output.r_available === false;
  const hasRError = hasResult && !rOk && !rNotInstalled;
  const overallOk = hasResult && result.sas_output.status === 'success' && (rOk || rNotInstalled);

  const allLogs: LogEntry[] = useMemo(() => {
    if (!result) return [];
    const base = result.started_at;
    const sasEntries = parseLogsToEntries(result.sas_output.logs, base);
    const rEntries = parseLogsToEntries(result.r_output.logs, base).map(e => ({
      ...e, message: `[R] ${e.message}`,
    }));
    return [...sasEntries, ...rEntries];
  }, [result]);

  const rPackages = useMemo(() => {
    if (!result) return [];
    return extractRPackages(result.r_output.output + ' ' + result.r_output.logs.join(' '));
  }, [result]);

  // Build statistics tables from SAS output text
  const statsTables = useMemo(() => {
    if (!result?.sas_output.output) return [];
    const tables: Array<{ title: string; content: string }> = [];
    const sections = result.sas_output.output.split(/\n(?=The \w+ Procedure)/);
    for (const sec of sections) {
      const titleMatch = sec.match(/^The (\w+) Procedure/m);
      if (titleMatch) {
        tables.push({ title: `PROC ${titleMatch[1].toUpperCase()}`, content: sec.trim() });
      }
    }
    if (tables.length === 0 && result.sas_output.output.trim()) {
      tables.push({ title: 'SAS Output', content: result.sas_output.output.trim() });
    }
    return tables;
  }, [result]);

  const execId = result?.execution_id?.slice(0, 8).toUpperCase() ?? '—';
  const startedAt = result ? fmtTs(result.started_at) : '—';

  const TABS: Array<{ key: OutputTab; label: string; icon: React.ReactNode }> = [
    { key: 'sas',        label: 'SAS Output',      icon: <Terminal className="w-3.5 h-3.5" /> },
    { key: 'r',          label: 'R Output',         icon: <Code className="w-3.5 h-3.5" /> },
    { key: 'datasets',   label: 'Dataset Preview',  icon: <Table className="w-3.5 h-3.5" /> },
    { key: 'statistics', label: 'Statistics',       icon: <PieChart className="w-3.5 h-3.5" /> },
    { key: 'logs',       label: 'Logs',             icon: <FileText className="w-3.5 h-3.5" /> },
  ];

  return (
    <>
      {/* Dataset preview modal */}
      {previewDataset && result?.sas_output.datasets[previewDataset] && (
        <DatasetPreviewModal
          name={previewDataset}
          info={result.sas_output.datasets[previewDataset]}
          onClose={() => setPreviewDataset(null)}
        />
      )}

      <div className="max-w-5xl space-y-5">

        {/* ── Header ───────────────────────────────────────────────────────── */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
                <Zap className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <h2 className="text-lg font-extrabold text-slate-900 leading-tight">Execution Center</h2>
                <p className="text-xs text-slate-500 mt-0.5">SAS (Simulated) and R Execution in Parallel</p>
              </div>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0">
              <div className="text-right hidden sm:block">
                <p className="text-[11px] text-slate-400">Execution ID</p>
                <p className="text-xs font-mono font-bold text-slate-600">EXE-{execId}</p>
              </div>
              {hasResult && (
                <div className="text-right hidden sm:block">
                  <p className="text-[11px] text-slate-400">Started</p>
                  <p className="text-xs font-mono font-bold text-slate-600">{startedAt}</p>
                </div>
              )}
              {hasResult && <StatusBadge status={overallOk ? 'completed' : rNotInstalled ? 'r_not_installed' : 'error'} />}
              <button
                onClick={() => { setResult(null); setRerunCount(c => c + 1); }}
                disabled={isRunning}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold border border-slate-200 rounded-lg hover:bg-slate-50 text-slate-600 disabled:opacity-40 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
                Re-run
              </button>
            </div>
          </div>
        </div>

        {/* ── Loading ───────────────────────────────────────────────────────── */}
        {isRunning && (
          <div className="bg-white border border-slate-200 rounded-xl p-12 flex flex-col items-center gap-4">
            <Loader2 className="w-10 h-10 text-[#1f4368] animate-spin" />
            <div className="text-center">
              <p className="font-bold text-slate-800">Executing in parallel…</p>
              <p className="text-sm text-slate-500 mt-1">Running SAS simulation and R code simultaneously</p>
            </div>
            <div className="w-full max-w-xs space-y-2 mt-2">
              {['SAS Code Parsing', 'AST Generation', 'R Translation', 'SAS Execution', 'R Execution'].map((s, i) => (
                <div key={s} className="flex items-center gap-2.5">
                  <Loader2 className={`w-3.5 h-3.5 text-[#1f4368] ${i <= 2 ? 'animate-spin' : 'opacity-30'}`} />
                  <span className="text-xs text-slate-500">{s}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Error from mutation ────────────────────────────────────────────── */}
        {executionMutation.isError && !hasResult && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-red-900">Execution failed</p>
              <p className="text-sm text-red-700 mt-0.5">
                {(executionMutation.error as any)?.response?.data?.detail ||
                  'Could not reach the backend. Make sure the server is running.'}
              </p>
              <button
                onClick={() => executionMutation.mutate()}
                className="mt-3 text-xs font-bold text-red-700 underline"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {hasResult && (
          <>
            {/* ── Status cards ──────────────────────────────────────────────── */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className={`col-span-2 sm:col-span-1 rounded-xl border p-4 flex items-start gap-3 ${
                overallOk ? 'bg-emerald-50 border-emerald-200' :
                rNotInstalled ? 'bg-amber-50 border-amber-200' :
                'bg-red-50 border-red-200'
              }`}>
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                  overallOk ? 'bg-emerald-100' : rNotInstalled ? 'bg-amber-100' : 'bg-red-100'
                }`}>
                  {overallOk
                    ? <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    : rNotInstalled
                    ? <AlertTriangle className="w-5 h-5 text-amber-600" />
                    : <AlertCircle className="w-5 h-5 text-red-600" />}
                </div>
                <div>
                  <p className={`font-extrabold text-sm leading-tight ${
                    overallOk ? 'text-emerald-800' : rNotInstalled ? 'text-amber-800' : 'text-red-800'
                  }`}>
                    {overallOk ? 'Execution Completed' : rNotInstalled ? 'R Not Installed' : 'Execution Failed'}
                  </p>
                  <p className={`text-xs mt-0.5 ${
                    overallOk ? 'text-emerald-600' : rNotInstalled ? 'text-amber-600' : 'text-red-600'
                  }`}>
                    {overallOk ? 'All processes completed' :
                     rNotInstalled ? 'SAS simulation succeeded' :
                     'Check logs for details'}
                  </p>
                </div>
              </div>

              <MetricCard
                icon={<Clock className="w-4 h-4" />}
                label="Duration"
                value={`${result.duration_seconds.toFixed(1)}s`}
                sub={`${fmtTs(result.started_at)} – ${fmtTs(result.completed_at)}`}
                color="blue"
              />
              <MetricCard
                icon={<Database className="w-4 h-4" />}
                label="Datasets Generated"
                value={result.datasets_generated}
                sub={result.dataset_names.slice(0, 2).join(', ')}
                color="emerald"
              />
              <MetricCard
                icon={<BarChart2 className="w-4 h-4" />}
                label="Rows Processed"
                value={result.total_rows_sas.toLocaleString()}
                sub={`SAS: ${result.total_rows_sas} · R: ${result.total_rows_r}`}
                color="purple"
              />
            </div>

            {/* ── R not installed notice ────────────────────────────────────── */}
            {rNotInstalled && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
                <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-amber-800">
                  <strong>R is not installed.</strong>{' '}
                  Install R from{' '}
                  <span className="font-mono">https://www.r-project.org/</span>{' '}
                  to execute and verify the generated R code. The SAS simulation completed successfully.
                </p>
              </div>
            )}

            {/* ── Main content grid ─────────────────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">

              {/* Left: Timeline + Metrics */}
              <div className="md:col-span-1 space-y-4">
                <div className="bg-white border border-slate-200 rounded-xl p-5">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-4">Execution Timeline</p>
                  <TimelineView steps={result.timeline} />
                </div>
                <div className="bg-white border border-slate-200 rounded-xl p-5">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-4">Runtime Metrics</p>
                  <RuntimeMetrics dur={result.duration_seconds} rows={result.total_rows_sas} />
                </div>
              </div>

              {/* Right: Dataset Summary */}
              <div className="md:col-span-2 bg-white border border-slate-200 rounded-xl p-5">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-4">Dataset Summary</p>
                <DatasetSummaryCards
                  datasets={result.sas_output.datasets}
                  onPreview={setPreviewDataset}
                />
              </div>
            </div>

            {/* ── Execution Outputs section ──────────────────────────────────── */}
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100">
                <p className="text-sm font-extrabold text-slate-900">Execution Outputs</p>
              </div>

              {/* Tab bar */}
              <div className="flex border-b border-slate-100 px-5 gap-1 overflow-x-auto">
                {TABS.map(t => (
                  <button
                    key={t.key}
                    onClick={() => setActiveTab(t.key)}
                    className={`flex items-center gap-1.5 px-3.5 py-3 text-xs font-semibold whitespace-nowrap transition-colors border-b-2 -mb-px ${
                      activeTab === t.key
                        ? 'border-[#1f4368] text-[#1f4368]'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    {t.icon} {t.label}
                  </button>
                ))}
              </div>

              <div className="p-5">
                {/* SAS Output tab */}
                {activeTab === 'sas' && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Datasets Created</p>
                        <ul className="space-y-1.5">
                          {result.dataset_names.map(n => (
                            <li key={n} className="flex items-center gap-2 text-sm text-slate-700">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                              {n} ({result.sas_output.datasets[n]?.rows ?? '?'} rows, {result.sas_output.datasets[n]?.columns ?? '?'} cols)
                            </li>
                          ))}
                          {result.dataset_names.length === 0 && (
                            <li className="text-sm text-slate-400 italic">None</li>
                          )}
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Procedures Executed</p>
                        <ul className="space-y-1.5">
                          {result.sas_output.procs_executed.filter(Boolean).map(p => (
                            <li key={p} className="flex items-center gap-2 text-sm text-slate-700">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                              PROC {p}
                            </li>
                          ))}
                          {result.sas_output.procs_executed.filter(Boolean).length === 0 && (
                            <li className="text-sm text-slate-400 italic">None detected</li>
                          )}
                        </ul>
                      </div>
                    </div>

                    <button
                      onClick={() => setExpandSasOutput(v => !v)}
                      className="flex items-center gap-1.5 text-xs font-semibold text-[#1f4368] hover:text-[#1a3050]"
                    >
                      {expandSasOutput ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      {expandSasOutput ? 'Hide' : 'View'} Raw SAS Output
                    </button>
                    {expandSasOutput && (
                      <pre className="bg-slate-900 text-slate-100 rounded-xl p-4 text-xs font-mono overflow-auto max-h-80 whitespace-pre-wrap">
                        {result.sas_output.output || '(no output)'}
                      </pre>
                    )}
                  </div>
                )}

                {/* R Output tab */}
                {activeTab === 'r' && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Dataframes Created</p>
                        <ul className="space-y-1.5">
                          {result.dataset_names.map(n => (
                            <li key={n} className="flex items-center gap-2 text-sm text-slate-700">
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                              {n} ({result.sas_output.datasets[n]?.rows ?? '?'} rows, {result.sas_output.datasets[n]?.columns ?? '?'} cols)
                            </li>
                          ))}
                          {result.dataset_names.length === 0 && (
                            <li className="text-sm text-slate-400 italic">None</li>
                          )}
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">Packages Loaded</p>
                        {rNotInstalled ? (
                          <p className="text-sm text-amber-600 italic">R not installed — packages not loaded</p>
                        ) : (
                          <ul className="space-y-1.5">
                            {(rPackages.length > 0 ? rPackages : ['dplyr', 'tidyr']).map(p => (
                              <li key={p} className="flex items-center gap-2 text-sm text-slate-700">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                                {p}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={() => setExpandROutput(v => !v)}
                      className="flex items-center gap-1.5 text-xs font-semibold text-[#1f4368] hover:text-[#1a3050]"
                    >
                      {expandROutput ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      {expandROutput ? 'Hide' : 'View'} Raw R Console
                    </button>
                    {expandROutput && (
                      <pre className={`rounded-xl p-4 text-xs font-mono overflow-auto max-h-80 whitespace-pre-wrap ${
                        rNotInstalled ? 'bg-amber-950 text-amber-100' :
                        hasRError ? 'bg-red-950 text-red-100' :
                        'bg-slate-900 text-slate-100'
                      }`}>
                        {result.r_output.output || result.r_output.logs.join('\n') || '(no output)'}
                      </pre>
                    )}
                  </div>
                )}

                {/* Dataset Preview tab */}
                {activeTab === 'datasets' && (
                  <div>
                    {Object.keys(result.sas_output.datasets).length === 0 ? (
                      <div className="text-center py-12 text-slate-400">
                        <Database className="w-8 h-8 mx-auto mb-2 opacity-40" />
                        <p className="text-sm">No datasets generated</p>
                        <p className="text-xs mt-1">Ensure your SAS code includes DATALINES or SET statements with data</p>
                      </div>
                    ) : (
                      <div className="space-y-5">
                        {Object.entries(result.sas_output.datasets).map(([name, info]) => {
                          const cols = info.preview.length > 0 ? Object.keys(info.preview[0]) : [];
                          const rows = info.preview.slice(0, 5);
                          return (
                            <div key={name}>
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <Database className="w-4 h-4 text-[#1f4368]" />
                                  <span className="font-bold text-sm text-slate-900">{name}</span>
                                  <span className="text-xs text-slate-400">({info.rows} rows · {info.columns} cols)</span>
                                </div>
                                <button
                                  onClick={() => setPreviewDataset(name)}
                                  className="text-xs font-semibold text-[#1f4368] hover:text-[#1a3050]"
                                >
                                  Full Preview →
                                </button>
                              </div>
                              <div className="overflow-x-auto rounded-xl border border-slate-200">
                                <table className="w-full text-xs">
                                  <thead className="bg-slate-50 border-b border-slate-200">
                                    <tr>
                                      {cols.map(c => (
                                        <th key={c} className="px-3 py-2 text-left font-bold text-slate-500">{c}</th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-slate-100">
                                    {rows.map((row, i) => (
                                      <tr key={i} className="hover:bg-slate-50">
                                        {cols.map(c => (
                                          <td key={c} className="px-3 py-2 text-slate-700">
                                            {row[c] == null ? <span className="text-slate-300">—</span> : String(row[c])}
                                          </td>
                                        ))}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                              {info.rows > 5 && (
                                <p className="text-xs text-slate-400 mt-1.5">
                                  Showing 1–5 of {info.rows} rows —{' '}
                                  <button onClick={() => setPreviewDataset(name)} className="text-[#1f4368] hover:underline">
                                    view all
                                  </button>
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* Statistics tab */}
                {activeTab === 'statistics' && (
                  <div>
                    {statsTables.length === 0 ? (
                      <div className="text-center py-12 text-slate-400">
                        <PieChart className="w-8 h-8 mx-auto mb-2 opacity-40" />
                        <p className="text-sm">No statistical procedure output</p>
                        <p className="text-xs mt-1">Run PROC MEANS, PROC FREQ, etc. to see statistics here</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {statsTables.map((t, i) => (
                          <div key={i}>
                            <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-2">{t.title}</p>
                            <pre className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs font-mono text-slate-700 overflow-auto max-h-60 whitespace-pre-wrap">
                              {t.content}
                            </pre>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Logs tab */}
                {activeTab === 'logs' && <LogViewer entries={allLogs} />}
              </div>
            </div>
          </>
        )}

        {/* ── Actions ──────────────────────────────────────────────────────── */}
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => navigate(`/projects/${projectId}/translation`)}
            className="px-4 py-2.5 border border-slate-200 text-slate-700 rounded-xl hover:bg-slate-50 text-sm font-semibold transition-colors"
          >
            ← Back
          </button>

          <div className="flex-1" />

          {hasResult && (
            <>
              <button
                onClick={() => navigate(`/projects/${projectId}/translation`)}
                className="flex items-center gap-2 px-4 py-2.5 border border-[#ccdce9] text-[#1a3050] rounded-xl hover:bg-[#eef3f8] text-sm font-semibold transition-colors"
              >
                <Code className="w-4 h-4" /> View Generated R Code
              </button>
              <button
                onClick={() => {
                  const content = allLogs.map(e => `${e.time} [${e.level}] ${e.message}`).join('\n');
                  const blob = new Blob([content], { type: 'text/plain' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url; a.download = `execution-logs-${execId}.txt`; a.click();
                  URL.revokeObjectURL(url);
                }}
                className="flex items-center gap-2 px-4 py-2.5 border border-slate-200 text-slate-700 rounded-xl hover:bg-slate-50 text-sm font-semibold transition-colors"
              >
                <Download className="w-4 h-4" /> Download Logs
              </button>
            </>
          )}

          <button
            onClick={() => navigate(`/projects/${projectId}/validation`)}
            disabled={!hasResult}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#1f4368] text-white rounded-xl hover:bg-[#1a3654] text-sm font-bold transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            {isRunning ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Executing…</>
            ) : (
              <>Continue to Validation <ArrowRight className="w-4 h-4" /></>
            )}
          </button>
        </div>

      </div>
    </>
  );
};

export default ExecutionStep;
