import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FolderOpen, HelpCircle, LayoutDashboard } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const SasToRLogo: React.FC = () => (
  <div className="flex items-center gap-3">
    <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center shadow-sm flex-shrink-0">
      <svg viewBox="0 0 24 24" className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 9h8M4 15h8" />
        <path d="M14 7l5 5-5 5" />
      </svg>
    </div>
    <div className="leading-none">
      <span className="block text-[15px] font-bold text-slate-900 tracking-tight">SAS → R</span>
      <span className="block text-[10px] font-semibold text-slate-400 tracking-widest uppercase mt-0.5">Converter</span>
    </div>
  </div>
);

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/projects', label: 'Projects', icon: FolderOpen },
  ];

  const isProjectsActive =
    location.pathname === '/projects' ||
    (location.pathname.startsWith('/projects') && location.pathname !== '/dashboard');

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_#eff6ff_0%,_#f8fafc_55%,_#f1f5f9_100%)]">
      {/* Brand stripe */}
      <div className="h-[3px] bg-gradient-to-r from-blue-500 via-blue-600 to-blue-500" />

      {/* Nav */}
      <nav className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200/80 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-[60px] flex items-center justify-between">
          <Link to="/dashboard" className="hover:opacity-80 transition-opacity">
            <SasToRLogo />
          </Link>

          <div className="flex items-center gap-0.5">
            {navLinks.map(({ to, label, icon: Icon }) => {
              const isActive =
                to === '/dashboard'
                  ? location.pathname === '/dashboard' || location.pathname === '/'
                  : isProjectsActive && to === '/projects';

              return (
                <Link
                  key={to}
                  to={to}
                  className={`flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium rounded-lg transition-all ${
                    isActive
                      ? 'text-blue-700 bg-blue-50'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              );
            })}

            <div className="w-px h-5 bg-slate-200 mx-1" />

            <button className="flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-all">
              <HelpCircle className="w-4 h-4" />
              Help
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  );
};

export default Layout;
