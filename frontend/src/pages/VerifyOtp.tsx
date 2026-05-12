import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '@/services/api';

const VerifyOtp: React.FC = () => {
  const navigate = useNavigate();
  const email = sessionStorage.getItem('otpEmail') || '';
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await authApi.verifyOtp({ email, otp });
      localStorage.setItem('isAuthenticated', 'true');
      localStorage.setItem('authToken', res.token || '');
      navigate('/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'OTP verification failed');
    }
  };
  return <div className="min-h-screen bg-[#061a33] flex items-center justify-center p-4"><form onSubmit={submit} className="w-full max-w-md bg-[#07274a]/90 border border-cyan-700/30 rounded-2xl p-8 space-y-3"><h1 className="text-2xl text-white font-bold">Verify OTP</h1><p className="text-cyan-100 text-sm">OTP sent to: {email || 'your email'}</p><input className="w-full p-3 rounded bg-[#041e3a] text-white" placeholder="Enter 6-digit OTP" value={otp} onChange={(e) => setOtp(e.target.value)} />{error && <p className="text-rose-300 text-sm">{error}</p>}<button className="w-full py-3 rounded bg-cyan-500 text-white font-semibold">Verify & Continue</button></form></div>;
};

export default VerifyOtp;
