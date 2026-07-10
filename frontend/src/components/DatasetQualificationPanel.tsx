import React, { useState } from 'react';
import {
  ChevronDown, Zap, Shield, BarChart3, Network,
  AlertCircle, ThumbsUp, Clock, Database
} from 'lucide-react';

interface QualificationData {
  dataset_name: string;
  dataset_type: string;
  quality_score: number;
  compatibility_score: { [key: string]: number };
  quality_metrics: {
    completeness: number;
    accuracy: number;
    consistency: number;
    validity: number;
    integrity: number;
    uniqueness: number;
    overall_quality: number;
  };
  performance: {
    estimated_memory_mb: number;
    estimated_load_time_sec: number;
    can_process_in_memory: boolean;
    recommendations: string[];
  };
  missing_data: {
    profile: any[];
    overall_missing_pct: number;
  };
  clinical_standards: {
    dataset_classification: string;
    compliance_score: number;
    missing_expected_variables: string[];
    found_expected_variables: string[];
  };
  acceptance_status: 'accepted' | 'accepted_with_warning' | 'needs_review' | 'rejected';
  recommendations: string[];
  metadata: {
    row_count: number;
    column_count: number;
    estimated_memory_mb: number;
  };
  relationships: {
    primary_key?: string;
    duplicate_key_count: number;
    referential_integrity_score: number;
  };
  file_integrity: {
    is_valid: boolean;
    file_format: string;
    file_size_kb: number;
    issues: string[];
  };
}

