import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Plus, Upload, Eye, CheckCircle2, Clock, TrendingUp,
  FileText, Code2, Download, Play,
} from 'lucide-react';
import { projectsApi } from '@/services/api';

// ── Sparkline ──────────────────────────────────────────────────
const Sparkline: React.FC<{ data: number[]; color: string }> = ({ data, color }) => {
  const W = 130, H = 40;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const rng = max - min || 1;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / rng) * (H - 6) - 3}`)
    .join(' ');
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};

// ── File illustration in the welcome card ───────────────────────
const FileCard: React.FC<{ label: string; bg: string }> = ({ label, bg }) => (
  <div className={`${bg} rounded-xl shadow-lg w-[72px] h-[88px] flex flex-col items-center justify-center gap-2`}>
    <span className="text-white font-extrabold text-base tracking-wide">{label}</span>
    <div className="space-y-1 w-10">
      {[0, 1, 2].map(i => (
        <div key={i} className="h-[3px] bg-white/40 rounded-full" />
      ))}
    </div>
  </div>
);

// ── Workflow step icon ──────────────────────────────────────────
const STEP_ICONS = [Upload, Code2, Code2, Play, CheckCircle2, Download];

// ── Stat card ──────────────────────────────────────────────────
const StatCard: React.FC<{
  icon: React.ReactNode;
  iconBg: string;
  value: string | number;
  valueColor: string;
  title: string;
  sub: string;
  sparkData: number[];
  sparkColor: string;
}> = ({ icon, iconBg, value, valueColor, title, sub, sparkData, sparkColor }) => (
  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col">
    <div className={`w-10 h-10 ${iconBg} rounded-full flex items-center justify-center mb-3`}>
      {icon}
    </div>
    <p className={`text-2xl font-extrabold leading-none mb-1 ${valueColor}`}>{value}</p>
    <p className="text-sm font-semibold text-slate-800 mb-0.5">{title}</p>
    <p className="text-[11px] text-slate-400 mb-3">{sub}</p>
    <div className="mt-auto">
      <Sparkline data={sparkData} color={sparkColor} />
    </div>
  </div>
);

// ── Status config ───────────────────────────────────────────────
const STATUS: Record<string, { label: string; cls: string }> = {
  validated:  { label: 'Completed',  cls: 'bg-green-100 text-green-700' },
  completed:  { label: 'Completed',  cls: 'bg-green-100 text-green-700' },
  executing:  { label: 'In Progress',cls: 'bg-orange-100 text-orange-700' },
  translating:{ label: 'Validating', cls: 'bg-blue-100 text-blue-700' },
  uploaded:   { label: 'Uploaded',   cls: 'bg-violet-100 text-violet-700' },
  pending:    { label: 'Pending',    cls: 'bg-slate-100 text-slate-500' },
};

// ── Sample code for Quick Preview ──────────────────────────────
const SAS_SAMPLE = `data patients;
  set sdtm.dm;
  where age > 18;
  if sex = 'M' then gender = 'Male';
  else gender = 'Female';
