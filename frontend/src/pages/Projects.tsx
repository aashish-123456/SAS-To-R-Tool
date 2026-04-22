import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, ExternalLink } from 'lucide-react';
import { projectsApi } from '@/services/api';

const Projects: React.FC = () => {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.getAll,
  });

  return (
    <div className="fade-in">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">All Projects</h1>
        <Link
          to="/projects/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          New Project
        </Link>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-700">
                  Project name
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-700">
                  Status
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-700">
                  Match rate
                </th>
                <th className="text-left px-6 py-3 text-sm font-medium text-gray-700">
                  Created
                </th>
                <th className="text-center px-6 py-3 text-sm font-medium text-gray-700">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {projects.map((project) => (
                <tr
                  key={project.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{project.name}</div>
                    {project.description && (
                      <div className="text-sm text-gray-500">{project.description}</div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={project.status} />
                  </td>
                  <td className="px-6 py-4 text-gray-700">
                    {project.status === 'validated' ? '96%' : '—'}
                  </td>
                  <td className="px-6 py-4 text-gray-700">
                    {new Date(project.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <Link
                      to={`/projects/${project.id}`}
                      className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"
                    >
                      View
                      <ExternalLink className="w-4 h-4" />
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

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const config = {
    completed: { label: 'Completed', className: 'bg-green-100 text-green-800' },
    validated: { label: 'Completed', className: 'bg-green-100 text-green-800' },
    executing: { label: 'Executing', className: 'bg-yellow-100 text-yellow-800' },
    translating: { label: 'Translating', className: 'bg-yellow-100 text-yellow-800' },
    pending: { label: 'Pending', className: 'bg-gray-100 text-gray-800' },
  }[status] || { label: status, className: 'bg-gray-100 text-gray-800' };

  return (
    <span className={`inline-block px-3 py-1 rounded-md text-xs font-medium ${config.className}`}>
      {config.label}
    </span>
  );
};

export default Projects;
