import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

type LocalUser = { name: string; email: string; username: string; password: string };

const ForgotPassword: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const reset = () => {
    setError('');
    const users: LocalUser[] = JSON.parse(localStorage.getItem('localUsers') || '[]');
    const idx = users.findIndex((u) => u.email === email);
    if (idx === -1) {
      setError('No account found with this email.');
      return;
    }
    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    users[idx].password = newPassword;
    localStorage.setItem('localUsers', JSON.stringify(users));
    setMessage('Password updated. You can login now.');
    setTimeout(() => navigate('/login'), 800);
  };

  return <div className="min-h-screen bg-[#061a33] flex items-center justify-center p-4"><div className="w-full max-w-md bg-[#061a33] border border-cyan-700/30 rounded-2xl p-8 space-y-3"><h1 className="text-2xl text-white font-bold">Forgot Password</h1><input className="w-full p-3 rounded bg-[#041e3a] text-white" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} /><input type="password" className="w-full p-3 rounded bg-[#041e3a] text-white" placeholder="New Password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />{error && <p className="text-rose-300 text-sm">{error}</p>}{message && <p className="text-emerald-300 text-sm">{message}</p>}<button onClick={reset} className="w-full py-3 rounded bg-cyan-500 text-white font-semibold">Reset Password</button><button onClick={() => navigate('/login')} className="w-full text-cyan-200 text-sm">Back to Login</button></div></div>;
};

export default ForgotPassword;