run;`;

const R_SAMPLE = `patients <- subset(sdtm_dm, age > 18)
patients$gender <- ifelse(
  patients$sex == 'M', 'Male', 'Female'
)`;

// ── Fake sparkline series (trend shapes) ───────────────────────
const SPARK = {
  total:    [10, 13, 12, 16, 19, 21, 23, 24, 26, 28],
  done:     [ 7, 10,  9, 13, 15, 17, 19, 20, 22, 23],
  accuracy: [86, 89, 90, 88, 91, 92, 90, 93, 92, 92],
  progress: [ 3,  3,  3,  4,  4,  5,  6,  4,  5,  5],
};

// ── Dashboard ──────────────────────────────────────────────────
const Dashboard: React.FC = () => {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.getAll,
  });

  const total     = projects.length;
  const completed = projects.filter(p => ['validated', 'completed'].includes(p.status)).length;
  const inProg    = projects.filter(p => ['executing', 'translating', 'uploaded'].includes(p.status)).length;
  const accuracy  = total > 0 ? ((completed / total) * 100).toFixed(1) + '%' : '—';

  const recent = [...projects]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <div className="fade-in space-y-5">

      {/* ── Welcome Banner ── */}
      <div className="relative overflow-hidden bg-gradient-to-r from-blue-600 to-blue-700 rounded-2xl p-8 text-white shadow-md">
        <div className="relative z-10 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-extrabold mb-1.5 tracking-tight">
              Welcome back, Admin User! 👋
            </h1>
            <p className="text-blue-100 text-sm mb-6 leading-relaxed">
              Convert your SAS programs to R with AI-powered precision.
            </p>
            <div className="flex gap-3">
              <Link
                to="/projects/new"
                className="inline-flex items-center gap-2 bg-white text-blue-700 px-5 py-2.5 rounded-xl font-bold text-sm hover:bg-blue-50 transition-colors shadow-sm"
              >
                <Plus className="w-4 h-4" />
                New Conversion
              </Link>
              <Link
                to="/projects/new"
                className="inline-flex items-center gap-2 bg-white/15 text-white px-5 py-2.5 rounded-xl font-semibold text-sm hover:bg-white/25 transition-colors border border-white/30 backdrop-blur-sm"
              >
                <Upload className="w-4 h-4" />
                Upload SAS File
              </Link>
            </div>
          </div>

          {/* File illustration */}
          <div className="hidden lg:flex items-center gap-5 mr-6">
            <FileCard label="SAS" bg="bg-blue-500" />
            <span className="text-4xl font-bold text-white/70">→</span>
            <FileCard label="R" bg="bg-emerald-500" />
          </div>
        </div>

        {/* Decorative blobs */}
        <div className="absolute right-0 top-0 w-64 h-64 bg-blue-500/20 rounded-full -translate-y-1/3 translate-x-1/4 blur-3xl pointer-events-none" />
        <div className="absolute right-20 bottom-0 w-40 h-40 bg-blue-400/20 rounded-full translate-y-1/2 blur-2xl pointer-events-none" />
      </div>

      {/* ── Workflow Steps ── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
        <div className="flex items-start">
          {[
            { title: 'Upload', desc: 'Upload SAS Inputs' },
            { title: 'Preview', desc: 'Input Validation Preview' },
            { title: 'Translate', desc: 'SAS to R Translation' },
            { title: 'Execute', desc: 'Dual Runtime Execution' },
            { title: 'Validate', desc: 'Output Reconciliation' },
            { title: 'Export', desc: 'Export R Script' },
          ].map(({ title, desc }, idx) => {
            const Icon = STEP_ICONS[idx];
            return (
              <React.Fragment key={title}>
                <div className="flex flex-col items-center text-center flex-shrink-0">
                  <div className="w-10 h-10 rounded-full bg-blue-600 text-white ring-4 ring-blue-100 flex items-center justify-center mb-2 shadow-sm">
                    <Icon className="w-[18px] h-[18px]" />
                  </div>
                  <p className="text-[11px] font-semibold text-blue-700 mb-1 leading-tight">
                    {idx + 1}. {title}
                  </p>
                  <p className="text-[10px] text-slate-400 leading-tight max-w-[90px]">{desc}</p>
                </div>
                {idx < 5 && (
                  <div className="flex-1 px-3 mt-5">
                    <div className="h-0.5 rounded-full bg-slate-200" />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* ── Stat Cards ── */}
      {!isLoading && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            icon={<FileText className="w-[18px] h-[18px]" />}
            iconBg="bg-blue-50"
            value={total}
            valueColor="text-blue-600"
            title="Total Conversions"
            sub="All time conversions"
            sparkData={SPARK.total}
            sparkColor="#1f4368"
          />
          <StatCard
            icon={<CheckCircle2 className="w-5 h-5 text-emerald-600" />}
            iconBg="bg-emerald-50"
            value={completed}
            valueColor="text-emerald-600"
            title="Completed"
            sub="Successfully converted"
            sparkData={SPARK.done}
            sparkColor="#10b981"
          />
          <StatCard
            icon={<TrendingUp className="w-5 h-5 text-violet-600" />}
            iconBg="bg-violet-50"
            value={accuracy}
            valueColor="text-violet-600"
            title="Validation Accuracy"
            sub="Average accuracy score"
            sparkData={SPARK.accuracy}
            sparkColor="#8b5cf6"
          />
          <StatCard
            icon={<Clock className="w-5 h-5 text-orange-500" />}
            iconBg="bg-orange-50"
            value={inProg}
            valueColor="text-orange-500"
            title="In Progress"
            sub="Currently processing"
            sparkData={SPARK.progress}
            sparkColor="#f97316"
          />
        </div>
      )}

      {/* ── Bottom Row ── */}
      <div className="grid grid-cols-5 gap-5">

        {/* Recent Conversions */}
        <div className="col-span-3 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-900 text-[15px]">Recent Conversions</h2>
            <Link to="/projects" className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors">
              View All
            </Link>
          </div>

          {isLoading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" />
            </div>
          ) : recent.length === 0 ? (
            <div className="py-12 text-center text-sm text-slate-400">
              No conversions yet.{' '}
              <Link to="/projects/new" className="text-blue-600 font-semibold hover:underline">Start one</Link>.
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60">
                  {['File Name', 'Lines of Code', 'Status', 'Accuracy', 'Converted On', 'Action'].map(h => (
                    <th
                      key={h}
                      className={`py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider ${h === 'Action' ? 'text-center px-4' : 'text-left px-4'} ${h === 'File Name' ? 'pl-6' : ''}`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {recent.map(p => {
                  const { label, cls } = STATUS[p.status] ?? { label: p.status, cls: 'bg-slate-100 text-slate-500' };
                  const isComplete = ['validated', 'completed'].includes(p.status);
                  return (
                    <tr key={p.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="pl-6 pr-4 py-3.5 text-sm font-medium text-blue-600 truncate max-w-[130px]">
                        {p.name}
                      </td>
                      <td className="px-4 py-3.5 text-sm text-slate-400">—</td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${cls}`}>
                          {label}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-sm text-slate-400">
                        {isComplete ? '—' : '—'}
                      </td>
                      <td className="px-4 py-3.5 text-[11px] text-slate-400 whitespace-nowrap">
                        {new Date(p.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        {' '}
                        {new Date(p.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="px-4 py-3.5 text-center">
                        <Link
                          to={`/projects/${p.id}`}
                          className="inline-flex items-center justify-center w-7 h-7 rounded-full hover:bg-blue-50 transition-colors text-slate-400 hover:text-blue-600"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Quick Preview */}
        <div className="col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 flex-shrink-0">
            <h2 className="font-semibold text-slate-900 text-[15px]">Quick Preview</h2>
            <Link to="/projects" className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors flex items-center gap-1">
              View Full Conversion →
            </Link>
          </div>
          <div className="flex-1 grid grid-cols-2 gap-3 p-4">
            {/* SAS */}
            <div className="flex flex-col min-h-0">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">SAS Code (Sample)</p>
              <div className="flex-1 bg-slate-950 rounded-lg p-3 font-mono text-[11px] text-slate-300 overflow-auto">
                {SAS_SAMPLE.split('\n').map((line, i) => (
                  <div key={i} className="flex gap-2.5 leading-relaxed">
                    <span className="text-slate-600 select-none w-3 flex-shrink-0 text-right">{i + 1}</span>
                    <span>{line}</span>
                  </div>
                ))}
              </div>
            </div>
            {/* R */}
            <div className="flex flex-col min-h-0">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">R Code (Converted)</p>
              <div className="flex-1 bg-slate-950 rounded-lg p-3 font-mono text-[11px] text-slate-300 overflow-auto">
                {R_SAMPLE.split('\n').map((line, i) => (
                  <div key={i} className="flex gap-2.5 leading-relaxed">
                    <span className="text-slate-600 select-none w-3 flex-shrink-0 text-right">{i + 1}</span>
                    <span>{line}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Dashboard;

