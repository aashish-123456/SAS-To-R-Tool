import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Code,
  ArrowRight,
  AlertCircle,
  Sparkles,
  Download,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Loader2,
  Clock,
  Brain,
  GitBranch,
  Package,
  Zap,
  ShieldCheck,
  ScanSearch,
} from 'lucide-react';
import { projectsApi } from '@/services/api';

// ── types ──────────────────────────────────────────────────────────────────────

interface EngineResults {
  parse?: {
    proc_types: string[];
    functions: string[];
    keywords: string[];
    variables: Record<string, string>;
    datasets: Record<string, string>;
    total_statements: number;
    data_steps_count: number;
    proc_steps_count: number;
    if_else_count: number;
    has_macros: boolean;
    has_sql: boolean;
    has_merge: boolean;
    has_array: boolean;
    has_retain: boolean;
    has_clinical: boolean;
    statistics_found: string[];
  };
  intent?: {
    problem_domain: string;
    domain_confidence: number;
    primary_goal: string;
    secondary_goals: string[];
    problem_statement: string;
    methodology: string;
    analysis_types: string[];
    complexity: string;
    key_metrics: string[];
    transformations: string[];
    output_segments: Array<{ name: string; description: string; proc_type: string }>;
  };
  flow?: {
    total_steps: number;
    flow_description: string;
    input_datasets: string[];
    output_datasets: string[];
    steps: Array<{
      order: number;
      name: string;
      description: string;
      step_type: string;
      sas_constructs: string[];
      inputs: string[];
      outputs: string[];
    }>;
  };
  packages?: {
    all_packages: string[];
    install_code: string;
    library_code: string;
    selection_rationale: string;
    primary_packages: Array<{
      name: string;
      purpose: string;
      functions_used: string[];
      rationale: string;
      alternatives: string[];
    }>;
  };
  translation?: {
    warnings: string[];
    translation_notes: string[];
    packages_used: string[];
    lines_of_code: number;
    annotations: string[];
  };
  validation?: {
    problem_statement_match: boolean;
    execution_flow_match: boolean;
    packages_appropriate: boolean;
    code_complexity: string;
    estimated_equivalence_pct: number;
    approval_status: string;
    validation_summary: string;
    engine_coverage: Record<string, boolean>;
    strengths: string[];
    recommendations: string[];
    issues: Array<{ severity: string; title: string; detail: string; suggestion?: string }>;
  };
}

// ── engine panel config ────────────────────────────────────────────────────────

const ENGINE_CONFIG = [
  {
    key: 'parse',
    label: 'Parser Engine',
    subtitle: 'Reads what is written in the SAS code',
    icon: ScanSearch,
    color: 'blue',
  },
  {
    key: 'intent',
    label: 'Intent Engine',
    subtitle: 'Understands WHY the code was written',
    icon: Brain,
    color: 'purple',
  },
  {
    key: 'flow',
    label: 'Execution Flow Engine',
    subtitle: 'Maps the step-by-step logic sequence',
    icon: GitBranch,
    color: 'indigo',
  },
  {
    key: 'packages',
    label: 'R/Package Recommender',
    subtitle: 'Selects the best R packages for each construct',
    icon: Package,
    color: 'emerald',
  },
  {
    key: 'translation',
    label: 'Translation Engine',
    subtitle: 'Generates optimised R code from all engine insights',
    icon: Zap,
    color: 'orange',
  },
  {
    key: 'validation',
    label: 'Flow Validation Engine',
    subtitle: 'Verifies R code matches SAS intent and output',
    icon: ShieldCheck,
    color: 'teal',
  },
] as const;

type ColorKey = 'blue' | 'purple' | 'indigo' | 'emerald' | 'orange' | 'teal';

