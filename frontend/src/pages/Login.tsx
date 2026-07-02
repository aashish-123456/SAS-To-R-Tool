import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Lock, User, AlertCircle } from 'lucide-react';

type LocalUser = { name: string; email: string; username: string; password: string };

const Login: React.FC = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!username || !password) return setError('Please enter username and password.');

    const signedUsers: LocalUser[] = JSON.parse(localStorage.getItem('localUsers') || '[]');
    const matched = signedUsers.find((u) => u.username === username && u.password === password);
    const isDefault = username === 'admin' && password === 'admin123';

    if (!matched && !isDefault) {
      setError('Invalid credentials. Use admin / admin123 or your signed-up account.');
      return;
    }

    localStorage.setItem('isAuthenticated', 'true');
    localStorage.setItem('lastActivityAt', String(Date.now()));
    localStorage.setItem('activeUsername', username);
    window.location.href = '/dashboard';
  };

  return (
    <div className="min-h-screen bg-[#061a33] relative overflow-hidden flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(20,137,197,0.28),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(17,81,130,0.35),transparent_40%)]" />

      <div className="relative w-full max-w-md rounded-2xl border border-cyan-700/30 bg-[#061a33] backdrop-blur-md overflow-hidden">
        {/* Logo - Full width, no gaps */}
        <div className="text-center bg-gradient-to-b from-[#061a33] to-[#041e3a] py-2">
          <img src="/image.png" alt="R EvolveS" className="h-24 mx-auto object-contain block" />
        </div>

        <div className="p-8">
          <h2 className="text-2xl font-bold text-white text-center">Welcome back</h2>
          <p className="text-cyan-200/70 text-sm text-center mt-1">Sign in to access your workspace</p>

          <form onSubmit={handleLogin} className="space-y-3 mt-5">
          <div>
            <label className="text-cyan-200/70 text-sm block mb-2">Username</label>
            <div className="relative">
              <User className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-3 text-white placeholder-cyan-200/30 focus:border-cyan-500 focus:outline-none transition"
              />
            </div>
          </div>

          <div>
            <label className="text-cyan-200/70 text-sm block mb-2">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-10 text-white placeholder-cyan-200/30 focus:border-cyan-500 focus:outline-none transition"
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-cyan-200/80 hover:text-cyan-200"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex items-center">
            <input type="checkbox" id="remember" className="w-4 h-4 rounded border border-cyan-700/40 bg-[#041e3a]" />
            <label htmlFor="remember" className="text-cyan-200/70 text-sm ml-2">Remember me</label>
            <a href="#" onClick={() => navigate('/forgot-password')} className="text-cyan-400 text-sm ml-auto hover:text-cyan-300">
              Forgot Password?
            </a>
          </div>

          {error && (
            <div className="flex gap-2 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          <button
            type="submit"
            className="w-full py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 text-white font-semibold hover:from-cyan-600 hover:to-teal-600 transition duration-200 flex items-center justify-center gap-2"
          >
            <Lock className="w-4 h-4" /> Sign In
          </button>

          <div className="text-center text-cyan-200/70 text-sm">or</div>

          <button
            type="button"
            onClick={() => navigate('/signup')}
            className="w-full py-3 rounded-lg border border-cyan-500/50 text-cyan-300 font-semibold hover:bg-cyan-500/10 transition duration-200 flex items-center justify-center gap-2"
          >
            <User className="w-4 h-4" /> Sign Up
          </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;
