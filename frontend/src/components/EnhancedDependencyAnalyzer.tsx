import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface DependencyExplanation {
  name: string;
  dep_type: string;
  purpose: string;
  locations: number[];
  used_by: string[];
  outputs_affected: string[];
  criticality: string;
  consequences_if_missing: string;
  confidence: number;
}

interface VariableMapping {
  original_var: string;
  expected_var: string;
  confidence: number;
  reason: string;
}

interface SchemaValidation {
  required_vars: string[];
  found_vars: string[];
  missing_vars: string[];
  extra_vars: string[];
  variable_mappings: VariableMapping[];
  schema_score: number;
}

interface CompatibilityScore {
  overall: number;
  structure: number;
  variables: number;
  datatypes: number;
  relationships: number;
  translation_ready: boolean;
}

interface EnhancedDependencyData {
  dependencies: DependencyExplanation[];
  dependency_graph: Record<string, string[]>;
  schema_validations: Record<string, SchemaValidation>;
  compatibility_scores: Record<string, CompatibilityScore>;
  readiness_percent: number;
  total_dependencies: number;
  satisfied_count: number;
  missing_count: number;
  critical_issues: string[];
}

export const EnhancedDependencyAnalyzer: React.FC<{ data: EnhancedDependencyData }> = ({ data }) => {
  const [expandedSection, setExpandedSection] = useState<string | null>('summary');

  const getStatusColor = (status: string) => {
    if (status === 'critical' || status === 'rejected') return 'bg-red-50 border-red-200 text-red-700';
    if (status === 'high' || status === 'warning') return 'bg-amber-50 border-amber-200 text-amber-700';
    if (status === 'accepted') return 'bg-emerald-50 border-emerald-200 text-emerald-700';
    return 'bg-slate-50 border-slate-200 text-slate-700';
  };

  return (
    <div className="space-y-4">
      {/* HEADER */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Enhanced Dependency Analyzer</h2>
            <p className="text-xs text-slate-600">6 Critical Features for SAS→R Translation Readiness</p>
          </div>
          <span className={`px-3 py-1 rounded-full font-bold text-sm ${
            data.readiness_percent >= 80 ? 'bg-emerald-100 text-emerald-700' :
            data.readiness_percent >= 60 ? 'bg-amber-100 text-amber-700' :
            'bg-red-100 text-red-700'
          }`}>
            {data.readiness_percent}% Ready
          </span>
        </div>

        {/* Summary Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-white rounded p-3 text-center border border-slate-200">
            <p className="text-2xl font-bold text-slate-800">{data.total_dependencies}</p>
            <p className="text-xs text-slate-600 mt-1">Dependencies Found</p>
          </div>
          <div className="bg-white rounded p-3 text-center border border-emerald-200">
            <p className="text-2xl font-bold text-emerald-600">{data.satisfied_count}</p>
            <p className="text-xs text-slate-600 mt-1">Satisfied</p>
          </div>
          <div className="bg-white rounded p-3 text-center border border-amber-200">
            <p className="text-2xl font-bold text-amber-600">{data.missing_count}</p>
            <p className="text-xs text-slate-600 mt-1">Missing</p>
          </div>
          <div className="bg-white rounded p-3 text-center border border-blue-200">
            <p className="text-2xl font-bold text-blue-600">{data.critical_issues.length}</p>
            <p className="text-xs text-slate-600 mt-1">Critical Issues</p>
          </div>
        </div>
      </div>

      {/* FEATURE 1 & 2: AI Dependency Discovery + Explainability */}
      <CollapsibleSection
        title="🔍 Dependency Discovery & Explainability"
        isOpen={expandedSection === 'dependencies'}
        onToggle={() => setExpandedSection(expandedSection === 'dependencies' ? null : 'dependencies')}
      >
        <div className="space-y-3">
          {data.dependencies.map((dep, idx) => (
            <div key={idx} className={`rounded-lg border p-4 ${getStatusColor(dep.criticality)}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold">{dep.name}</span>
                <span className="text-xs font-semibold uppercase px-2 py-1 rounded bg-white/50">
                  {dep.dep_type.replace('_', ' ')}
                </span>
              </div>

              <div className="text-sm space-y-2">
                <p><strong>Purpose:</strong> {dep.purpose}</p>
                <p><strong>Used by:</strong> {dep.used_by.join(', ')}</p>
                <p><strong>Outputs affected:</strong> {dep.outputs_affected.join(', ') || 'None detected'}</p>
                <p className="text-red-700"><strong>If missing:</strong> {dep.consequences_if_missing}</p>
                <p className="text-xs text-slate-600">
                  <strong>Confidence:</strong> {(dep.confidence * 100).toFixed(0)}%
                </p>
              </div>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      {/* FEATURE 3: Dataset Qualification */}
      <CollapsibleSection
        title="✅ Dataset Qualification"
        isOpen={expandedSection === 'qualification'}
        onToggle={() => setExpandedSection(expandedSection === 'qualification' ? null : 'qualification')}
      >
        <div className="space-y-2">
          {Object.entries(data.compatibility_scores).map(([name, score]) => (
            <div key={name} className="bg-white border rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-slate-800">{name}</span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                  score.translation_ready ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                }`}>
                  {score.translation_ready ? '✓ Ready' : '⚠ Review Needed'}
                </span>
              </div>
              <div className="text-xs text-slate-600">Compatibility: {score.overall.toFixed(1)}%</div>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      {/* FEATURE 4 & 5: Schema Validation + AI Variable Mapping */}
      <CollapsibleSection
        title="📋 Schema Validation & Variable Mapping"
        isOpen={expandedSection === 'schema'}
        onToggle={() => setExpandedSection(expandedSection === 'schema' ? null : 'schema')}
      >
        <div className="space-y-4">
          {Object.entries(data.schema_validations).map(([dataset, schema]) => (
            <div key={dataset} className="bg-white border rounded-lg p-4">
              <h4 className="font-bold text-slate-800 mb-3">{dataset}</h4>

              {/* Missing Variables */}
              {schema.missing_vars.length > 0 && (
                <div className="mb-3 p-2 bg-amber-50 border border-amber-200 rounded">
                  <p className="text-xs font-bold text-amber-700 mb-1">Missing Variables:</p>
                  <div className="flex flex-wrap gap-1">
                    {schema.missing_vars.map(v => (
                      <span key={v} className="text-xs bg-amber-200 text-amber-800 px-2 py-0.5 rounded">
                        {v}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Variable Mappings */}
              {schema.variable_mappings.length > 0 && (
                <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded">
                  <p className="text-xs font-bold text-blue-700 mb-1">AI Variable Mappings:</p>
                  <div className="space-y-1">
                    {schema.variable_mappings.map((m, i) => (
                      <div key={i} className="text-xs text-blue-700">
                        <strong>{m.original_var}</strong> → <strong>{m.expected_var}</strong>
                        <span className="ml-2 text-blue-600 font-semibold">
                          ({(m.confidence * 100).toFixed(0)}% match)
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-xs text-slate-600">
                Schema Match: <span className="font-bold">{schema.schema_score.toFixed(1)}%</span>
              </p>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      {/* FEATURE 6: Compatibility Scores */}
      <CollapsibleSection
        title="⭐ Dataset Compatibility Scores"
        isOpen={expandedSection === 'compatibility'}
        onToggle={() => setExpandedSection(expandedSection === 'compatibility' ? null : 'compatibility')}
      >
        <div className="space-y-4">
          {Object.entries(data.compatibility_scores).map(([dataset, scores]) => (
            <div key={dataset} className="bg-white border rounded-lg p-4">
              <h4 className="font-bold text-slate-800 mb-3">{dataset}</h4>

              {/* Overall Score */}
              <div className="mb-3 p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-700">Overall Compatibility</span>
                  <span className="text-2xl font-bold text-blue-600">{scores.overall.toFixed(1)}%</span>
                </div>
              </div>

              {/* Component Scores */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-slate-50 p-2 rounded border border-slate-200">
                  <p className="text-slate-600">Structure</p>
                  <p className="font-bold text-slate-800">{scores.structure.toFixed(1)}%</p>
                </div>
                <div className="bg-slate-50 p-2 rounded border border-slate-200">
                  <p className="text-slate-600">Variables</p>
                  <p className="font-bold text-slate-800">{scores.variables.toFixed(1)}%</p>
                </div>
                <div className="bg-slate-50 p-2 rounded border border-slate-200">
                  <p className="text-slate-600">Datatypes</p>
                  <p className="font-bold text-slate-800">{scores.datatypes.toFixed(1)}%</p>
                </div>
                <div className="bg-slate-50 p-2 rounded border border-slate-200">
                  <p className="text-slate-600">Relationships</p>
                  <p className="font-bold text-slate-800">{scores.relationships.toFixed(1)}%</p>
                </div>
              </div>

              <div className="mt-3 p-2 rounded" style={{
                backgroundColor: scores.translation_ready ? '#d1fae5' : '#fef3c7',
                color: scores.translation_ready ? '#065f46' : '#78350f'
              }}>
                <p className="text-xs font-bold">
                  {scores.translation_ready ? '✓ Translation Ready' : '⚠ Needs Review Before Translation'}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CollapsibleSection>

      {/* Critical Issues */}
      {data.critical_issues.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm font-bold text-red-700 mb-2">⚠️ Critical Issues</p>
          <div className="space-y-1">
            {data.critical_issues.map((issue, i) => (
              <p key={i} className="text-sm text-red-700">• {issue}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// Helper component for collapsible sections
const CollapsibleSection: React.FC<{
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}> = ({ title, isOpen, onToggle, children }) => (
  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
    <button
      onClick={onToggle}
      className="w-full p-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
    >
      <span className="font-semibold text-slate-800">{title}</span>
      <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
    </button>
    {isOpen && (
      <div className="p-4 border-t border-slate-200 space-y-3">
        {children}
      </div>
    )}
  </div>
);

export default EnhancedDependencyAnalyzer;