const COLOR_MAP: Record<ColorKey, { bg: string; border: string; icon: string; badge: string; text: string }> = {
  blue:    { bg: 'bg-blue-50',    border: 'border-blue-200',   icon: 'text-blue-600',    badge: 'bg-blue-100 text-blue-700',    text: 'text-blue-800' },
  purple:  { bg: 'bg-purple-50',  border: 'border-purple-200', icon: 'text-purple-600',  badge: 'bg-purple-100 text-purple-700',text: 'text-purple-800' },
  indigo:  { bg: 'bg-indigo-50',  border: 'border-indigo-200', icon: 'text-indigo-600',  badge: 'bg-indigo-100 text-indigo-700',text: 'text-indigo-800' },
  emerald: { bg: 'bg-emerald-50', border: 'border-emerald-200',icon: 'text-emerald-600', badge: 'bg-emerald-100 text-emerald-700',text: 'text-emerald-800' },
  orange:  { bg: 'bg-orange-50',  border: 'border-orange-200', icon: 'text-orange-600',  badge: 'bg-orange-100 text-orange-700',text: 'text-orange-800' },
  teal:    { bg: 'bg-teal-50',    border: 'border-teal-200',   icon: 'text-teal-600',    badge: 'bg-teal-100 text-teal-700',   text: 'text-teal-800' },
};

// ── sub-components ─────────────────────────────────────────────────────────────

