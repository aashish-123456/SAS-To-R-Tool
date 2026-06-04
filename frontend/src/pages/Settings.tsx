import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi, systemApi } from '@/services/api';

const Settings: React.FC = () => {
  const queryClient = useQueryClient();

  // Password change
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // SAS Viya config
  const [viyaUrl, setViyaUrl]           = useState('');
  const [viyaUsername, setViyaUsername] = useState('');
  const [viyaPassword, setViyaPassword] = useState('');
  const [viyaEnabled, setViyaEnabled]   = useState(false);
  const [viyaMsg, setViyaMsg]           = useState('');
  const [viyaErr, setViyaErr]           = useState('');
  const [testingConn, setTestingConn]   = useState(false);

  const { data: execConfig } = useQuery({
    queryKey: ['exec-config'],
    queryFn: systemApi.getExecutionConfig,
    staleTime: 30_000,
  });

  // Populate form when config loads
  React.useEffect(() => {
    if (execConfig) {
      setViyaEnabled(execConfig.sasViya.enabled);
      setViyaUrl(execConfig.sasViya.baseUrl);
      setViyaUsername(execConfig.sasViya.username);
    }
  }, [execConfig]);

  const saveViyaMutation = useMutation({
    mutationFn: () => systemApi.updateExecutionConfig({
      sasViya: { enabled: viyaEnabled, baseUrl: viyaUrl, username: viyaUsername, password: viyaPassword },
    }),
    onSuccess: () => {
      setViyaMsg('SAS Viya settings saved.');
      setViyaErr('');
      setViyaPassword('');
      queryClient.invalidateQueries({ queryKey: ['exec-config'] });
    },
    onError: () => setViyaErr('Could not save settings.'),
  });

  const handleTestConnection = async () => {
    setTestingConn(true);
    setViyaMsg('');
    setViyaErr('');
    // Save first then test
    await systemApi.updateExecutionConfig({
      sasViya: { enabled: viyaEnabled, baseUrl: viyaUrl, username: viyaUsername, password: viyaPassword },
    });
    const result = await systemApi.testSasViyaConnection();
    setTestingConn(false);
    if (result.status === 'connected') {
      setViyaMsg('Connection successful — SAS Viya is reachable.');
    } else if (result.status === 'disabled') {
      setViyaErr('Enable SAS Viya first before testing.');
    } else {
      setViyaErr(`Connection failed: ${result.message ?? result.status}`);
    }
  };

  const changePasswordMutation = useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: () => {
      setMessage('Password changed successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    },
    onError: () => {
      setError('Could not update password from server. Please try again.');
    },
  });

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage('');
    setError('');

    if (!currentPassword || !newPassword || !confirmPassword) {
      setError('Please fill all password fields.');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('New password and confirm password do not match.');
      return;
    }

    changePasswordMutation.mutate({
      current_password: currentPassword,
      new_password: newPassword,
    });
  };

  return (
    <div className="max-w-2xl space-y-6">

      {/* ── SAS Viya Configuration ─────────────────────────────────────── */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-bold text-slate-900 mb-1">SAS Viya Execution</h2>
        <p className="text-sm text-slate-500 mb-5">
          Connect to SAS OnDemand for Academics for live SAS execution. Leave disabled to use the built-in SAS simulator.
        </p>
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-800 font-medium mb-1">Regional ODA URLs:</p>
          <ul className="text-xs text-blue-700 space-y-1 font-mono">
            <li>🌏 Asia-Pacific 1: <span className="font-semibold">https://odamid-apse1-2.oda.sas.com</span></li>
            <li>🌏 Asia-Pacific 2: <span className="font-semibold">https://odamid-apse2-2.oda.sas.com</span></li>
            <li>🌎 Americas: <span className="font-semibold">https://odamid-usw2-2.oda.sas.com</span></li>
            <li>🌍 Europe: <span className="font-semibold">https://odamid-euw2-2.oda.sas.com</span></li>
          </ul>
          <p className="text-xs text-blue-700 mt-2">Extract from your ODA login URL (e.g., https://odamid-<strong>apse1</strong>-2.oda.sas.com)</p>
        </div>

        <div className="space-y-4">
          {/* Enable toggle */}
          <div className="flex items-center justify-between py-2 border-b border-slate-100">
            <div>
              <p className="text-sm font-semibold text-slate-800">Enable SAS Viya</p>
              <p className="text-xs text-slate-400">Route SAS execution through SAS OnDemand for Academics</p>
            </div>
            <button
              type="button"
              onClick={() => setViyaEnabled(v => !v)}
              className={`w-12 h-6 rounded-full p-0.5 transition-colors ${viyaEnabled ? 'bg-[#1f4368]' : 'bg-slate-200'}`}
            >
              <span className={`block w-5 h-5 bg-white rounded-full shadow-sm transition-transform ${viyaEnabled ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          {/* Base URL */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Base URL</label>
            <input
              type="url"
              value={viyaUrl}
              onChange={e => setViyaUrl(e.target.value)}
              placeholder="https://odamid-apse2-2.oda.sas.com"
              className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#8aaec9] outline-none text-sm"
            />
            <p className="text-xs text-slate-400 mt-1">Regional API endpoint for your SAS ODA account</p>
          </div>

          {/* Username */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">SAS Username</label>
            <input
              type="text"
              value={viyaUsername}
              onChange={e => setViyaUsername(e.target.value)}
              placeholder="your@email.com"
              className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#8aaec9] outline-none text-sm"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">SAS Password</label>
            <input
              type="password"
              value={viyaPassword}
              onChange={e => setViyaPassword(e.target.value)}
              placeholder="Enter password to update"
              className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#8aaec9] outline-none text-sm"
            />
          </div>

          {viyaErr && <p className="text-sm text-red-600">{viyaErr}</p>}
          {viyaMsg && <p className="text-sm text-emerald-700">{viyaMsg}</p>}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => saveViyaMutation.mutate()}
              disabled={saveViyaMutation.isPending}
              className="px-4 py-2.5 bg-[#1f4368] text-white rounded-lg hover:bg-[#1a3654] transition-colors font-medium text-sm disabled:opacity-50"
            >
              {saveViyaMutation.isPending ? 'Saving…' : 'Save Settings'}
            </button>
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testingConn}
              className="px-4 py-2.5 border border-[#ccdce9] text-[#1f4368] rounded-lg hover:bg-[#eef3f8] transition-colors font-medium text-sm disabled:opacity-50"
            >
              {testingConn ? 'Testing…' : 'Test Connection'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Change Password ────────────────────────────────────────────── */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6">
        <h1 className="text-xl font-bold text-slate-900 mb-1">Settings</h1>
        <p className="text-sm text-slate-500 mb-6">Change your account password.</p>

        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Current Password</label>
            <input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#8aaec9] focus:border-transparent outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">New Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#8aaec9] focus:border-transparent outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Confirm New Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#8aaec9] focus:border-transparent outline-none"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
          {message && <p className="text-sm text-green-700">{message}</p>}

          <button
            type="submit"
            disabled={changePasswordMutation.isPending}
            className="px-4 py-2.5 bg-[#1f4368] text-white rounded-lg hover:bg-[#1a3654] transition-colors font-medium"
          >
            {changePasswordMutation.isPending ? 'Updating...' : 'Change Password'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Settings;
