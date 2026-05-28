import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Mail, Phone, User, LogOut, Edit2, Check, X } from 'lucide-react';
import { authApi } from '@/services/api';

function getInitials(name: string): string {
  return name
    .split(' ')
    .map(w => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

const MyProfile: React.FC = () => {
  const navigate = useNavigate();

  const { data: profile } = useQuery({
    queryKey: ['my-profile'],
    queryFn: authApi.getProfile,
    retry: false,
  });

  const name  = profile?.name  || 'Admin User';
  const email = profile?.email || 'admin@example.com';

  // Phone stored locally (no backend field)
  const [phone, setPhone]         = useState(() => localStorage.getItem('profile_phone') || '');
  const [editingPhone, setEditingPhone] = useState(false);
  const [phoneInput, setPhoneInput]     = useState(phone);

  const savePhone = () => {
    setPhone(phoneInput);
    localStorage.setItem('profile_phone', phoneInput);
    setEditingPhone(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('authToken');
    localStorage.removeItem('lastActivityAt');
    navigate('/login');
  };

  return (
    <div className="max-w-lg mx-auto fade-in">

      {/* Avatar card */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">

        {/* Top banner */}
        <div className="h-24 bg-gradient-to-r from-[#1f4368] to-[#24507e]" />

        {/* Avatar + name */}
        <div className="px-6 pb-6 -mt-12">
          <div className="flex items-end gap-4 mb-5">
            {profile?.profile_photo ? (
              <img
                src={profile.profile_photo}
                alt={name}
                className="w-20 h-20 rounded-full object-cover border-4 border-white shadow-md"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-[#1f4368] border-4 border-white shadow-md flex items-center justify-center flex-shrink-0">
                <span className="text-white text-2xl font-extrabold">{getInitials(name)}</span>
              </div>
            )}
            <div className="pb-1">
              <h1 className="text-xl font-extrabold text-slate-900 leading-tight">{name}</h1>
              <p className="text-sm text-slate-500">Administrator</p>
            </div>
          </div>

          {/* Info rows */}
          <div className="space-y-3">

            {/* Name */}
            <div className="flex items-center gap-3 p-3.5 bg-slate-50 rounded-xl border border-slate-100">
              <div className="w-8 h-8 bg-[#eef3f8] rounded-lg flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-[#1f4368]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wide">Full Name</p>
                <p className="text-sm font-semibold text-slate-900 truncate">{name}</p>
              </div>
            </div>

            {/* Email */}
            <div className="flex items-center gap-3 p-3.5 bg-slate-50 rounded-xl border border-slate-100">
              <div className="w-8 h-8 bg-[#eef3f8] rounded-lg flex items-center justify-center flex-shrink-0">
                <Mail className="w-4 h-4 text-[#1f4368]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wide">Email Address</p>
                <p className="text-sm font-semibold text-slate-900 truncate">{email}</p>
              </div>
            </div>

            {/* Phone */}
            <div className="flex items-center gap-3 p-3.5 bg-slate-50 rounded-xl border border-slate-100">
              <div className="w-8 h-8 bg-[#eef3f8] rounded-lg flex items-center justify-center flex-shrink-0">
                <Phone className="w-4 h-4 text-[#1f4368]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wide">Phone Number</p>
                {editingPhone ? (
                  <div className="flex items-center gap-2 mt-0.5">
                    <input
                      type="tel"
                      value={phoneInput}
                      onChange={e => setPhoneInput(e.target.value)}
                      placeholder="+1 (555) 000-0000"
                      className="flex-1 text-sm border border-slate-300 rounded-lg px-2.5 py-1 focus:outline-none focus:ring-2 focus:ring-[#8aaec9]"
                      autoFocus
                      onKeyDown={e => { if (e.key === 'Enter') savePhone(); if (e.key === 'Escape') setEditingPhone(false); }}
                    />
                    <button onClick={savePhone} className="p-1 rounded-lg text-green-600 hover:bg-green-50 transition-colors">
                      <Check className="w-4 h-4" />
                    </button>
                    <button onClick={() => { setEditingPhone(false); setPhoneInput(phone); }} className="p-1 rounded-lg text-slate-400 hover:bg-slate-200 transition-colors">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-900">
                      {phone || <span className="text-slate-400 font-normal">Not set</span>}
                    </p>
                    <button
                      onClick={() => { setPhoneInput(phone); setEditingPhone(true); }}
                      className="p-1 rounded-lg text-slate-400 hover:bg-slate-200 hover:text-slate-600 transition-colors"
                      title="Edit phone"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="mt-5 w-full flex items-center justify-center gap-2 py-2.5 border border-red-200 text-red-600 rounded-xl hover:bg-red-50 transition-colors text-sm font-semibold"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </div>

    </div>
  );
};

export default MyProfile;
