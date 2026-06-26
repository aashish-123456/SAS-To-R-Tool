import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Settings, ChevronDown, KeyRound,
  Bell, HelpCircle, Moon, Sun,
} from 'lucide-react';

interface LayoutProps { children: React.ReactNode; }

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen]       = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [darkMode, setDarkMode]       = useState(() => localStorage.getItem('darkMode') === 'true');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('darkMode', String(darkMode));
  }, [darkMode]);

  const isActive = (to: string) => {
    const path = location.pathname;
    if (to === '/dashboard') return path === '/' || path === '/dashboard';
    return path.startsWith(to);
  };

  const handleLogout = () => {
    setMenuOpen(false);
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('authToken');
    localStorage.removeItem('lastActivityAt');
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-[#0f172a]">

      {/* ── Sidebar ── */}
      <aside className="w-60 bg-[#1f4368] border-r border-blue-900/40 flex flex-col flex-shrink-0">

        {/* Zuality Logo */}
        <div className="h-28 border-b border-blue-900/40 flex-shrink-0">
          <Link to="/dashboard" className="block w-full h-full">
            <img src="/zuality-logo.png" alt="Zuality" className="w-full h-full object-contain" />
          </Link>
        </div>

        {/* Nav — Dashboard + Settings only */}
        <nav className="flex-1 py-3 px-3 overflow-y-auto">
          <ul className="space-y-0.5">

            {/* Dashboard */}
            <li>
              <Link
                to="/dashboard"
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive('/dashboard')
                    ? 'bg-white/15 text-white'
                    : 'text-blue-100 hover:bg-white/10 hover:text-white'
                }`}
              >
                <LayoutDashboard className="w-4 h-4 flex-shrink-0" />
                Dashboard
              </Link>
            </li>

            {/* Settings (expandable) */}
            <li>
              <button
                onClick={() => setSettingsOpen(p => !p)}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-blue-100 hover:bg-white/10 hover:text-white transition-colors"
              >
                <span className="flex items-center gap-3">
                  <Settings className="w-4 h-4 flex-shrink-0" />
                  Settings
                </span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${settingsOpen ? 'rotate-180' : ''}`} />
              </button>

              {settingsOpen && (
                <div className="mt-0.5 ml-3 pl-3 border-l border-white/10 space-y-0.5">

                  {/* Change Password */}
                  <button
                    onClick={() => navigate('/settings')}
                    className={`w-full text-left flex items-center gap-2.5 px-2 py-2 rounded-lg text-sm transition-colors ${
                      isActive('/settings') ? 'text-white bg-white/10' : 'text-blue-200 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    <KeyRound className="w-3.5 h-3.5 flex-shrink-0" />
                    Change Password
                  </button>

                  {/* Dark Mode toggle */}
                  <button
                    onClick={() => setDarkMode(p => !p)}
                    className="w-full flex items-center justify-between px-2 py-2 rounded-lg text-sm text-blue-200 hover:text-white hover:bg-white/10 transition-colors"
                  >
                    <span className="flex items-center gap-2.5">
                      {darkMode
                        ? <Sun className="w-3.5 h-3.5 flex-shrink-0" />
                        : <Moon className="w-3.5 h-3.5 flex-shrink-0" />
                      }
                      Dark Mode
                    </span>
                    {/* Toggle pill */}
                    <span className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors flex-shrink-0 ${darkMode ? 'bg-white/30' : 'bg-white/10'}`}>
                      <span className={`w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${darkMode ? 'translate-x-4' : 'translate-x-0'}`} />
                    </span>
                  </button>

                </div>
              )}
            </li>

          </ul>
        </nav>

      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 flex flex-col overflow-hidden">

        {/* Top header */}
        <header className="h-32 bg-white dark:bg-[#1e293b] border-b border-slate-200 dark:border-slate-700 flex items-center justify-between px-6 flex-shrink-0 shadow-sm">
          <div className="flex items-center">
            <img src="/evolves-logo.png" alt="R EvolveS" className="h-28 object-contain" />
          </div>

          <div className="flex items-center gap-2">
            {/* Help */}
            <button className="w-9 h-9 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors">
              <HelpCircle className="w-5 h-5" />
            </button>

            {/* Notifications */}
            <button className="relative w-9 h-9 rounded-lg flex items-center justify-center text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">3</span>
            </button>

            <div className="w-px h-6 bg-slate-200 mx-1" />

            {/* Profile menu */}
            <div className="relative">
              <button
                onClick={() => setMenuOpen(p => !p)}
                className="flex items-center gap-2.5 px-3 py-2 rounded-xl hover:bg-slate-100 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-[#1f4368] flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">AM</span>
                </div>
                <div className="text-left leading-tight">
                  <p className="text-sm font-semibold text-slate-900">Admin User</p>
                  <p className="text-[10px] text-slate-400">Administrator</p>
                </div>
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
              </button>

              {menuOpen && (
                <div className="absolute right-0 mt-1 w-48 bg-white dark:bg-[#1e293b] border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg p-1.5 z-50">
                  <button
                    onClick={() => { setMenuOpen(false); navigate('/profile'); }}
                    className="w-full text-left px-3 py-2 rounded-lg text-sm text-slate-700 hover:bg-slate-50"
                  >
                    My Profile
                  </button>
                  <button
                    onClick={() => { setMenuOpen(false); navigate('/settings'); }}
                    className="w-full text-left px-3 py-2 rounded-lg text-sm text-slate-700 hover:bg-slate-50"
                  >
                    Settings
                  </button>
                  <div className="my-1 h-px bg-slate-100" />
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-3 py-2 rounded-lg text-sm text-red-600 hover:bg-red-50"
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6 dark:bg-[#0f172a]">{children}</main>

        <footer className="flex-shrink-0 py-2.5 text-center text-[11px] text-slate-400 border-t border-slate-100 bg-white dark:bg-[#1e293b] dark:border-slate-700">
          © 2025 R EvolveS · All rights reserved.
        </footer>
      </div>
    </div>
  );
};

export default Layout;
