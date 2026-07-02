import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, User, Mail, Lock, AlertCircle } from 'lucide-react';

type LocalUser = { name: string; email: string; username: string; password: string };

const SignUp: React.FC = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', username: '', password: '', confirmPassword: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [error, setError] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!form.name || !form.email || !form.username || !form.password || !form.confirmPassword) {
      setError('Please fill all fields.');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(form.email)) {
      setError('Please enter a valid email address.');
      return;
    }

    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (!agreedToTerms) {
      setError('Please agree to the Terms of Use and Privacy Policy.');
      return;
    }

    const users: LocalUser[] = JSON.parse(localStorage.getItem('localUsers') || '[]');
    if (users.some((u) => u.username === form.username || u.email === form.email)) {
      setError('Username or email already exists.');
      return;
    }

    users.push({ name: form.name, email: form.email, username: form.username, password: form.password });
    localStorage.setItem('localUsers', JSON.stringify(users));
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[#061a33] relative overflow-hidden flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(20,137,197,0.28),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(17,81,130,0.35),transparent_40%)]" />

      <div className="relative w-full max-w-md rounded-2xl border border-cyan-700/30 bg-[#061a33] backdrop-blur-md max-h-[90vh] overflow-y-auto overflow-x-hidden">
        {/* Logo - Full width, no gaps */}
        <div className="text-center bg-gradient-to-b from-[#061a33] to-[#041e3a] py-2">
          <img src="/image.png" alt="R EvolveS" className="h-24 mx-auto object-contain block" />
        </div>

        <div className="p-8">
          <h2 className="text-2xl font-bold text-white text-center">Create your account</h2>
          <p className="text-cyan-200/70 text-sm text-center mt-1">Join RevolveS to get started</p>

          <form onSubmit={submit} className="space-y-3 mt-4">
          <div>
            <label className="text-cyan-200/70 text-sm block mb-2">Full Name</label>
            <div className="relative">
              <User className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                placeholder="Enter your full name"
                className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-3 text-white placeholder-cyan-200/30 focus:border-cyan-500 focus:outline-none transition"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="text-cyan-200/70 text-sm block mb-2">Username</label>
            <div className="relative">
              <User className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                placeholder="Choose a username"
                className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-3 text-white placeholder-cyan-200/30 focus:border-cyan-500 focus:outline-none transition"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="text-cyan-200/70 text-sm block mb-2">Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="email"
                placeholder="Enter your email address"
                className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-3 text-white placeholder-cyan-200/30 focus:border-cyan-500 focus:outline-none transition"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="text-cyan-200/70 text-sm block mb-2">Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Create a password"
                className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-10 text-white placeholder-cyan-200/30 focus:border-cyan-500 focus:outline-none transition"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-cyan-200/80 hover:text-cyan-200"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="text-cyan-200/70 text-sm block mb-2">Confirm Password</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                placeholder="Confirm your password"
                className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-10 text-white placeholder-cyan-200/30 focus:border-cyan-500 focus:outline-none transition"
                value={form.confirmPassword}
                onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-cyan-200/80 hover:text-cyan-200"
              >
                {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <input
              type="checkbox"
              id="terms"
              checked={agreedToTerms}
              onChange={(e) => setAgreedToTerms(e.target.checked)}
              className="w-4 h-4 rounded border border-cyan-700/40 bg-[#041e3a] mt-1 cursor-pointer"
            />
            <label htmlFor="terms" className="text-xs text-cyan-200/70">
              I agree to the <span className="text-cyan-300">Terms of Use</span> and <span className="text-cyan-300">Privacy Policy</span>
            </label>
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
            <User className="w-4 h-4" /> Sign Up
          </button>

          <div className="text-center text-cyan-200/70 text-sm">or</div>

          <button
            type="button"
            onClick={() => navigate('/login')}
            className="w-full text-cyan-300 text-sm hover:text-cyan-200"
          >
            Already have an account? Sign In
          </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SignUp;
