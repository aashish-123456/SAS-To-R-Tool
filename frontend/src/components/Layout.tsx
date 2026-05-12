import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Settings, UserCircle2, LogOut, KeyRound, ChevronDown } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
];

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(true);

  const isActive = (to: string) => {
    const path = location.pathname;
    if (to === '/dashboard') return path === '/' || path === '/dashboard';
    return path === to;
  };

  const handleLogout = () => {
    setMenuOpen(false);
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('authToken');
    localStorage.removeItem('lastActivityAt');
    window.location.href = '/login';
    alert('Logged out successfully.');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <aside className="w-60 bg-[#1f4368] border-r border-blue-900/40 flex flex-col flex-shrink-0">
        <div className="h-28 border-b border-blue-900/40 flex-shrink-0">
          <Link to="/dashboard" className="block w-full h-full">
            <img src="/zuality-logo.png" alt="Zuality" className="w-full h-full object-contain" />
          </Link>
        </div>

        <nav className="flex-1 py-3 px-3 overflow-y-auto">
          <ul className="space-y-0.5">
            {NAV_ITEMS.map(({ to, label, icon: Icon }, idx) => {
              const active = isActive(to);
              return (
                <li key={`${to}-${idx}`}>
                  <Link
                    to={to}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      active ? 'bg-white/15 text-white' : 'text-blue-100 hover:bg-white/10 hover:text-white'
                    }`}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    {label}
                  </Link>
                </li>
              );
            })}
            <li>
              <button
                onClick={() => setSettingsOpen((prev) => !prev)}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium text-blue-100 hover:bg-white/10 hover:text-white transition-colors"
              >
                <span className="flex items-center gap-3">
                  <Settings className="w-4 h-4 flex-shrink-0" />
                  Settings
                </span>
                <ChevronDown className={`w-4 h-4 transition-transform ${settingsOpen ? 'rotate-180' : ''}`} />
              </button>
              {settingsOpen && (
                <div className="mt-1 ml-3">
                  <button
                    onClick={() => navigate('/settings')}
                    className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                      isActive('/settings') ? 'bg-white/15 text-white' : 'text-blue-100 hover:bg-white/10 hover:text-white'
                    }`}
                  >
                    <KeyRound className="w-4 h-4" />
                    Change Password
                  </button>
                </div>
              )}
            </li>
          </ul>
        </nav>

        <div className="p-4 border-t border-slate-100 flex-shrink-0">
          <div className="bg-white/10 rounded-xl p-3">
            <p className="text-xs text-blue-100">Logout is available in the profile menu.</p>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-[#1f4368] border-b border-blue-900/40 flex items-center justify-end px-6 flex-shrink-0">
          <div className="relative">
            <button onClick={() => setMenuOpen((prev) => !prev)} className="group flex items-center gap-3 bg-[#1f4368] hover:bg-[#193a5a] text-white rounded-xl px-3 py-2 transition-all shadow-sm hover:shadow-md">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <UserCircle2 className="w-5 h-5 text-white" />
              </div>
              <div className="text-left leading-tight">
                <p className="text-[10px] text-blue-100">Signed in as</p>
                <p className="text-sm font-semibold">Admin User</p>
              </div>
              <ChevronDown className={`w-4 h-4 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
            </button>
            {menuOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white border border-slate-200 rounded-xl shadow-lg p-1.5 z-50">
                <button onClick={() => { setMenuOpen(false); navigate('/profile'); }} className="w-full text-left px-3 py-2 rounded-lg text-sm text-slate-700 hover:bg-slate-50">My Profile</button>
                <button onClick={handleLogout} className="w-full text-left px-3 py-2 rounded-lg text-sm text-red-600 hover:bg-red-50">Logout</button>
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">{children}</main>

        <footer className="flex-shrink-0 py-3 text-center text-[11px] text-slate-400 border-t border-slate-100 bg-white">
          © 2025 SAS to R Converter. All rights reserved.
        </footer>
      </div>
    </div>
  );
};

export default Layout;