export const DatasetQualificationPanel: React.FC<{ data: QualificationData }> = ({ data }) => {
  const [expandedSections, setExpandedSections] = useState<{ [key: string]: boolean }>({
    summary: true,
    quality: false,
    clinical: false,
    performance: false,
    missing: false,
    relationships: false,
    recommendations: false
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Color coding
  const getQualityColor = (score: number) => {
    if (score >= 90) return 'from-emerald-50 to-emerald-100 border-emerald-200';
    if (score >= 70) return 'from-amber-50 to-amber-100 border-amber-200';
    if (score >= 50) return 'from-orange-50 to-orange-100 border-orange-200';
    return 'from-red-50 to-red-100 border-red-200';
  };

  const getStatusBadge = () => {
    const statusConfig = {
      'accepted': { bg: 'bg-emerald-100', text: 'text-emerald-700', icon: '✓', label: 'Accepted' },
      'accepted_with_warning': { bg: 'bg-amber-100', text: 'text-amber-700', icon: '⚠', label: 'Warning' },
      'needs_review': { bg: 'bg-orange-100', text: 'text-orange-700', icon: '!', label: 'Review' },
      'rejected': { bg: 'bg-red-100', text: 'text-red-700', icon: '✗', label: 'Rejected' }
    };
    return statusConfig[data.acceptance_status] || statusConfig['needs_review'];
  };

  const status = getStatusBadge();

  return (
    <div className="space-y-4">
      {/* HEADER WITH KEY METRICS */}
      <div className={`rounded-lg border-2 bg-gradient-to-r ${getQualityColor(data.quality_score)} p-5`}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold text-slate-800">{data.dataset_name}</h3>
            <p className="text-sm text-slate-600">
              {data.dataset_type.toUpperCase()} • {data.metadata.row_count.toLocaleString()} rows • {data.metadata.column_count} columns
            </p>
          </div>
          <span className={`${status.bg} ${status.text} px-3 py-1.5 rounded-full font-bold text-sm`}>
            {status.icon} {status.label}
          </span>
        </div>

        {/* KEY METRICS GRID */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard label="Quality Score" value={data.quality_score} unit="%" />
          <MetricCard label="Completeness" value={data.quality_metrics.completeness} unit="%" />
          <MetricCard label="Consistency" value={data.quality_metrics.consistency} unit="%" />
          <MetricCard label="Integrity" value={data.quality_metrics.integrity} unit="%" />
        </div>
      </div>

      {/* SECTION 1: QUALITY DIMENSIONS */}
      <CollapsibleSection
        title="📊 Data Quality Analysis"
        icon={<BarChart3 className="w-4 h-4" />}
        isOpen={expandedSections.quality}
        onToggle={() => toggleSection('quality')}
      >
        <QualityDimensionsGrid metrics={data.quality_metrics} />
      </CollapsibleSection>

      {/* SECTION 2: CLINICAL STANDARDS */}
      <CollapsibleSection
        title="🏥 Clinical Standards Compliance"
        icon={<Shield className="w-4 h-4" />}
        isOpen={expandedSections.clinical}
        onToggle={() => toggleSection('clinical')}
      >
        <ClinicalCompliancePanel clinical={data.clinical_standards} />
      </CollapsibleSection>

      {/* SECTION 3: PERFORMANCE */}
      <CollapsibleSection
        title="⚡ Performance & Capacity"
        icon={<Zap className="w-4 h-4" />}
        isOpen={expandedSections.performance}
        onToggle={() => toggleSection('performance')}
      >
        <PerformanceAnalysisPanel performance={data.performance} metadata={data.metadata} />
      </CollapsibleSection>

      {/* SECTION 4: MISSING DATA */}
      <CollapsibleSection
        title="🔍 Missing Data Intelligence"
        icon={<AlertCircle className="w-4 h-4" />}
        isOpen={expandedSections.missing}
        onToggle={() => toggleSection('missing')}
      >
        <MissingDataPanel missing={data.missing_data} />
      </CollapsibleSection>

      {/* SECTION 5: RELATIONSHIPS */}
      <CollapsibleSection
        title="🔗 Relationship Validation"
        icon={<Network className="w-4 h-4" />}
        isOpen={expandedSections.relationships}
        onToggle={() => toggleSection('relationships')}
      >
        <RelationshipPanel relationships={data.relationships} />
      </CollapsibleSection>

      {/* SECTION 6: RECOMMENDATIONS */}
      {data.recommendations.length > 0 && (
        <CollapsibleSection
          title="💡 AI Recommendations"
          icon={<ThumbsUp className="w-4 h-4" />}
          isOpen={expandedSections.recommendations}
          onToggle={() => toggleSection('recommendations')}
        >
          <RecommendationsPanel recommendations={data.recommendations} />
        </CollapsibleSection>
      )}

      {/* FILE INTEGRITY */}
      {!data.file_integrity.is_valid && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm font-bold text-red-700 mb-2">⚠️ File Integrity Issues</p>
          {data.file_integrity.issues.map((issue, i) => (
            <p key={i} className="text-xs text-red-600 ml-2">• {issue}</p>
          ))}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// COMPONENT: Metric Card
// ============================================================================

const MetricCard: React.FC<{ label: string; value: number; unit: string }> = ({ label, value, unit }) => {
  return (
    <div className="bg-white rounded-lg p-3 text-center border border-slate-200">
      <p className="text-2xl font-bold" style={{ color: value >= 90 ? '#059669' : value >= 70 ? '#b45309' : '#dc2626' }}>
        {value.toFixed(0)}{unit}
      </p>
      <p className="text-xs font-semibold text-slate-600 mt-1">{label}</p>
    </div>
  );
};

// ============================================================================
// COMPONENT: Collapsible Section
// ============================================================================

const CollapsibleSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}> = ({ title, icon, isOpen, onToggle, children }) => (
  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
    <button
      onClick={onToggle}
      className="w-full p-4 flex items-center justify-between bg-slate-50 hover:bg-slate-100 transition-colors"
    >
      <div className="flex items-center gap-3">
        <span className="text-slate-500">{icon}</span>
        <span className="text-sm font-semibold text-slate-700">{title.includes(' ') ? title.substring(title.indexOf(' ') + 1) : title}</span>
      </div>
      <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
    </button>
    {isOpen && <div className="p-4 border-t border-slate-100">{children}</div>}
  </div>
);

// ============================================================================
// COMPONENT: Quality Dimensions Grid
// ============================================================================

const QualityDimensionsGrid: React.FC<{ metrics: any }> = ({ metrics }) => {
  const dimensions = [
    { name: 'Completeness', value: metrics.completeness, icon: '📊' },
    { name: 'Accuracy', value: metrics.accuracy, icon: '✓' },
    { name: 'Consistency', value: metrics.consistency, icon: '🔄' },
    { name: 'Validity', value: metrics.validity, icon: '✔️' },
    { name: 'Integrity', value: metrics.integrity, icon: '🔗' },
    { name: 'Uniqueness', value: metrics.uniqueness, icon: '⭐' }
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {dimensions.map(dim => (
        <div key={dim.name} className="bg-slate-50 rounded-lg p-3 text-center">
          <p className="text-2xl mb-1">{dim.icon}</p>
          <p className="text-lg font-bold text-slate-800">{dim.value.toFixed(0)}%</p>
          <p className="text-xs font-semibold text-slate-600">{dim.name}</p>
          <div className="mt-2 h-1.5 bg-slate-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${
                dim.value >= 90 ? 'bg-emerald-500' :
                dim.value >= 70 ? 'bg-amber-500' :
                'bg-red-500'
              }`}
              style={{ width: `${Math.min(100, dim.value)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// COMPONENT: Clinical Compliance
// ============================================================================

const ClinicalCompliancePanel: React.FC<{ clinical: any }> = ({ clinical }) => (
  <div className="space-y-3">
    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
      <span className="text-sm font-semibold text-slate-700">Dataset Type</span>
      <span className="px-2.5 py-1 bg-blue-100 text-blue-700 rounded font-bold text-xs">
        {clinical.dataset_classification.toUpperCase()}
      </span>
    </div>

    <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
      <span className="text-sm font-semibold text-slate-700">CDISC Compliance</span>
      <span className="text-lg font-bold">{clinical.compliance_score.toFixed(0)}%</span>
    </div>

    {clinical.found_expected_variables.length > 0 && (
      <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
        <p className="text-xs font-bold text-emerald-700 mb-2">✓ Expected Variables Found</p>
        <div className="flex flex-wrap gap-2">
          {clinical.found_expected_variables.map((v: string, i: number) => (
            <span key={i} className="text-xs bg-emerald-200 text-emerald-700 px-2 py-1 rounded">
              {v}
            </span>
          ))}
        </div>
      </div>
    )}

    {clinical.missing_expected_variables.length > 0 && (
      <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-xs font-bold text-amber-700 mb-2">⚠️ Missing Variables</p>
        <div className="flex flex-wrap gap-2">
          {clinical.missing_expected_variables.map((v: string, i: number) => (
            <span key={i} className="text-xs bg-amber-200 text-amber-700 px-2 py-1 rounded">
              {v}
            </span>
          ))}
        </div>
      </div>
    )}
  </div>
);

// ============================================================================
// COMPONENT: Performance Analysis
// ============================================================================

const PerformanceAnalysisPanel: React.FC<{ performance: any; metadata: any }> = ({ performance }) => (
  <div className="space-y-3">
    <div className="grid grid-cols-2 gap-3">
      <div className="bg-slate-50 rounded-lg p-3 text-center">
        <Clock className="w-5 h-5 mx-auto mb-1 text-blue-500" />
        <p className="text-sm font-bold text-slate-800">{performance.estimated_load_time_sec}s</p>
        <p className="text-xs text-slate-600">Est. Load Time</p>
      </div>
      <div className="bg-slate-50 rounded-lg p-3 text-center">
        <Database className="w-5 h-5 mx-auto mb-1 text-purple-500" />
        <p className="text-sm font-bold text-slate-800">{performance.estimated_memory_mb.toFixed(1)} MB</p>
        <p className="text-xs text-slate-600">Est. Memory</p>
      </div>
    </div>

    {!performance.can_process_in_memory && (
      <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-xs font-bold text-red-700">⚠️ Large Dataset Warning</p>
        <p className="text-xs text-red-600 mt-1">Dataset may exceed available memory</p>
      </div>
    )}

    {performance.recommendations.length > 0 && (
      <div className="space-y-2">
        {performance.recommendations.map((rec: string, i: number) => (
          <p key={i} className="text-xs text-slate-600 flex items-start gap-2">
            <span>💡</span> {rec}
          </p>
        ))}
      </div>
    )}
  </div>
);

// ============================================================================
// COMPONENT: Missing Data
// ============================================================================

const MissingDataPanel: React.FC<{ missing: any }> = ({ missing }) => (
  <div className="space-y-3">
    <div className="p-3 bg-slate-50 rounded-lg">
      <p className="text-sm font-semibold text-slate-700">Overall Missing</p>
      <p className="text-2xl font-bold text-slate-800">{missing.overall_missing_pct.toFixed(2)}%</p>
    </div>

    {missing.profile.length > 0 && (
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {missing.profile.map((m: any, i: number) => (
          <div key={i} className="p-2 bg-slate-50 rounded-lg text-xs">
            <div className="flex justify-between mb-1">
              <span className="font-semibold text-slate-700">{m.variable}</span>
              <span className={`font-bold ${m.missing_pct > 50 ? 'text-red-600' : m.missing_pct > 20 ? 'text-amber-600' : 'text-emerald-600'}`}>
                {m.missing_pct.toFixed(1)}%
              </span>
            </div>
            <p className="text-slate-600">Pattern: {m.pattern} | Rec: {m.recommendation}</p>
          </div>
        ))}
      </div>
    )}
  </div>
);

// ============================================================================
// COMPONENT: Relationships
// ============================================================================

const RelationshipPanel: React.FC<{ relationships: any }> = ({ relationships }) => (
  <div className="space-y-3">
    {relationships.primary_key && (
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-xs font-bold text-blue-700">Primary Key</p>
        <p className="text-sm font-semibold text-blue-900">{relationships.primary_key}</p>
      </div>
    )}

    <div className="grid grid-cols-2 gap-3">
      <div className="bg-slate-50 rounded-lg p-3 text-center">
        <p className="text-lg font-bold text-slate-800">{relationships.duplicate_key_count}</p>
        <p className="text-xs text-slate-600">Duplicate Rows</p>
      </div>
      <div className="bg-slate-50 rounded-lg p-3 text-center">
        <p className="text-lg font-bold text-slate-800">{relationships.referential_integrity_score.toFixed(0)}%</p>
        <p className="text-xs text-slate-600">Integrity Score</p>
      </div>
    </div>
  </div>
);

// ============================================================================
// COMPONENT: Recommendations
// ============================================================================

const RecommendationsPanel: React.FC<{ recommendations: string[] }> = ({ recommendations }) => (
  <div className="space-y-2">
    {recommendations.map((rec, i) => (
      <div key={i} className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <span className="text-lg flex-shrink-0">💡</span>
        <p className="text-sm text-blue-700">{rec}</p>
      </div>
    ))}
  </div>
);

export default DatasetQualificationPanel;
