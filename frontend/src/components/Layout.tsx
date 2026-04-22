import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, FolderOpen, HelpCircle } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const getBreadcrumb = () => {
    const path = location.pathname;
    if (path === '/dashboard') return 'Dashboard';
    if (path === '/projects') return 'Projects';
    if (path === '/projects/new') return 'New Project';
    if (path.includes('/projects/')) {
      const parts = path.split('/');
      if (parts.includes('upload')) return 'New Project → Upload Files';
      if (parts.includes('translation')) return 'New Project → Translation';
      if (parts.includes('execution')) return 'New Project → Execution';
      if (parts.includes('validation')) return 'New Project → Validation';
      if (parts.includes('report')) return 'New Project → Final Report';
      return 'Project Details';
    }
    return 'Dashboard';
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#eef4ff_0%,_#f8fafc_45%,_#f1f5f9_100%)]">
      {/* Navigation Bar */}
      <nav className="sticky top-0 z-30 bg-white/85 backdrop-blur-md border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <div>
                <h1 className="text-xl font-semibold text-slate-900 tracking-tight">SAS To R Transformation</h1>
                <span className="inline-block mt-0.5 text-[11px] font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-full px-2 py-0.5">
                  Enterprise Workflow
                </span>
              </div>
              <span className="text-sm text-slate-500">{getBreadcrumb()}</span>
            </div>
            <div className="flex gap-2">
              <Link
                to="/dashboard"
                className={`px-4 py-2 text-sm rounded-md transition-colors ${
                  location.pathname === '/dashboard'
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-white hover:text-slate-900'
                }`}
              >
                <Home className="inline w-4 h-4 mr-2" />
                Dashboard
              </Link>
              <Link
                to="/projects"
                className={`px-4 py-2 text-sm rounded-md transition-colors ${
                  location.pathname === '/projects'
                    ? 'bg-slate-900 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-white hover:text-slate-900'
                }`}
              >
                <FolderOpen className="inline w-4 h-4 mr-2" />
                Projects
              </Link>
              <button className="px-4 py-2 text-sm text-slate-600 hover:bg-white hover:text-slate-900 rounded-md transition-colors">
                <HelpCircle className="inline w-4 h-4 mr-2" />
                Help
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  );
};

export default Layout;

