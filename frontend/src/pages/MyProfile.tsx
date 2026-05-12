import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { authApi } from '@/services/api';

const MyProfile: React.FC = () => {
  const navigate = useNavigate();
  const { data: profile } = useQuery({
    queryKey: ['my-profile'],
    queryFn: authApi.getProfile,
    retry: false,
  });
  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSettled: () => navigate('/dashboard'),
  });

  return (
    <div className="max-w-2xl">
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6">
        <h1 className="text-xl font-bold text-slate-900 mb-5">My Profile</h1>

        <div className="flex items-center gap-4 mb-6">
          <img
            src={profile?.profile_photo || 'https://i.pravatar.cc/120?img=12'}
            alt="Profile"
            className="w-20 h-20 rounded-full object-cover border-2 border-blue-100"
          />
          <div>
            <p className="text-lg font-semibold text-slate-900">{profile?.name || 'Admin User'}</p>
            <p className="text-sm text-slate-500">{profile?.email || 'admin@example.com'}</p>
          </div>
        </div>

        <div className="flex gap-3">
          <button className="px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
            Edit Profile
          </button>
          <button
            onClick={() => logoutMutation.mutate()}
            className="px-4 py-2.5 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors font-medium"
          >
            {logoutMutation.isPending ? 'Logging out...' : 'Logout'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default MyProfile;
