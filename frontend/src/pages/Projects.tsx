import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, FolderOpen, ArrowRight, FileCode2 } from 'lucide-react';
import { projectsApi } from '@/services/api';

const Projects: React.FC = () => {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.getAll,
  });

  const sortedProjects = [...projects].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Projects</h1>
          {!isLoading && (
            <p className="text-sm text-slate-500 mt-0.5">
              {projects.length} project{projects.length !== 1 ? 's' : ''}
            </p>
          )}
        </div>
        <Link
          to="/projects/new"
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#1f4368] text-white rounded-xl hover:bg-[#1a3654] transition-colors text-sm font-semibold shadow-sm"
        >
          <Plus className="w-4 h-4" />
          New Project
        </Link>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center py-24">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-[#1f4368] border-t-transparent" />
        </div>
      ) : sortedProjects.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/60">
                <th className="text-left px-6 py-3.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Project
                </th>
                <th className="text-left px-6 py-3.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="text-left px-6 py-3.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Created
                </th>
                <th className="text-right px-6 py-3.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedProjects.map((project) => (
                <tr
                  key={project.id}
                  className="hover:bg-slate-50/70 transition-colors group"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-[#eef3f8] flex items-center justify-center flex-shrink-0 group-hover:bg-blue-100 transition-colors">
                        <FileCode2 className="w-4 h-4 text-[#1f4368]" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-900 text-sm group-hover:text-[#1a3050] transition-colors truncate">
                          {project.name}
                        </p>
                        {project.description && (
                          <p className="text-xs text-slate-500 mt-0.5 truncate max-w-xs">
                            {project.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={project.status} />
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-500">
                    {new Date(project.created_at).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <Link
                      to={`/projects/${project.id}`}
                      className="inline-flex items-center gap-1 text-sm text-[#1f4368] hover:text-[#1a3050] font-semibold transition-colors"
                    >
                      Open <ArrowRight className="w-4 h-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const EmptyState: React.FC = () => (
  <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col items-center justify-center py-20 text-center px-8">
    <div className="w-16 h-16 bg-[#eef3f8] rounded-2xl flex items-center justify-center mb-5">
      <FolderOpen className="w-8 h-8 text-[#1f4368]" />
    </div>
    <h2 className="text-lg font-bold text-slate-900 mb-2">No projects yet</h2>
    <p className="text-sm text-slate-500 mb-6 max-w-sm leading-relaxed">
      Create your first conversion project to start transforming SAS scripts into production-ready R code.
    </p>
    <Link
      to="/projects/new"
      className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#1f4368] text-white text-sm font-semibold rounded-xl hover:bg-[#1a3654] transition-colors shadow-sm"
    >
      <Plus className="w-4 h-4" />
      Create First Project
    </Link>
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
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${cls}`}>
      {label}
    </span>
  );
};

export default Projects;
