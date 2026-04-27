import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Plus, FolderOpen, ArrowRight, FileCode2,
  CheckCircle2, Clock, Layers,
} from 'lucide-react';
import { projectsApi } from '@/services/api';

const Dashboard: React.FC = () => {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.getAll,
  });

  const totalProjects = projects.length;
  const completedProjects = projects.filter(p => p.status === 'validated').length;
  const activeProjects = projects.filter(p =>
    ['executing', 'translating', 'uploaded'].includes(p.status)
  ).length;

  const recentProjects = [...projects]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 6);

  return (
    <div className="fade-in space-y-7">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-600 via-blue-650 to-blue-700 shadow-lg p-8 text-white">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 bg-white/15 rounded-full px-3 py-1 text-xs font-semibold text-blue-100 mb-4 backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            SAS to R Automation Platform
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight mb-2 leading-tight">
            Transform SAS Code<br className="hidden sm:block" /> into Production-Ready R
          </h1>
          <p className="text-blue-100 text-sm leading-relaxed mb-6 max-w-lg">
            Upload your SAS scripts, get idiomatic R code via AST-based translation,
            run both runtimes side-by-side, and validate output consistency — all in one workflow.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/projects/new"
              className="inline-flex items-center gap-2 bg-white text-blue-700 px-5 py-2.5 rounded-xl font-bold text-sm hover:bg-blue-50 transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Start New Conversion
            </Link>
            <Link
              to="/projects"
              className="inline-flex items-center gap-2 bg-white/15 text-white px-5 py-2.5 rounded-xl font-semibold text-sm hover:bg-white/25 transition-colors backdrop-blur-sm"
            >
              <FolderOpen className="w-4 h-4" />
              My Projects
            </Link>
          </div>
        </div>

        {/* Decorative blobs */}
        <div className="absolute right-0 top-0 w-72 h-72 bg-blue-500/20 rounded-full -translate-y-1/3 translate-x-1/4 blur-3xl pointer-events-none" />
        <div className="absolute right-20 bottom-0 w-52 h-52 bg-blue-400/20 rounded-full translate-y-1/2 blur-2xl pointer-events-none" />
        <div className="absolute left-1/2 top-1/2 w-32 h-32 bg-white/5 rounded-full -translate-x-1/2 -translate-y-1/2 blur-xl pointer-events-none" />
      </div>

      {/* Stats Row — only real data */}
      {!isLoading && (
        <div className="grid grid-cols-3 gap-4">
          <StatCard
            icon={<Layers className="w-5 h-5" />}
            label="Total Projects"
            value={totalProjects}
            colorClass="text-slate-700 bg-slate-100"
            valueClass="text-slate-900"
          />
          <StatCard
            icon={<CheckCircle2 className="w-5 h-5" />}
            label="Completed"
            value={completedProjects}
            colorClass="text-emerald-700 bg-emerald-100"
            valueClass="text-emerald-700"
          />
          <StatCard
            icon={<Clock className="w-5 h-5" />}
            label="In Progress"
            value={activeProjects}
            colorClass="text-amber-700 bg-amber-100"
            valueClass="text-amber-700"
          />
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Projects */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-900 text-[15px]">Recent Projects</h2>
            <Link
              to="/projects"
              className="flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors"
            >
              View all <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent" />
            </div>
          ) : recentProjects.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
              <div className="w-14 h-14 bg-slate-100 rounded-2xl flex items-center justify-center mb-4">
                <FolderOpen className="w-7 h-7 text-slate-400" />
              </div>
              <h3 className="font-semibold text-slate-900 mb-1">No projects yet</h3>
              <p className="text-sm text-slate-500 mb-5 max-w-xs">
                Create your first conversion project to begin transforming SAS code into R.
              </p>
              <Link
                to="/projects/new"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus className="w-4 h-4" />
                New Project
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {recentProjects.map((project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}`}
                  className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50/80 transition-colors group"
                >
                  <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-100 transition-colors">
                    <FileCode2 className="w-4.5 h-4.5 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-slate-900 truncate text-sm group-hover:text-blue-700 transition-colors">
                      {project.name}
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5 truncate">
                      {project.description
                        ? project.description
                        : <span className="italic">No description</span>}
                      {' · '}
                      {getRelativeTime(project.created_at)}
                    </p>
                  </div>
                  <StatusBadge status={project.status} />
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-5">
          {/* Quick Actions */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h2 className="font-semibold text-slate-900 text-[15px] mb-4">Quick Actions</h2>
            <div className="space-y-2.5">
              <Link
                to="/projects/new"
                className="flex items-center gap-3 w-full px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors font-semibold text-sm shadow-sm"
              >
                <Plus className="w-4 h-4 flex-shrink-0" />
                New Conversion Project
              </Link>
              <Link
                to="/projects"
                className="flex items-center gap-3 w-full px-4 py-3 border border-slate-200 text-slate-700 rounded-xl hover:bg-slate-50 transition-colors text-sm font-medium"
              >
                <FolderOpen className="w-4 h-4 flex-shrink-0" />
                Browse All Projects
              </Link>
            </div>
          </div>

          {/* How It Works */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
            <h2 className="font-semibold text-slate-900 text-[15px] mb-4">How It Works</h2>
            <ol className="space-y-3.5">
              {HOW_IT_WORKS.map(({ step, title, desc, color }) => (
                <li key={step} className="flex items-start gap-3">
                  <span className={`w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5 ${color}`}>
                    {step}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-slate-900 leading-snug">{title}</p>
                    <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
};

const HOW_IT_WORKS = [
  { step: '1', title: 'Upload SAS Code', desc: 'Upload your .sas or .txt file, plus optional datasets', color: 'bg-blue-100 text-blue-700' },
  { step: '2', title: 'Auto-Translate', desc: 'AST-based conversion to idiomatic R using dplyr, tidyr', color: 'bg-violet-100 text-violet-700' },
  { step: '3', title: 'Dual Execution', desc: 'Run SAS simulation and R script side-by-side', color: 'bg-amber-100 text-amber-700' },
  { step: '4', title: 'Validate & Export', desc: 'Compare outputs numerically and download .R file', color: 'bg-emerald-100 text-emerald-700' },
];

const StatCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: number;
  colorClass: string;
  valueClass: string;
}> = ({ icon, label, value, colorClass, valueClass }) => (
  <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex items-center gap-4">
    <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${colorClass}`}>
      {icon}
    </div>
    <div>
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-extrabold leading-none mt-1 ${valueClass}`}>{value}</p>
    </div>
  </div>
);

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const config: Record<string, { label: string; cls: string }> = {
    validated: { label: 'Completed', cls: 'bg-emerald-100 text-emerald-700' },
    completed: { label: 'Completed', cls: 'bg-emerald-100 text-emerald-700' },
    executing: { label: 'Running', cls: 'bg-amber-100 text-amber-700' },
    translating: { label: 'Translating', cls: 'bg-blue-100 text-blue-700' },
    uploaded: { label: 'Uploaded', cls: 'bg-violet-100 text-violet-700' },
    pending: { label: 'Pending', cls: 'bg-slate-100 text-slate-500' },
  };
  const { label, cls } = config[status] ?? { label: status, cls: 'bg-slate-100 text-slate-500' };
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap flex-shrink-0 ${cls}`}>
      {label}
    </span>
  );
};

const getRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const diffMs = Date.now() - date.getTime();
  const diffH = Math.floor(diffMs / 3_600_000);
  const diffD = Math.floor(diffH / 24);
  if (diffH < 1) return 'Just now';
  if (diffH < 24) return `${diffH}h ago`;
  if (diffD === 1) return 'Yesterday';
  if (diffD < 7) return `${diffD}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

export default Dashboard;
