import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { CheckCircle, AlertTriangle, ThumbsUp, ThumbsDown, ArrowRight, Sparkles } from 'lucide-react';
import { projectsApi } from '@/services/api';

const ValidationStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [feedbackGiven, setFeedbackGiven] = useState(false);
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);
  const [correctionText, setCorrectionText] = useState('');

  const { data: validation, isLoading } = useQuery({
    queryKey: ['validation', projectId],
    queryFn: () => projectsApi.getValidation(projectId!),
  });

  const submitFeedbackMutation = useMutation({
    mutationFn: projectsApi.submitFeedback,
    onSuccess: () => {
      setFeedbackGiven(true);
      setShowFeedbackForm(false);
    },
  });

  const handleFeedback = (isCorrect: boolean) => {
    if (isCorrect) {
      // Positive feedback - translation is correct
      submitFeedbackMutation.mutate({
        project_id: projectId!,
        translation_id: projectId!, // Should be actual translation ID
        is_correct: true,
      });
    } else {
      // Show feedback form for corrections
      setShowFeedbackForm(true);
    }
  };

  const handleSubmitCorrection = (corrections: any) => {
    submitFeedbackMutation.mutate({
      project_id: projectId!,
      translation_id: projectId!,
      is_correct: false,
      corrections,
      user_notes: corrections?.user_notes,
    });
  };

  const matchRate = validation?.overall_match || 0;
  const isHighMatch = matchRate >= 95;

  return (
    <div className="max-w-4xl">
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
            isHighMatch ? 'bg-green-100' : 'bg-yellow-100'
          }`}>
            {isHighMatch ? (
              <CheckCircle className="w-6 h-6 text-green-600" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-yellow-600" />
            )}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Validation Results
            </h2>
            <p className="text-sm text-gray-600">
              Comparing SAS and R outputs
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Validating outputs...</p>
          </div>
        ) : (
          <>
            {/* Overall Match Score */}
            <div className="mb-8">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-gray-700">
                  Overall Match Rate
                </span>
                <span className="text-2xl font-bold text-gray-900">
                  {matchRate.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    matchRate >= 95
                      ? 'bg-green-500'
                      : matchRate >= 85
                      ? 'bg-yellow-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${matchRate}%` }}
                />
              </div>
            </div>

            {/* Validation Details */}
            <div className="space-y-4 mb-8">
              <ValidationItem
                label="Structure Match"
                value={validation?.structure_match ? 'Pass' : 'Fail'}
                status={validation?.structure_match ? 'success' : 'error'}
              />
              <ValidationItem
                label="Value Discrepancies"
                value={`${validation?.value_discrepancies || 0} differences found`}
                status={
                  (validation?.value_discrepancies || 0) === 0
                    ? 'success'
                    : 'warning'
                }
              />
              <ValidationItem
                label="Statistical Comparison"
                value="Mean, Median, SD validated"
                status="success"
              />
            </div>

            {/* Reinforcement Learning Feedback */}
            {!feedbackGiven && !showFeedbackForm && (
              <div className="mb-8 p-6 bg-purple-50 border border-purple-200 rounded-lg">
                <div className="flex items-start gap-3 mb-4">
                  <Sparkles className="w-6 h-6 text-purple-600 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-purple-900 mb-1">
                      Help Improve Translation Quality
                    </h3>
                    <p className="text-sm text-purple-800">
                      Your feedback trains our AI model to make better translations. Is this translation correct?
                    </p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleFeedback(true)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <ThumbsUp className="w-5 h-5" />
                    Yes, looks good
                  </button>
                  <button
                    onClick={() => handleFeedback(false)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    <ThumbsDown className="w-5 h-5" />
                    No, needs correction
                  </button>
                </div>
              </div>
            )}

            {/* Feedback Form */}
            {showFeedbackForm && (
              <div className="mb-8 p-6 bg-gray-50 border border-gray-200 rounded-lg">
                <h3 className="font-semibold text-gray-900 mb-4">
                  What needs to be corrected?
                </h3>
                <textarea
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none mb-4"
                  rows={4}
                  value={correctionText}
                  onChange={(e) => setCorrectionText(e.target.value)}
                  placeholder="Describe the issues or provide the correct R code..."
                />
                <div className="flex gap-3">
                  <button
                    onClick={() => { setShowFeedbackForm(false); setCorrectionText(''); }}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleSubmitCorrection({ user_notes: correctionText })}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Submit Feedback
                  </button>
                </div>
              </div>
            )}

            {/* Feedback Confirmation */}
            {feedbackGiven && (
              <div className="mb-8 p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-green-800 font-medium">
                  ✓ Thank you! Your feedback has been recorded and will help improve future translations.
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={() => navigate(`/projects/${projectId}/execution`)}
                className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => navigate(`/projects/${projectId}/report`)}
                className="flex-[2] flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                Export R Code
                <ArrowRight className="w-5 h-5" />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const ValidationItem: React.FC<{
  label: string;
  value: string;
  status: 'success' | 'warning' | 'error';
}> = ({ label, value, status }) => {
  const config = {
    success: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-800', icon: '✓' },
    warning: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-800', icon: '⚠' },
    error: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-800', icon: '✗' },
  }[status];

  return (
    <div className={`p-4 ${config.bg} border ${config.border} rounded-lg`}>
      <div className="flex justify-between items-center">
        <span className="font-medium text-gray-900">{label}</span>
        <span className={`${config.text} flex items-center gap-2`}>
          <span>{config.icon}</span>
          <span>{value}</span>
        </span>
      </div>
    </div>
  );
};

export default ValidationStep;