const Badge: React.FC<{ label: string; color: ColorKey }> = ({ label, color }) => (
  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${COLOR_MAP[color].badge}`}>
    {label}
  </span>
);

const Pill: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 text-xs font-mono border border-gray-200">
    {children}
  </span>
);

// ── engine detail renderers ────────────────────────────────────────────────────

const ParseDetail: React.FC<{ data: NonNullable<EngineResults['parse']> }> = ({ data }) => (
  <div className="space-y-3 text-sm">
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[
        { label: 'Statements', value: data.total_statements },
        { label: 'DATA steps', value: data.data_steps_count },
        { label: 'PROC steps', value: data.proc_steps_count },
        { label: 'IF-ELSE chains', value: data.if_else_count },
      ].map(({ label, value }) => (
        <div key={label} className="bg-white rounded border border-gray-200 p-2 text-center">
          <div className="text-xl font-bold text-gray-900">{value}</div>
          <div className="text-xs text-gray-500">{label}</div>
        </div>
      ))}
    </div>

    {data.proc_types.length > 0 && (
      <div>
        <p className="text-xs font-medium text-gray-600 mb-1">PROC types detected:</p>
        <div className="flex flex-wrap gap-1">
          {data.proc_types.map(pt => <Pill key={pt}>PROC {pt.toUpperCase()}</Pill>)}
        </div>
      </div>
    )}

    {data.functions.length > 0 && (
      <div>
        <p className="text-xs font-medium text-gray-600 mb-1">Functions used ({data.functions.length}):</p>
        <div className="flex flex-wrap gap-1">
          {data.functions.slice(0, 16).map(f => <Pill key={f}>{f}()</Pill>)}
          {data.functions.length > 16 && <Pill>+{data.functions.length - 16} more</Pill>}
        </div>
      </div>
    )}

    <div className="flex flex-wrap gap-2 text-xs">
      {data.has_macros  && <Badge label="Macros"      color="blue" />}
      {data.has_sql     && <Badge label="PROC SQL"    color="purple" />}
      {data.has_merge   && <Badge label="MERGE"       color="indigo" />}
      {data.has_array   && <Badge label="ARRAY"       color="emerald" />}
      {data.has_retain  && <Badge label="RETAIN"      color="orange" />}
      {data.has_clinical && <Badge label="Clinical"   color="teal" />}
    </div>

    {Object.keys(data.datasets).length > 0 && (
      <div>
        <p className="text-xs font-medium text-gray-600 mb-1">Datasets:</p>
        <div className="flex flex-wrap gap-1">
          {Object.entries(data.datasets).map(([ds, role]) => (
            <span key={ds} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-100 text-xs border border-gray-200">
              <span className="font-mono text-gray-700">{ds}</span>
              <span className={`text-xs ${role === 'output' ? 'text-green-600' : role === 'input' ? 'text-blue-600' : 'text-purple-600'}`}>
                ({role})
              </span>
            </span>
          ))}
        </div>
      </div>
    )}
  </div>
);

const IntentDetail: React.FC<{ data: NonNullable<EngineResults['intent']> }> = ({ data }) => (
  <div className="space-y-3 text-sm">
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      <div className="bg-white rounded border p-2">
        <p className="text-xs text-gray-500">Domain</p>
        <p className="font-semibold text-gray-800 capitalize">{data.problem_domain.replace(/_/g, ' ')}</p>
        <p className="text-xs text-gray-400">{Math.round(data.domain_confidence * 100)}% confidence</p>
      </div>
      <div className="bg-white rounded border p-2">
        <p className="text-xs text-gray-500">Primary Goal</p>
        <p className="font-semibold text-gray-800 capitalize">{data.primary_goal.replace(/_/g, ' ')}</p>
      </div>
      <div className="bg-white rounded border p-2">
        <p className="text-xs text-gray-500">Complexity</p>
        <p className={`font-semibold capitalize ${
          data.complexity === 'simple' ? 'text-green-700' :
          data.complexity === 'moderate' ? 'text-blue-700' :
          data.complexity === 'complex' ? 'text-orange-700' : 'text-red-700'
        }`}>{data.complexity}</p>
      </div>
    </div>

    <div className="bg-white rounded border p-3">
      <p className="text-xs font-medium text-gray-600 mb-1">Problem Statement</p>
      <p className="text-gray-800 leading-relaxed">{data.problem_statement}</p>
    </div>

    <div className="bg-white rounded border p-3">
      <p className="text-xs font-medium text-gray-600 mb-1">Methodology</p>
      <p className="text-gray-700">{data.methodology}</p>
    </div>

    {data.output_segments.length > 0 && (
      <div>
        <p className="text-xs font-medium text-gray-600 mb-2">Expected Outputs ({data.output_segments.length}):</p>
        <div className="space-y-1">
          {data.output_segments.map((seg, i) => (
            <div key={i} className="bg-white rounded border p-2">
              <p className="text-xs font-medium text-gray-700">{seg.name}</p>
              <p className="text-xs text-gray-500">{seg.description}</p>
            </div>
          ))}
        </div>
      </div>
    )}

    {data.transformations.length > 0 && (
      <div>
        <p className="text-xs font-medium text-gray-600 mb-1">Transformations applied:</p>
        <ul className="space-y-0.5">
          {data.transformations.map((t, i) => (
            <li key={i} className="text-xs text-gray-700 flex items-start gap-1">
              <span className="text-purple-400 mt-0.5">•</span>{t}
            </li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

const FlowDetail: React.FC<{ data: NonNullable<EngineResults['flow']> }> = ({ data }) => (
  <div className="space-y-3 text-sm">
    <div className="flex gap-3 text-xs">
      {data.input_datasets.length > 0 && (
        <div className="bg-blue-50 rounded border border-blue-100 px-2 py-1">
          <span className="text-blue-600 font-medium">Inputs: </span>
          <span className="text-blue-800">{data.input_datasets.join(', ')}</span>
        </div>
      )}
      {data.output_datasets.length > 0 && (
        <div className="bg-green-50 rounded border border-green-100 px-2 py-1">
          <span className="text-green-600 font-medium">Outputs: </span>
          <span className="text-green-800">{data.output_datasets.join(', ')}</span>
        </div>
      )}
    </div>

    <div className="space-y-2">
      {data.steps.map((step) => (
        <div key={step.order} className="flex gap-3 items-start">
          <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white ${
            step.step_type === 'data_prep' ? 'bg-blue-500' :
            step.step_type === 'transform' ? 'bg-purple-500' :
            step.step_type === 'analysis'  ? 'bg-indigo-500' :
            step.step_type === 'output'    ? 'bg-teal-500' : 'bg-gray-500'
          }`}>
            {step.order}
          </div>
          <div className="flex-1 bg-white rounded border p-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-gray-800 text-xs">{step.name}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded capitalize ${
                step.step_type === 'data_prep' ? 'bg-blue-100 text-blue-700' :
                step.step_type === 'transform' ? 'bg-purple-100 text-purple-700' :
                step.step_type === 'analysis'  ? 'bg-indigo-100 text-indigo-700' :
                step.step_type === 'output'    ? 'bg-teal-100 text-teal-700' : 'bg-gray-100 text-gray-700'
              }`}>{step.step_type.replace(/_/g, ' ')}</span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">{step.description}</p>
            {step.sas_constructs.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {step.sas_constructs.map(c => (
                  <span key={c} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-mono">{c}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  </div>
);

const PackagesDetail: React.FC<{ data: NonNullable<EngineResults['packages']> }> = ({ data }) => (
  <div className="space-y-3 text-sm">
    <div>
      <p className="text-xs font-medium text-gray-600 mb-1">Selected packages:</p>
      <div className="flex flex-wrap gap-2">
        {data.all_packages.map(pkg => (
          <span key={pkg} className={`px-2.5 py-1 rounded-full text-xs font-medium font-mono border ${
            pkg === 'dplyr' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' :
            pkg === 'tidyr' ? 'bg-blue-50 text-blue-700 border-blue-200' :
            pkg === 'survival' ? 'bg-purple-50 text-purple-700 border-purple-200' :
            pkg === 'base'  ? 'bg-gray-50 text-gray-600 border-gray-200' :
            'bg-orange-50 text-orange-700 border-orange-200'
          }`}>
            {pkg}
          </span>
        ))}
      </div>
    </div>

    {data.primary_packages.filter(p => p.name !== 'base').slice(0, 4).map(pkg => (
      <div key={pkg.name} className="bg-white rounded border p-3">
        <div className="flex items-start justify-between gap-2">
          <span className="font-mono font-semibold text-gray-800">{pkg.name}</span>
          <span className="text-xs text-gray-500 text-right">{pkg.purpose}</span>
        </div>
        <p className="text-xs text-gray-600 mt-1">{pkg.rationale}</p>
        {pkg.functions_used.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {pkg.functions_used.slice(0, 6).map(fn => (
              <span key={fn} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded font-mono">{fn}</span>
            ))}
          </div>
        )}
        {pkg.alternatives.length > 0 && (
          <p className="text-xs text-gray-400 mt-1">Alternatives: {pkg.alternatives.join(', ')}</p>
        )}
      </div>
    ))}

    <div className="bg-white rounded border p-3">
      <p className="text-xs font-medium text-gray-600 mb-1">Auto-install snippet (included in R code):</p>
      <pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap bg-gray-50 rounded p-2 overflow-x-auto">
        {data.install_code}
      </pre>
    </div>
  </div>
);

const TranslationDetail: React.FC<{ data: NonNullable<EngineResults['translation']> }> = ({ data }) => (
  <div className="space-y-3 text-sm">
    <div className="grid grid-cols-2 gap-3">
      <div className="bg-white rounded border p-2 text-center">
        <div className="text-xl font-bold text-orange-700">{data.lines_of_code}</div>
        <div className="text-xs text-gray-500">Lines of R code</div>
      </div>
      <div className="bg-white rounded border p-2 text-center">
        <div className="text-xl font-bold text-orange-700">{data.packages_used.length}</div>
        <div className="text-xs text-gray-500">Packages used</div>
      </div>
    </div>

    {data.translation_notes.length > 0 && (
      <div className="bg-white rounded border p-3">
        <p className="text-xs font-medium text-gray-600 mb-2">Translation notes:</p>
        <ul className="space-y-1">
          {data.translation_notes.map((note, i) => (
            <li key={i} className="text-xs text-gray-700 flex items-start gap-1">
              <span className="text-orange-400 mt-0.5">•</span>
              <span>{note}</span>
            </li>
          ))}
        </ul>
      </div>
    )}

    {data.warnings.length > 0 && (
      <div className="bg-yellow-50 rounded border border-yellow-200 p-3">
        <p className="text-xs font-medium text-yellow-800 mb-1">Items for manual review:</p>
        <ul className="space-y-1">
          {data.warnings.map((w, i) => (
            <li key={i} className="text-xs text-yellow-700 flex items-start gap-1">
              <AlertCircle className="w-3 h-3 text-yellow-500 mt-0.5 flex-shrink-0" />
              <span>{w}</span>
            </li>
          ))}
        </ul>
      </div>
    )}
  </div>
);

const ValidationDetail: React.FC<{ data: NonNullable<EngineResults['validation']> }> = ({ data }) => {
  const statusColor = {
    approved:               'bg-green-100 text-green-800 border-green-200',
    approved_with_warnings: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    needs_review:           'bg-orange-100 text-orange-800 border-orange-200',
    requires_revision:      'bg-red-100 text-red-800 border-red-200',
  }[data.approval_status] ?? 'bg-gray-100 text-gray-700 border-gray-200';

  return (
    <div className="space-y-3 text-sm">
      <div className={`rounded border px-3 py-2 text-xs font-medium ${statusColor}`}>
        {data.validation_summary}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <div className="bg-white rounded border p-2">
          <div className={`text-lg font-bold ${data.estimated_equivalence_pct >= 85 ? 'text-green-700' : data.estimated_equivalence_pct >= 70 ? 'text-yellow-700' : 'text-red-700'}`}>
            {data.estimated_equivalence_pct.toFixed(0)}%
          </div>
          <div className="text-xs text-gray-500">Equivalence</div>
        </div>
        <div className="bg-white rounded border p-2">
          <div className={`text-lg font-bold ${data.problem_statement_match ? 'text-green-700' : 'text-orange-700'}`}>
            {data.problem_statement_match ? '✓' : '~'}
          </div>
          <div className="text-xs text-gray-500">Goal match</div>
        </div>
        <div className="bg-white rounded border p-2">
          <div className={`text-lg font-bold ${data.packages_appropriate ? 'text-green-700' : 'text-red-700'}`}>
            {data.packages_appropriate ? '✓' : '✗'}
          </div>
          <div className="text-xs text-gray-500">Packages OK</div>
        </div>
        <div className="bg-white rounded border p-2">
          <div className={`text-sm font-bold capitalize ${
            data.code_complexity === 'simple' ? 'text-green-700' :
            data.code_complexity === 'moderate' ? 'text-blue-700' :
            'text-orange-700'
          }`}>{data.code_complexity}</div>
          <div className="text-xs text-gray-500">Complexity</div>
        </div>
      </div>

      {data.strengths.length > 0 && (
        <div className="bg-green-50 rounded border border-green-200 p-3">
          <p className="text-xs font-medium text-green-800 mb-1">Strengths:</p>
          <ul className="space-y-0.5">
            {data.strengths.map((s, i) => (
              <li key={i} className="text-xs text-green-700 flex items-start gap-1">
                <CheckCircle2 className="w-3 h-3 mt-0.5 flex-shrink-0" />{s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.issues.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-600">Validation issues:</p>
          {data.issues.map((issue, i) => (
            <div key={i} className={`rounded border p-2 text-xs ${
              issue.severity === 'error'   ? 'bg-red-50 border-red-200 text-red-800' :
              issue.severity === 'warning' ? 'bg-yellow-50 border-yellow-200 text-yellow-800' :
              'bg-gray-50 border-gray-200 text-gray-700'
            }`}>
              <p className="font-medium">{issue.title}</p>
              <p className="opacity-80">{issue.detail}</p>
              {issue.suggestion && <p className="mt-0.5 italic opacity-70">→ {issue.suggestion}</p>}
            </div>
          ))}
        </div>
      )}

      {data.recommendations.length > 0 && (
        <div className="bg-blue-50 rounded border border-blue-200 p-3">
          <p className="text-xs font-medium text-blue-800 mb-1">Recommendations:</p>
          <ul className="space-y-0.5">
            {data.recommendations.map((r, i) => (
              <li key={i} className="text-xs text-blue-700">• {r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

// ── engine panel ───────────────────────────────────────────────────────────────

interface EnginePanelProps {
  config: (typeof ENGINE_CONFIG)[number];
  engineData: EngineResults;
  isRunning: boolean;
  isDone: boolean;
  index: number;
}

const EnginePanel: React.FC<EnginePanelProps> = ({ config, engineData, isRunning, isDone, index }) => {
  const [expanded, setExpanded] = useState(false);
  const colors = COLOR_MAP[config.color];
  const Icon = config.icon;
  const data = (engineData as any)[config.key];
  const hasData = isDone && !!data;

  // Auto-expand validation and intent on completion
  useEffect(() => {
    if (hasData && (config.key === 'validation' || config.key === 'intent')) {
      setExpanded(true);
    }
  }, [hasData]);

  return (
    <div className={`rounded-lg border transition-all duration-300 ${
      isDone  ? `${colors.bg} ${colors.border}` :
      isRunning ? 'bg-blue-50 border-blue-300 animate-pulse' :
      'bg-gray-50 border-gray-200'
    }`}>
      <button
        className="w-full flex items-center gap-3 p-4 text-left"
        onClick={() => hasData && setExpanded(v => !v)}
        disabled={!hasData}
      >
        {/* Status icon */}
        <div className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center ${
          isDone  ? `bg-white ${colors.border} border-2` :
          isRunning ? 'bg-white border-2 border-blue-300' :
          'bg-white border-2 border-gray-200'
        }`}>
          {isDone    ? <Icon className={`w-4 h-4 ${colors.icon}`} /> :
           isRunning ? <Loader2 className="w-4 h-4 text-blue-500 animate-spin" /> :
           <Clock className="w-4 h-4 text-gray-300" />}
        </div>

        {/* Label */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-medium ${
              isDone ? 'text-gray-400' : 'text-gray-400'
            }`}>Engine {index + 1}</span>
            {isDone && <Badge label="Done" color={config.color} />}
            {isRunning && <Badge label="Running" color="blue" />}
          </div>
          <p className={`font-semibold text-sm ${isDone ? colors.text : 'text-gray-500'}`}>
            {config.label}
          </p>
          <p className="text-xs text-gray-500 truncate">{config.subtitle}</p>
        </div>

        {/* Quick summary */}
        {isDone && data && (
          <div className="hidden sm:block text-right flex-shrink-0 max-w-[180px]">
            <p className="text-xs text-gray-600 line-clamp-2">
              {config.key === 'parse'       && `${(data as any).proc_types?.length ?? 0} PROCs, ${(data as any).total_statements ?? 0} statements`}
              {config.key === 'intent'      && `${(data as any).problem_domain} — ${(data as any).primary_goal?.replace(/_/g, ' ')}`}
              {config.key === 'flow'        && `${(data as any).total_steps} execution steps`}
              {config.key === 'packages'    && (data as any).all_packages?.join(', ')}
              {config.key === 'translation' && `${(data as any).lines_of_code} lines of R code`}
              {config.key === 'validation'  && `${(data as any).estimated_equivalence_pct?.toFixed(0)}% equivalence`}
            </p>
          </div>
        )}

        {/* Expand chevron */}
        {hasData && (
          <div className="flex-shrink-0 ml-1">
            {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
          </div>
        )}
      </button>

      {/* Expandable detail */}
      {expanded && hasData && (
        <div className="px-4 pb-4 border-t border-white/60 pt-3">
          {config.key === 'parse'       && <ParseDetail       data={data} />}
          {config.key === 'intent'      && <IntentDetail      data={data} />}
          {config.key === 'flow'        && <FlowDetail        data={data} />}
          {config.key === 'packages'    && <PackagesDetail    data={data} />}
          {config.key === 'translation' && <TranslationDetail data={data} />}
          {config.key === 'validation'  && <ValidationDetail  data={data} />}
        </div>
      )}
    </div>
  );
};

// ── main component ─────────────────────────────────────────────────────────────

const TranslationStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [autoStarted, setAutoStarted] = useState(false);

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.getById(projectId!),
    enabled: !!projectId,
    staleTime: 0,
  });

  const startTranslationMutation = useMutation({
    mutationFn: () => projectsApi.startTranslation(projectId!),
    onSuccess: () => {
      // Remove any stale cached translation results so the new translation is
      // fetched fresh — prevents old project data from flashing on screen.
      queryClient.removeQueries({ queryKey: ['translation-status', projectId] });
      queryClient.removeQueries({ queryKey: ['translation-r-code', projectId] });
      setAutoStarted(true);
    },
  });

  const { data: status } = useQuery({
    queryKey: ['translation-status', projectId],
    queryFn: () => projectsApi.getTranslationStatus(projectId!),
    enabled: autoStarted,
    staleTime: 0,
    refetchInterval: (query) =>
      query.state.data?.status === 'completed' ? false : 2000,
  });

  useEffect(() => {
    if (!autoStarted && projectId) {
      startTranslationMutation.mutate();
    }
  }, [projectId, autoStarted]);

  const isCompleted = status?.status === 'completed';
  const isFailed    = status?.status === 'failed';
  const engineResults: EngineResults = (status as any)?.engine_results ?? {};

  const { data: rCodeData } = useQuery({
    queryKey: ['translation-r-code', projectId, isCompleted],
    queryFn: async () => {
      try {
        const full = await projectsApi.getRCode(projectId!);
        return full.r_code;
      } catch {
        return status?.r_code_preview ?? '';
      }
    },
    enabled: !!projectId && isCompleted,
  });

  const handleExportRCode = () => {
    if (!projectId) return;
    window.open(projectsApi.getRCodeDownloadUrl(projectId), '_blank');
  };

  const progress = status?.progress ?? 0;

  // Animate engines sequentially based on progress
  const engineProgress = isCompleted ? 6 : Math.floor((progress / 100) * 6);

  return (
    <div className="max-w-4xl space-y-6">
      {/* ── Header card ─────────────────────────────────────────────────────── */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-11 h-11 bg-blue-100 rounded-full flex items-center justify-center">
            <Code className="w-5 h-5 text-blue-600" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900">Translation Module</h2>
            <div className="flex items-center gap-2 mt-0.5">
              <Sparkles className="w-3.5 h-3.5 text-purple-500" />
              <span className="text-xs text-purple-600 font-medium">
                Six-Engine AI Translation Pipeline
              </span>
            </div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-gray-600">
              {isCompleted ? 'All 6 engines completed — translation ready!' :
               isFailed    ? 'Translation failed' :
               `Running engine ${Math.min(engineProgress + 1, 6)} of 6…`}
            </span>
            <span className="font-medium text-gray-700">{progress}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                isCompleted ? 'bg-green-500' : isFailed ? 'bg-red-500' : 'bg-blue-600'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Engine mini-progress dots */}
        <div className="flex items-center gap-1.5">
          {ENGINE_CONFIG.map((eng, i) => (
            <div
              key={eng.key}
              title={eng.label}
              className={`flex-1 h-1.5 rounded-full transition-all duration-500 ${
                i < engineProgress ? COLOR_MAP[eng.color].badge.split(' ')[0] :
                i === engineProgress && !isCompleted ? 'bg-blue-400 animate-pulse' :
                'bg-gray-200'
              }`}
            />
          ))}
        </div>
      </div>

      {/* ── Six engine panels ────────────────────────────────────────────────── */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-gray-700 px-1">Pipeline Engines</h3>
        {ENGINE_CONFIG.map((config, i) => (
          <EnginePanel
            key={config.key}
            config={config}
            engineData={engineResults}
            isRunning={!isCompleted && !isFailed && i === engineProgress}
            isDone={isCompleted || i < engineProgress}
            index={i}
          />
        ))}
      </div>

      {/* ── Side-by-side code view ───────────────────────────────────────────── */}
      {isCompleted && (project?.sas_code || rCodeData || status?.r_code_preview) && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">SAS vs Generated R Code</h3>
            <button
              onClick={handleExportRCode}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <Download className="w-3.5 h-3.5" />
              Download R Script
            </button>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">SAS Input</p>
              <div className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-auto max-h-[400px]">
                <pre className="text-xs font-mono whitespace-pre-wrap">
                  {project?.sas_code ?? '# SAS input not available'}
                </pre>
              </div>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">Generated R Code</p>
              <div className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-auto max-h-[400px]">
                <pre className="text-xs font-mono whitespace-pre-wrap">
                  {rCodeData ?? status?.r_code_preview ?? '# R code not available yet'}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Warnings (from translation engine) ──────────────────────────────── */}
      {status?.warnings && status.warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-sm font-medium text-yellow-900 mb-2">Items requiring manual review:</h3>
              <ul className="space-y-1">
                {status.warnings.map((w, i) => (
                  <li key={i} className="text-xs text-yellow-800">• {w}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* ── Actions ──────────────────────────────────────────────────────────── */}
      <div className="flex gap-3">
        <button
          onClick={() => navigate(`/projects/${projectId}/upload`)}
          className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm"
        >
          Back
        </button>
        <button
          onClick={() => navigate(`/projects/${projectId}/execution`)}
          disabled={!isCompleted}
          className="flex-[2] flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm"
        >
          {isCompleted ? (
            <>Continue to Execution <ArrowRight className="w-4 h-4" /></>
          ) : (
            <><Loader2 className="w-4 h-4 animate-spin" /> Running pipeline…</>
          )}
        </button>
      </div>
    </div>
  );
};

export default TranslationStep;
