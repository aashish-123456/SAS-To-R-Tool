import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, AlertCircle, ArrowLeft } from 'lucide-react';

type LocalUser = { name: string; email: string; username: string; password: string };

const ForgotPassword: React.FC = () => {
  const navigate = useNavigate();
  const [emailOrUsername, setEmailOrUsername] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleReset = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (!emailOrUsername) {
      setError('Please enter your username or email address.');
      return;
    }

    const users: LocalUser[] = JSON.parse(localStorage.getItem('localUsers') || '[]');
    const userExists = users.some(
      (u) => u.email === emailOrUsername || u.username === emailOrUsername
    );

    if (!userExists) {
      setError('No account found with this username or email.');
      return;
    }

    setSuccess(true);
    setTimeout(() => {
      navigate('/login');
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-[#061a33] relative overflow-hidden flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(20,137,197,0.28),transparent_45%),radial-gradient(circle_at_80%_0%,rgba(17,81,130,0.35),transparent_40%)]" />

      <div className="relative w-full max-w-md rounded-2xl border border-cyan-700/30 bg-[#061a33] backdrop-blur-md">
        {/* Logo - Full width, no gaps */}
        <div className="text-center bg-gradient-to-b from-[#061a33] to-[#041e3a] py-2">
          <img src="/image.png" alt="R EvolveS" className="h-24 mx-auto object-contain block" />
        </div>

        <div className="p-8">
          <h2 className="text-2xl font-bold text-white text-center">Forgot your password?</h2>
          <p className="text-cyan-200/70 text-sm text-center mt-2">
            No worries! Enter your username or email and we'll send you instructions to reset it.
          </p>

          <form onSubmit={handleReset} className="space-y-3 mt-4">
          <div>
            <label className="text-cyan-200/70 text-sm block mb-2">Username or Email</label>
            <div className="relative">
              <Lock className="w-4 h-4 text-cyan-300 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={emailOrUsername}
                onChange={(e) => setEmailOrUsername(e.target.value)}
                placeholder="Enter your username or email address"
                className="w-full bg-[#041e3a] border border-cyan-700/40 rounded-lg py-3 pl-10 pr-3 text-white placeholder-cyan-200/30 focus:border-cyan-500 focus:outline-none transition"
              />
            </div>
          </div>

          {error && (
            <div className="flex gap-2 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          {success && (
            <div className="flex gap-2 bg-green-500/10 border border-green-500/30 rounded-lg p-3">
              <p className="text-sm text-green-300">✓ Reset instructions sent! Redirecting to login...</p>
            </div>
          )}

          <button
            type="submit"
            className="w-full py-3 rounded-lg bg-gradient-to-r from-cyan-500 to-teal-500 text-white font-semibold hover:from-cyan-600 hover:to-teal-600 transition duration-200 flex items-center justify-center gap-2"
          >
            Send Reset Link
          </button>

          <button
            type="button"
            onClick={() => navigate('/login')}
            className="w-full text-cyan-300 text-sm hover:text-cyan-200 flex items-center justify-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Sign In
          </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
