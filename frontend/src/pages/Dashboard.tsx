import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Plus, FolderOpen, BookOpen, TrendingUp, Clock, CheckCircle2 } from 'lucide-react';
import { projectsApi } from '@/services/api';

const Dashboard: React.FC = () => {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.getAll,
  });

  const stats = {
    translationSuccess: 87,
    outputMatch: 96,
    projectsCompleted: projects.filter(p => p.status === 'validated').length,
    timeSaved: 680,
  };

  const recentProjects = projects.slice(0, 3);

  return (
    <div className="fade-in">
      {/* Hero Section */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-gray-900 mb-2">
          Welcome to SAS→R Platform
        </h1>
        <p className="text-gray-600">
          Automated translation, execution, and validation for clinical data
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-100 rounded-lg p-5">
          <p className="text-sm text-gray-600 mb-2">Translation success rate</p>
          <p className="text-3xl font-semibold text-gray-900">{stats.translationSuccess}%</p>
        </div>
        <div className="bg-gray-100 rounded-lg p-5">
          <p className="text-sm text-gray-600 mb-2">Output match accuracy</p>
          <p className="text-3xl font-semibold text-gray-900">{stats.outputMatch}%</p>
        </div>
        <div className="bg-gray-100 rounded-lg p-5">
          <p className="text-sm text-gray-600 mb-2">Projects completed</p>
          <p className="text-3xl font-semibold text-gray-900">{stats.projectsCompleted}</p>
        </div>
        <div className="bg-gray-100 rounded-lg p-5">
          <p className="text-sm text-gray-600 mb-2">Time saved</p>
          <p className="text-3xl font-semibold text-gray-900">{stats.timeSaved}h</p>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Projects */}
        <div className="lg:col-span-2 bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent projects</h2>

          {isLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
            </div>
          ) : recentProjects.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FolderOpen className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No projects yet. Create your first project to get started!</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentProjects.map((project) => (
                <Link
                  key={project.id}
                  to={`/projects/${project.id}/validation`}
                  className="block p-4 bg-gray-50 hover:bg-blue-50 rounded-lg transition-colors cursor-pointer border border-transparent hover:border-blue-200"
                >
                  <div className="flex justify-between items-center mb-2">
                    <p className="font-medium text-gray-900">{project.name}</p>
                    <StatusBadge status={project.status} />
                  </div>
                  <p className="text-sm text-gray-600">
                    {project.description || 'No description'} • {getRelativeTime(project.created_at)}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick actions</h2>

          <div className="space-y-3">
            <Link
              to="/projects/new"
              className="flex items-center justify-center gap-2 w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              <Plus className="w-5 h-5" />
              New Project
            </Link>

            <Link
              to="/projects"
              className="flex items-center justify-center gap-2 w-full px-4 py-3 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <FolderOpen className="w-5 h-5" />
              Browse Projects
            </Link>

            <button className="flex items-center justify-center gap-2 w-full px-4 py-3 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
              <BookOpen className="w-5 h-5" />
              View Documentation
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const config = {
    completed: { label: 'Completed', className: 'bg-green-100 text-green-800', icon: CheckCircle2 },
    validated: { label: 'Completed', className: 'bg-green-100 text-green-800', icon: CheckCircle2 },
    executing: { label: 'In Progress', className: 'bg-yellow-100 text-yellow-800', icon: Clock },
    translating: { label: 'In Progress', className: 'bg-yellow-100 text-yellow-800', icon: Clock },
    pending: { label: 'Pending', className: 'bg-gray-100 text-gray-800', icon: TrendingUp },
  }[status] || { label: 'Unknown', className: 'bg-gray-100 text-gray-800', icon: TrendingUp };

  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-md text-xs font-medium ${config.className}`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
};

const getRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours} hours ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
};

export default Dashboard;
