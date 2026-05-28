import React, { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Plus, Upload, Eye, CheckCircle2, Clock,
  FileCode2, Download, Code2, Search, BarChart2,
  Shield, AlertTriangle, Sparkles, ArrowRight,
  Database, Activity, RefreshCw, Filter,
  ChevronUp, ChevronDown, XCircle, Info,
} from 'lucide-react';
import { projectsApi, Project } from '@/services/api';

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreColor(n: number) {
  if (n >= 95) return 'text-green-600';
  if (n >= 80) return 'text-blue-600';
  if (n >= 60) return 'text-yellow-600';
  return 'text-red-600';
}
function scoreBg(n: number) {
  if (n >= 95) return 'bg-green-100';
  if (n >= 80) return 'bg-blue-100';
  if (n >= 60) return 'bg-yellow-100';
  return 'bg-red-100';
}
function barColor(n: number) {
  if (n >= 95) return 'bg-green-500';
  if (n >= 80) return 'bg-blue-500';
  if (n >= 60) return 'bg-yellow-400';
  return 'bg-red-500';
}

const STATUS_MAP: Record<string, { label: string; dot: string; text: string; bg: string }> = {
  validated:   { label: 'Completed',    dot: 'bg-green-500',  text: 'text-green-700',  bg: 'bg-green-50 border-green-200' },
  completed:   { label: 'Completed',    dot: 'bg-green-500',  text: 'text-green-700',  bg: 'bg-green-50 border-green-200' },
  executed:    { label: 'Executed',     dot: 'bg-blue-500',   text: 'text-blue-700',   bg: 'bg-blue-50 border-blue-200' },
  translated:  { label: 'Translated',   dot: 'bg-[#1f4368]',  text: 'text-[#1f4368]', bg: 'bg-[#eef3f8] border-[#ccdce9]' },
  executing:   { label: 'Executing',    dot: 'bg-orange-400', text: 'text-orange-700', bg: 'bg-orange-50 border-orange-200' },
  translating: { label: 'Translating',  dot: 'bg-yellow-400', text: 'text-yellow-700', bg: 'bg-yellow-50 border-yellow-200' },
  uploaded:    { label: 'Uploaded',     dot: 'bg-purple-500', text: 'text-purple-700', bg: 'bg-purple-50 border-purple-200' },
  uploading:   { label: 'Uploading',    dot: 'bg-slate-400',  text: 'text-slate-700',  bg: 'bg-slate-50 border-slate-200' },
  pending:     { label: 'Pending',      dot: 'bg-slate-400',  text: 'text-slate-500',  bg: 'bg-slate-50 border-slate-200' },
};

