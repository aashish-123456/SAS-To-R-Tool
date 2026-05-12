import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Lock, User } from 'lucide-react';

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

  return (<div className="min-h-screen bg-[#061a33] relative overflow-hidden flex items-center justify-center px-4"><div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(20,137,197,0.28),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(17,81,130,0.35),transparent_40%)]" /><div className="relative w-full max-w-md rounded-2xl border border-cyan-700/30 bg-[#061a33] backdrop-blur-md p-8"><div className="text-center mb-7"><img src="/zuality-logo.png" alt="Zuality" className="h-20 mx-auto object-contain bg-[#061a33]" /><h1 className="text-3xl font-bold text-white mt-4">Welcome Back</h1></div><form onSubmit={handleLogin} className="space-y-4"><div className="relative"><User className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" /><input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-3 text-white" /></div><div className="relative"><Lock className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" /><input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-10 text-white" /><button type="button" onClick={() => setShowPassword((s) => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-cyan-200/80">{showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}</button></div>{error && <p className="text-sm text-rose-300">{error}</p>}<button type="submit" className="w-full py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 text-white font-semibold">Log In</button><div className="flex items-center justify-between text-sm pt-2"><button type="button" onClick={() => navigate('/signup')} className="text-cyan-300 hover:text-cyan-200">Sign Up</button><button type="button" onClick={() => navigate('/forgot-password')} className="text-cyan-300 hover:text-cyan-200">Forgot Password?</button></div></form></div></div>);
};

export default Login;
