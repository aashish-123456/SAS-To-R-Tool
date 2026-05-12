import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

type LocalUser = { name: string; email: string; username: string; password: string };

const SignUp: React.FC = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', username: '', password: '' });
  const [error, setError] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.email || !form.username || !form.password) {
      setError('Please fill all fields.');
      return;
    }
    if (form.password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    const users: LocalUser[] = JSON.parse(localStorage.getItem('localUsers') || '[]');
    if (users.some((u) => u.username === form.username || u.email === form.email)) {
      setError('Username or email already exists.');
      return;
    }

    users.push(form);
    localStorage.setItem('localUsers', JSON.stringify(users));
    navigate('/login');
  };

  return <div className="min-h-screen bg-[#061a33] flex items-center justify-center p-4"><form onSubmit={submit} className="w-full max-w-md bg-[#061a33] border border-cyan-700/30 rounded-2xl p-8 space-y-3"><h1 className="text-2xl text-white font-bold">Create Account</h1><input className="w-full p-3 rounded bg-[#041e3a] text-white" placeholder="Full Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /><input className="w-full p-3 rounded bg-[#041e3a] text-white" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /><input className="w-full p-3 rounded bg-[#041e3a] text-white" placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /><input type="password" className="w-full p-3 rounded bg-[#041e3a] text-white" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />{error && <p className="text-rose-300 text-sm">{error}</p>}<button className="w-full py-3 rounded bg-cyan-500 text-white font-semibold">Sign Up</button><button type="button" onClick={() => navigate('/login')} className="w-full text-cyan-200 text-sm">Back to Login</button></form></div>;
};

export default SignUp;
