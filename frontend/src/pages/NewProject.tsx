import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { ArrowRight, ArrowLeft, Wand2 } from 'lucide-react';
import { projectsApi } from '@/services/api';

const NewProject: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ name: '', description: '' });

  const createProjectMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: (data) => navigate(`/projects/${data.id}/upload`),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.name.trim()) {
      createProjectMutation.mutate(formData);
    }
  };

  const isValid = formData.name.trim().length > 0;

  return (
    <div className="fade-in max-w-xl mx-auto">
      {/* Back link */}
      <Link
        to="/projects"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-800 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Projects
      </Link>

      {/* Hero card */}
      <div className="relative overflow-hidden bg-gradient-to-br from-[#1f4368] to-[#1a3654] rounded-2xl p-7 mb-5 text-white shadow-lg">
        <div className="relative z-10">
          <div className="w-11 h-11 bg-white/20 rounded-xl flex items-center justify-center mb-4 backdrop-blur-sm">
            <Wand2 className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-xl font-extrabold tracking-tight mb-1.5">New Conversion Project</h1>
          <p className="text-blue-100 text-sm leading-relaxed max-w-xs">
            Give your project a name. You'll upload your SAS file in the next step.
          </p>
        </div>
        <div className="absolute right-0 top-0 w-40 h-40 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/4 blur-2xl pointer-events-none" />
      </div>

      {/* Form card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="name" className="block text-sm font-semibold text-slate-800 mb-1.5">
              Project name <span className="text-red-500 ml-0.5">*</span>
            </label>
            <input
              type="text"
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Clinical Trial Analysis Q3"
              className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-[#8aaec9] focus:border-transparent outline-none transition"
              required
              autoFocus
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-semibold text-slate-800 mb-1.5">
              Description
              <span className="ml-1.5 text-xs font-normal text-slate-400">optional</span>
            </label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Brief description of what this SAS code does…"
              rows={3}
              className="w-full px-4 py-2.5 border border-slate-300 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-[#8aaec9] focus:border-transparent outline-none transition resize-none"
            />
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="flex-1 px-4 py-2.5 border border-slate-200 text-slate-700 rounded-xl hover:bg-slate-50 transition-colors text-sm font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isValid || createProjectMutation.isPending}
              className="flex-[2] flex items-center justify-center gap-2 px-4 py-2.5 bg-[#1f4368] text-white rounded-xl hover:bg-[#1a3654] transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-bold shadow-sm"
            >
              {createProjectMutation.isPending ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Creating…
                </>
              ) : (
                <>
                  Create & Continue
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Info footer */}
      <p className="text-xs text-slate-400 text-center mt-5 leading-relaxed">
        After creating your project, you'll upload your SAS script and optional datasets.
      </p>
    </div>
  );
};

export default NewProject;