function fmtDate(d: string) {
  const dt = new Date(d);
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function fmtTime(d: string) {
  return new Date(d).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// ── Sparkline ─────────────────────────────────────────────────────────────────
const Sparkline: React.FC<{ data: number[]; color: string }> = ({ data, color }) => {
  const W = 100, H = 32;
  if (data.length < 2) return null;
  const min = Math.min(...data), max = Math.max(...data), rng = max - min || 1;
  const pts = data.map((v, i) =>
    `${(i / (data.length - 1)) * W},${H - ((v - min) / rng) * (H - 6) - 3}`
  ).join(' ');
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="opacity-70">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

// ── Metric card ───────────────────────────────────────────────────────────────
const MetricCard: React.FC<{
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  value: React.ReactNode;
  sub: string;
  sparkData: number[];
  sparkColor: string;
  trend?: string;
}> = ({ icon, iconBg, label, value, sub, sparkData, sparkColor, trend }) => (
  <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-1">
    <div className={`w-10 h-10 ${iconBg} rounded-lg flex items-center justify-center mb-1`}>{icon}</div>
    <p className="text-2xl font-bold text-gray-900 leading-none">{value}</p>
    <p className="text-sm font-semibold text-gray-700">{label}</p>
    <p className="text-xs text-gray-400">{sub}</p>
    {trend && <p className="text-xs font-medium text-green-600">{trend}</p>}
    <div className="mt-2"><Sparkline data={sparkData} color={sparkColor} /></div>
  </div>
);

// ── Status badge ──────────────────────────────────────────────────────────────
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const cfg = STATUS_MAP[status] ?? { label: status, dot: 'bg-slate-400', text: 'text-slate-600', bg: 'bg-slate-50 border-slate-200' };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${cfg.bg} ${cfg.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
};

// ── Sort arrow ────────────────────────────────────────────────────────────────
const SortIcon: React.FC<{ col: string; active: string; dir: 'asc' | 'desc' }> = ({ col, active, dir }) => {
  if (active !== col) return <ChevronDown className="w-3 h-3 text-gray-300 ml-1 inline" />;
  return dir === 'asc'
    ? <ChevronUp className="w-3 h-3 text-[#1f4368] ml-1 inline" />
    : <ChevronDown className="w-3 h-3 text-[#1f4368] ml-1 inline" />;
};

// ── Pipeline steps ────────────────────────────────────────────────────────────
const STEPS = [
  { label: 'Upload',    desc: 'SAS Inputs' },
  { label: 'Preview',  desc: 'Validate Inputs' },
  { label: 'Translate',desc: 'SAS → R' },
  { label: 'Execute',  desc: 'Dual Runtime' },
  { label: 'Validate', desc: 'Reconciliation' },
  { label: 'Export',   desc: 'R Script' },
];

// ── Dashboard ─────────────────────────────────────────────────────────────────
const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const { data: projects = [], isLoading, refetch } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.getAll,
    staleTime: 0,
  });

  const [search, setSearch]     = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortCol, setSortCol]   = useState<string>('created_at');
  const [sortDir, setSortDir]   = useState<'asc' | 'desc'>('desc');

  // ── Derived stats ──────────────────────────────────────────────────────────
  const total      = projects.length;
  const completed  = projects.filter(p => ['validated', 'completed', 'executed', 'translated'].includes(p.status)).length;
  const validated  = projects.filter(p => ['validated', 'completed'].includes(p.status)).length;
  const inProg     = projects.filter(p => ['executing', 'translating', 'uploaded', 'uploading'].includes(p.status)).length;

  const confidences = projects.filter(p => p.overall_confidence != null).map(p => p.overall_confidence!);
  const avgConf     = confidences.length > 0
    ? (confidences.reduce((a, b) => a + b, 0) / confidences.length).toFixed(1)
    : '—';

  const totalRLines  = projects.reduce((s, p) => s + (p.r_lines ?? 0), 0);
  const totalWarnings = projects.reduce((s, p) => s + (p.warnings_count ?? 0), 0);

  // sparkline histories (build simple time-ordered series)
  const makeSpark = (vals: number[], fallback: number[]) =>
    vals.length >= 2 ? vals : fallback;

  const confSpark  = makeSpark(confidences.slice(-10), [80,85,88,90,91,92,93,95,94,96]);
  const totalSpark = makeSpark(projects.map((_, i) => i + 1), [1,2,3,5,8,10,13,16,20,total]);

  // ── History table ──────────────────────────────────────────────────────────
  const filtered = useMemo(() => {
    let rows = [...projects];
    if (search) {
      const q = search.toLowerCase();
      rows = rows.filter(p => p.name.toLowerCase().includes(q) || p.description?.toLowerCase().includes(q));
    }
    if (statusFilter !== 'all') {
      rows = rows.filter(p =>
        statusFilter === 'completed'
          ? ['validated', 'completed'].includes(p.status)
          : statusFilter === 'translated'
          ? ['translated', 'executed'].includes(p.status)
          : p.status === statusFilter
      );
    }
    rows.sort((a, b) => {
      let av: number | string, bv: number | string;
      if (sortCol === 'created_at') { av = a.created_at; bv = b.created_at; }
      else if (sortCol === 'confidence') { av = a.overall_confidence ?? -1; bv = b.overall_confidence ?? -1; }
      else if (sortCol === 'r_lines') { av = a.r_lines ?? 0; bv = b.r_lines ?? 0; }
      else if (sortCol === 'name') { av = a.name.toLowerCase(); bv = b.name.toLowerCase(); }
      else { av = a.status; bv = b.status; }
      if (av < bv) return sortDir === 'asc' ? -1 : 1;
      if (av > bv) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return rows;
  }, [projects, search, statusFilter, sortCol, sortDir]);

  const toggleSort = (col: string) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('desc'); }
  };

  const canExport = (p: Project) =>
    ['translated', 'executed', 'validated', 'completed'].includes(p.status);

  return (
    <div className="space-y-5 fade-in">

      {/* ── Welcome banner ── */}
      <div className="relative overflow-hidden bg-gradient-to-br from-[#1f4368] via-[#24507e] to-[#1a3a5c] rounded-2xl p-7 text-white shadow-lg">
        <div className="relative z-10 flex items-start justify-between">
          <div className="max-w-xl">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-5 h-5 text-blue-200" />
              <span className="text-blue-200 text-sm font-medium">Zuality · SAS → R Platform</span>
            </div>
            <h1 className="text-2xl font-extrabold mb-2 leading-tight tracking-tight">
              Welcome back, Admin User! 👋
            </h1>
            <p className="text-blue-100 text-sm mb-5 leading-relaxed">
              AI-powered semantic translation platform. Convert SAS programs to production-ready R scripts with{' '}
              <strong className="text-white">5-level equivalence validation</strong>.
            </p>
            <div className="flex gap-3">
              <Link
                to="/projects/new"
                className="inline-flex items-center gap-2 bg-white text-[#1f4368] px-5 py-2.5 rounded-xl font-bold text-sm hover:bg-blue-50 transition-colors shadow-sm"
              >
                <Plus className="w-4 h-4" />
                New Translation
              </Link>
            </div>
          </div>

          {/* SAS → R illustration */}
          <div className="hidden lg:flex items-center gap-4 mr-4 mt-2">
            <div className="flex flex-col items-center gap-1">
              <div className="w-16 h-20 bg-white/20 border border-white/20 rounded-xl flex flex-col items-center justify-center gap-2 backdrop-blur-sm">
                <span className="font-extrabold text-lg text-white">SAS</span>
                <div className="space-y-1 w-8">{[0,1,2].map(i=><div key={i} className="h-0.5 bg-white/30 rounded" />)}</div>
              </div>
            </div>
            <ArrowRight className="w-6 h-6 text-white/70" />
            <div className="w-10 h-10 bg-white/20 rounded-full border border-white/30 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <ArrowRight className="w-6 h-6 text-white/70" />
            <div className="flex flex-col items-center gap-1">
              <div className="w-16 h-20 bg-green-500/50 border border-white/20 rounded-xl flex flex-col items-center justify-center gap-2 backdrop-blur-sm">
                <span className="font-extrabold text-lg text-white">R</span>
                <div className="space-y-1 w-8">{[0,1,2].map(i=><div key={i} className="h-0.5 bg-white/30 rounded" />)}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Decorative blobs */}
        <div className="absolute -right-10 -top-10 w-64 h-64 bg-white/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute right-32 bottom-0 w-40 h-40 bg-[#1a3a5c]/30 rounded-full translate-y-1/2 blur-2xl pointer-events-none" />
      </div>

      {/* ── Pipeline steps strip ── */}
      <div className="bg-white border border-gray-200 rounded-xl px-6 py-4">
        <div className="flex items-center">
          {STEPS.map(({ label, desc }, idx) => (
            <React.Fragment key={label}>
              <div className="flex flex-col items-center text-center flex-shrink-0">
                <div className="w-9 h-9 rounded-full bg-[#1f4368] text-white ring-4 ring-[#ccdce9] flex items-center justify-center mb-1.5 text-xs font-bold shadow-sm">
                  {idx + 1}
                </div>
                <p className="text-[11px] font-semibold text-[#1f4368] leading-tight">{label}</p>
                <p className="text-[10px] text-gray-400 leading-tight max-w-[80px] mt-0.5">{desc}</p>
              </div>
              {idx < STEPS.length - 1 && (
                <div className="flex-1 mx-3 mt-[-14px]">
                  <div className="h-px bg-gradient-to-r from-[#8aaec9] to-[#ccdce9]" />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* ── Metric cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={<BarChart2 className="w-5 h-5 text-[#1f4368]" />}
          iconBg="bg-[#eef3f8]"
          label="Total Translations"
          value={total}
          sub="All-time conversions"
          sparkData={totalSpark}
          sparkColor="#1f4368"
          trend={total > 0 ? `+${total} this session` : undefined}
        />
        <MetricCard
          icon={<CheckCircle2 className="w-5 h-5 text-green-600" />}
          iconBg="bg-green-50"
          label="Completed"
          value={<span className="text-green-600">{completed}</span>}
          sub={`${validated} fully validated`}
          sparkData={makeSpark(Array.from({length:completed}, (_,i)=>i+1), [0,1,1,2,3,4,5,6,7,completed])}
          sparkColor="#16a34a"
        />
        <MetricCard
          icon={<Shield className="w-5 h-5 text-blue-600" />}
          iconBg="bg-blue-50"
          label="Avg Confidence"
          value={<span className={typeof avgConf === 'string' ? 'text-gray-400' : scoreColor(parseFloat(avgConf))}>{avgConf}{typeof avgConf !== 'string' ? '%' : ''}</span>}
          sub="Semantic equivalence score"
          sparkData={confSpark}
          sparkColor="#2563eb"
        />
        <MetricCard
          icon={<Clock className="w-5 h-5 text-orange-500" />}
          iconBg="bg-orange-50"
          label="In Progress"
          value={<span className="text-orange-500">{inProg}</span>}
          sub={`${totalRLines.toLocaleString()} total R lines generated`}
          sparkData={[1,2,1,3,2,1,2,3,2,inProg]}
          sparkColor="#f97316"
        />
      </div>

      {/* ── Secondary stats row ── */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white border border-gray-200 rounded-xl p-5 flex items-center gap-4">
          <div className="w-10 h-10 bg-purple-50 rounded-lg flex items-center justify-center">
            <FileCode2 className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <p className="text-xl font-bold text-gray-900">{totalRLines.toLocaleString()}</p>
            <p className="text-sm text-gray-500">Total R Lines Generated</p>
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5 flex items-center gap-4">
          <div className="w-10 h-10 bg-teal-50 rounded-lg flex items-center justify-center">
            <Database className="w-5 h-5 text-teal-600" />
          </div>
          <div>
            <p className="text-xl font-bold text-gray-900">
              {projects.reduce((s, p) => s + (p.datasets_validated ?? 0), 0)}
            </p>
            <p className="text-sm text-gray-500">Datasets Validated</p>
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-xl p-5 flex items-center gap-4">
          <div className="w-10 h-10 bg-yellow-50 rounded-lg flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
          </div>
          <div>
            <p className="text-xl font-bold text-gray-900">{totalWarnings}</p>
            <p className="text-sm text-gray-500">Translation Warnings</p>
          </div>
        </div>
      </div>

      {/* ── Translation History ── */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-[#1f4368]" />
            <h2 className="font-semibold text-gray-900">Translation History</h2>
            <span className="text-xs px-2 py-0.5 bg-[#eef3f8] text-[#1f4368] rounded-full font-medium border border-[#ccdce9]">
              {filtered.length} record{filtered.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => refetch()} className="p-2 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700" title="Refresh">
              <RefreshCw className="w-4 h-4" />
            </button>
            <Link to="/projects/new" className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1f4368] text-white rounded-lg text-sm font-medium hover:bg-[#1a3654]">
              <Plus className="w-4 h-4" />
              New
            </Link>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 px-5 py-3 border-b border-gray-100 bg-gray-50/60">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name or description…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#8aaec9]"
            />
          </div>
          {/* Status filter */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-4 h-4 text-gray-400" />
            {(['all', 'completed', 'translated', 'uploaded', 'pending'] as const).map(f => (
              <button
                key={f}
                onClick={() => setStatusFilter(f)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  statusFilter === f
                    ? 'bg-[#1f4368] text-white border-[#1f4368]'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#1f4368] border-t-transparent" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center">
            <Code2 className="w-10 h-10 mx-auto text-gray-200 mb-3" />
            <p className="text-gray-500 font-medium">No translations found</p>
            <p className="text-sm text-gray-400 mb-4">
              {search || statusFilter !== 'all' ? 'Try adjusting the filters' : 'Get started by creating a new translation'}
            </p>
            <Link to="/projects/new" className="inline-flex items-center gap-2 px-4 py-2 bg-[#1f4368] text-white rounded-lg text-sm font-medium hover:bg-[#1a3654]">
              <Plus className="w-4 h-4" />New Translation
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50/40">
                  {[
                    { col: 'name',       label: 'Project Name' },
                    { col: 'status',     label: 'Status' },
                    { col: 'r_lines',    label: 'R Lines' },
                    { col: 'confidence', label: 'Confidence' },
                    { col: 'issues',     label: 'Issues' },
                    { col: 'created_at', label: 'Translated On' },
                  ].map(({ col, label }) => (
                    <th
                      key={col}
                      className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer select-none hover:text-gray-700"
                      onClick={() => toggleSort(col)}
                    >
                      {label}
                      <SortIcon col={col} active={sortCol} dir={sortDir} />
                    </th>
                  ))}
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map(p => {
                  const conf = p.overall_confidence;
                  const issues = p.issues_count;
                  const totalIssues = issues ? issues.critical + issues.major + issues.minor : null;
                  return (
                    <tr key={p.id} className="hover:bg-[#f5f9fd] transition-colors group">

                      {/* Name */}
                      <td className="px-4 py-3.5">
                        <div>
                          <button
                            onClick={() => navigate(`/projects/${p.id}`)}
                            className="font-semibold text-[#1f4368] hover:text-[#1a3050] text-left leading-tight"
                          >
                            {p.name}
                          </button>
                          {p.description && (
                            <p className="text-xs text-gray-400 mt-0.5 truncate max-w-[200px]">{p.description}</p>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3.5">
                        <StatusBadge status={p.status} />
                      </td>

                      {/* R Lines */}
                      <td className="px-4 py-3.5 text-gray-600">
                        {p.r_lines ? (
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{p.r_lines}</span>
                            {p.sas_lines ? (
                              <span className="text-xs text-gray-400">/ {p.sas_lines} SAS</span>
                            ) : null}
                          </div>
                        ) : '—'}
                      </td>

                      {/* Confidence */}
                      <td className="px-4 py-3.5">
                        {conf != null ? (
                          <div className="flex items-center gap-2">
                            <div className={`px-2 py-0.5 rounded-full text-xs font-bold ${scoreBg(conf)} ${scoreColor(conf)}`}>
                              {conf.toFixed(1)}%
                            </div>
                            <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full ${barColor(conf)}`} style={{ width: `${conf}%` }} />
                            </div>
                          </div>
                        ) : (
                          <span className="text-xs text-gray-400">Not validated</span>
                        )}
                      </td>

                      {/* Issues */}
                      <td className="px-4 py-3.5">
                        {totalIssues != null ? (
                          totalIssues === 0 ? (
                            <div className="flex items-center gap-1 text-green-600">
                              <CheckCircle2 className="w-4 h-4" />
                              <span className="text-xs font-medium">None</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1.5">
                              {issues!.critical > 0 && (
                                <span className="flex items-center gap-0.5 text-xs text-red-600 font-medium">
                                  <XCircle className="w-3.5 h-3.5" />{issues!.critical}
                                </span>
                              )}
                              {issues!.major > 0 && (
                                <span className="flex items-center gap-0.5 text-xs text-yellow-600 font-medium">
                                  <AlertTriangle className="w-3.5 h-3.5" />{issues!.major}
                                </span>
                              )}
                              {issues!.minor > 0 && (
                                <span className="flex items-center gap-0.5 text-xs text-blue-600 font-medium">
                                  <Info className="w-3.5 h-3.5" />{issues!.minor}
                                </span>
                              )}
                            </div>
                          )
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>

                      {/* Date */}
                      <td className="px-4 py-3.5">
                        <div className="text-gray-600 text-xs">
                          <p className="font-medium">{fmtDate(p.translated_at ?? p.created_at)}</p>
                          <p className="text-gray-400">{fmtTime(p.translated_at ?? p.created_at)}</p>
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center justify-center gap-1 opacity-70 group-hover:opacity-100 transition-opacity">
                          {/* View workflow */}
                          <button
                            onClick={() => navigate(`/projects/${p.id}`)}
                            className="p-1.5 rounded-lg text-gray-500 hover:bg-[#eef3f8] hover:text-[#1f4368] transition-colors"
                            title="View workflow"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {/* View R code */}
                          {canExport(p) && (
                            <button
                              onClick={() => navigate(`/projects/${p.id}/report`)}
                              className="p-1.5 rounded-lg text-gray-500 hover:bg-green-50 hover:text-green-600 transition-colors"
                              title="View R Script"
                            >
                              <FileCode2 className="w-4 h-4" />
                            </button>
                          )}
                          {/* Download R script */}
                          {canExport(p) && (
                            <a
                              href={projectsApi.getRCodeDownloadUrl(p.id)}
                              target="_blank"
                              rel="noreferrer"
                              className="p-1.5 rounded-lg text-gray-500 hover:bg-[#eef3f8] hover:text-[#1f4368] transition-colors"
                              title="Download R Script"
                            >
                              <Download className="w-4 h-4" />
                            </a>
                          )}
                          {/* Continue / Validate */}
                          {p.status === 'executed' && (
                            <button
                              onClick={() => navigate(`/projects/${p.id}/validation`)}
                              className="p-1.5 rounded-lg text-gray-500 hover:bg-purple-50 hover:text-purple-600 transition-colors"
                              title="View Validation"
                            >
                              <Shield className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </td>

                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Footer */}
        {filtered.length > 0 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 bg-gray-50/40">
            <p className="text-xs text-gray-500">
              Showing {filtered.length} of {total} translation{total !== 1 ? 's' : ''}
            </p>
            <Link to="/projects/new" className="flex items-center gap-1.5 text-xs text-[#1f4368] font-medium hover:text-[#1a3050]">
              <Plus className="w-3.5 h-3.5" />Start new translation
            </Link>
          </div>
        )}
      </div>

      {/* ── Quick tips ── */}
      <div className="grid grid-cols-3 gap-4">
        {[
          {
            icon: <Upload className="w-5 h-5 text-[#1f4368]" />,
            bg: 'bg-[#eef3f8]',
            title: 'Upload SAS',
            body: 'Supports .sas files with DATA steps, PROCs, macros, and DATALINES.',
            link: '/projects/new',
            cta: 'Start Upload',
          },
          {
            icon: <Sparkles className="w-5 h-5 text-purple-500" />,
            bg: 'bg-purple-50',
            title: 'AI Translation',
            body: '6-engine pipeline: Parser → Intent → Flow → Package → Translate → Validate.',
            link: null,
            cta: null,
          },
          {
            icon: <Shield className="w-5 h-5 text-green-500" />,
            bg: 'bg-green-50',
            title: 'Semantic Validation',
            body: 'Structural · Functional · Statistical · Execution · Semantic — 5-level equivalence check.',
            link: null,
            cta: null,
          },
        ].map(({ icon, bg, title, body, link, cta }) => (
          <div key={title} className="bg-white border border-gray-200 rounded-xl p-5">
            <div className={`w-9 h-9 ${bg} rounded-lg flex items-center justify-center mb-3`}>{icon}</div>
            <h3 className="font-semibold text-gray-900 mb-1 text-sm">{title}</h3>
            <p className="text-xs text-gray-500 leading-relaxed mb-3">{body}</p>
            {link && cta && (
              <Link to={link} className="inline-flex items-center gap-1 text-xs text-[#1f4368] font-medium hover:text-[#1a3050]">
                {cta} <ArrowRight className="w-3 h-3" />
              </Link>
            )}
          </div>
        ))}
      </div>

    </div>
  );
};

export default Dashboard;
