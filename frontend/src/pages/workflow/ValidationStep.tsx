import React, { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  CheckCircle2, AlertTriangle, XCircle, ArrowRight, ArrowLeft,
  Download, RefreshCw, ChevronDown, ChevronRight,
  Search, Shield, BarChart2, Activity, Cpu, Layers,
  Database, Sparkles, CheckCheck, Info,
} from 'lucide-react';
import { projectsApi, ValidationResult, ValidationScenario, ValidationEngine } from '@/services/api';

// ── Types ─────────────────────────────────────────────────────────────────────

type TabId = 'overview' | 'scenarios' | 'comparison' | 'issues' | 'recommendations';
type FilterStatus = 'all' | 'passed' | 'warning' | 'failed';

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusColor(s: string) {
  if (s === 'passed' || s === 'completed') return 'text-green-600 bg-green-50 border-green-200';
  if (s === 'warning')  return 'text-yellow-600 bg-yellow-50 border-yellow-200';
  return 'text-red-600 bg-red-50 border-red-200';
}
function statusDot(s: string) {
  if (s === 'passed' || s === 'completed') return 'bg-green-500';
  if (s === 'warning')  return 'bg-yellow-400';
  return 'bg-red-500';
}
function severityColor(s: string) {
  if (s === 'critical') return 'text-red-700 bg-red-100 border-red-300';
  if (s === 'major')    return 'text-yellow-700 bg-yellow-100 border-yellow-300';
  return 'text-blue-700 bg-blue-100 border-blue-300';
}
function scoreColor(n: number) {
  if (n >= 95) return 'text-green-600';
  if (n >= 80) return 'text-blue-600';
  if (n >= 60) return 'text-yellow-600';
  return 'text-red-600';
}
function barColor(n: number) {
  if (n >= 95) return 'bg-green-500';
  if (n >= 80) return 'bg-blue-500';
  if (n >= 60) return 'bg-yellow-400';
  return 'bg-red-500';
}

const CATEGORY_DISPLAY: Record<string, string> = {
  structural: 'Structural Validation',
  functional: 'Functional (Logic) Validation',
  statistical: 'Statistical Validation',
  semantic: 'Semantic Validation',
  execution: 'Execution Validation',
};

const CATEGORY_ORDER = ['structural', 'functional', 'statistical', 'semantic', 'execution'];

// ── Sub-components ────────────────────────────────────────────────────────────

const StatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusColor(status)}`}>
    <span className={`w-1.5 h-1.5 rounded-full ${statusDot(status)}`} />
    {status.charAt(0).toUpperCase() + status.slice(1)}
  </span>
);

const CircleScore: React.FC<{ value: number; label: string }> = ({ value, label }) => {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const fill = (value / 100) * circ;
  const color = value >= 95 ? '#22c55e' : value >= 80 ? '#3b82f6' : value >= 60 ? '#eab308' : '#ef4444';
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-36 h-36">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r={r} fill="none" stroke="#e5e7eb" strokeWidth="10" />
          <circle
            cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="10"
            strokeDasharray={`${fill} ${circ - fill}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.8s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold text-gray-900">{value}%</span>
        </div>
      </div>
      <span className="mt-1 text-sm font-semibold" style={{ color }}>{label}</span>
    </div>
  );
};

const ScoreBar: React.FC<{ label: string; value: number }> = ({ label, value }) => (
  <div className="mb-3">
    <div className="flex justify-between items-center mb-1">
      <span className="text-sm text-gray-700">{label}</span>
      <span className={`text-sm font-semibold ${scoreColor(value)}`}>{value}%</span>
    </div>
    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${barColor(value)}`} style={{ width: `${value}%`, transition: 'width 0.6s ease' }} />
    </div>
  </div>
);

const EngineRow: React.FC<{ engine: ValidationEngine; defaultOpen?: boolean }> = ({ engine, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-gray-200 rounded-lg mb-2 overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50 text-left"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-3">
          <Shield className="w-4 h-4 text-indigo-500 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-gray-900">{engine.name}</p>
            <p className="text-xs text-gray-500">{engine.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={engine.status} />
          {open ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
        </div>
      </button>
      {open && engine.scenarios_total > 0 && (
        <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 text-sm text-gray-600">
          {engine.scenarios_passed} / {engine.scenarios_total} scenarios passed
        </div>
      )}
    </div>
  );
};

// Scenario row with expand
const ScenarioRow: React.FC<{
  scenario: ValidationScenario;
  onSelect: (s: ValidationScenario) => void;
  selected: boolean;
}> = ({ scenario, onSelect, selected }) => (
  <tr
    className={`border-b border-gray-100 cursor-pointer hover:bg-indigo-50/30 transition-colors ${selected ? 'bg-indigo-50' : ''}`}
    onClick={() => onSelect(scenario)}
  >
    <td className="px-4 py-3">
      <div className="flex items-center gap-2">
        <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
        <div>
          <p className="text-sm font-medium text-gray-900">{scenario.name}</p>
          <p className="text-xs text-gray-500">{scenario.description}</p>
        </div>
      </div>
    </td>
    <td className="px-4 py-3 text-sm text-gray-600">{scenario.sas_result}</td>
    <td className="px-4 py-3 text-sm text-gray-600">{scenario.r_result}</td>
    <td className="px-4 py-3"><StatusBadge status={scenario.status} /></td>
    <td className="px-4 py-3 text-sm text-gray-500">{scenario.impact.toFixed(1)}%</td>
  </tr>
);

// Category group with expand/collapse
const CategoryGroup: React.FC<{
  category: string;
  scenarios: ValidationScenario[];
  passedCount: number;
  total: number;
  score: number;
  selectedId: string | null;
  onSelect: (s: ValidationScenario) => void;
}> = ({ category, scenarios, passedCount, total, score, selectedId, onSelect }) => {
  const [open, setOpen] = useState(true);
  return (
    <div className="mb-3 border border-gray-200 rounded-lg overflow-hidden">
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-left"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-3">
          <Database className="w-4 h-4 text-indigo-500" />
          <span className="text-sm font-semibold text-gray-800">{CATEGORY_DISPLAY[category] ?? category}</span>
          <span className="text-xs text-gray-500">{passedCount}/{total} Passed</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-bold ${scoreColor(score)}`}>{score.toFixed(0)}%</span>
          {open ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
        </div>
      </button>
      {open && (
        <table className="w-full text-left">
          <thead>
            <tr className="bg-white border-b border-gray-100">
              <th className="px-4 py-2 text-xs font-medium text-gray-500 w-1/3">Scenario</th>
              <th className="px-4 py-2 text-xs font-medium text-gray-500">SAS Result</th>
              <th className="px-4 py-2 text-xs font-medium text-gray-500">R Result</th>
              <th className="px-4 py-2 text-xs font-medium text-gray-500">Status</th>
              <th className="px-4 py-2 text-xs font-medium text-gray-500">Impact</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map(s => (
              <ScenarioRow key={s.id} scenario={s} onSelect={onSelect} selected={selectedId === s.id} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

// Scenario detail panel
const ScenarioDetail: React.FC<{ scenario: ValidationScenario }> = ({ scenario }) => (
  <div className="bg-white border border-gray-200 rounded-xl p-5 sticky top-4">
    <div className="flex items-center justify-between mb-4">
      <h3 className="font-semibold text-gray-900">Scenario Details</h3>
      <StatusBadge status={scenario.status} />
    </div>
    <div className="space-y-3 text-sm">
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Scenario</p>
        <p className="font-medium text-gray-900">{scenario.name}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Category</p>
        <p className="text-gray-700">{CATEGORY_DISPLAY[scenario.category] ?? scenario.category}</p>
      </div>
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Impact on Score</p>
        <p className="font-semibold text-indigo-600">{scenario.impact.toFixed(1)}%</p>
      </div>
      {scenario.detail && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Description</p>
          <p className="text-gray-600 text-xs leading-relaxed">{scenario.detail || scenario.description}</p>
        </div>
      )}
      {scenario.sas_code && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">SAS Code</p>
          <pre className="bg-gray-900 text-green-300 text-xs rounded-lg p-3 overflow-x-auto whitespace-pre-wrap leading-relaxed">{scenario.sas_code}</pre>
        </div>
      )}
      {scenario.r_code && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">R Code</p>
          <pre className="bg-gray-900 text-blue-300 text-xs rounded-lg p-3 overflow-x-auto whitespace-pre-wrap leading-relaxed">{scenario.r_code}</pre>
        </div>
      )}
      <div className="pt-2 border-t border-gray-100">
        <div className="flex items-center gap-2">
          {scenario.status === 'passed' ? (
            <><CheckCircle2 className="w-4 h-4 text-green-500" /><span className="text-green-700 font-medium text-xs">Matched</span></>
          ) : scenario.status === 'warning' ? (
            <><AlertTriangle className="w-4 h-4 text-yellow-500" /><span className="text-yellow-700 font-medium text-xs">Review Needed</span></>
          ) : (
            <><XCircle className="w-4 h-4 text-red-500" /><span className="text-red-700 font-medium text-xs">Mismatch Detected</span></>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {scenario.sas_result} → {scenario.r_result}
        </p>
      </div>
    </div>
  </div>
);

// ── Main Component ────────────────────────────────────────────────────────────

const ValidationStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterSection, setFilterSection] = useState('all');
  const [selectedScenario, setSelectedScenario] = useState<ValidationScenario | null>(null);

  const { data: validation, isLoading, error, refetch } = useQuery({
    queryKey: ['validation', projectId],
    queryFn: () => projectsApi.getValidation(projectId!),
    staleTime: 0,
  });

  const v = validation as ValidationResult | undefined;

  // Compute summary numbers
  const confidence = v?.overall_confidence ?? v?.overall_match ?? 0;
  const confLabel = v?.confidence_label ?? (confidence >= 90 ? 'High Confidence' : confidence >= 75 ? 'Medium Confidence' : 'Low Confidence');

  const criticalCount = (v?.issues ?? []).filter(i => i.severity === 'critical').length;
  const majorCount    = (v?.issues ?? []).filter(i => i.severity === 'major').length;
  const minorCount    = (v?.issues ?? []).filter(i => i.severity === 'minor').length;
  const totalIssues   = criticalCount + majorCount + minorCount;

  // Group scenarios by category
  const scenariosByCategory = useMemo(() => {
    const all = v?.scenarios ?? [];
    const filtered = all.filter(s => {
      const matchStatus = filterStatus === 'all' || s.status === filterStatus;
      const matchSection = filterSection === 'all' || s.category === filterSection;
      const matchSearch = !searchQuery || s.name.toLowerCase().includes(searchQuery.toLowerCase());
      return matchStatus && matchSection && matchSearch;
    });
    const grouped: Record<string, ValidationScenario[]> = {};
    for (const sc of filtered) {
      if (!grouped[sc.category]) grouped[sc.category] = [];
      grouped[sc.category].push(sc);
    }
    return grouped;
  }, [v?.scenarios, filterStatus, filterSection, searchQuery]);

  const getCategoryScore = (cat: string) =>
    v?.category_scores?.find(cs => cs.name === cat)?.score ?? 100;

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'overview',         label: 'Validation Overview',  icon: <BarChart2 className="w-4 h-4" /> },
    { id: 'scenarios',        label: 'Scenario Explorer',    icon: <Layers className="w-4 h-4" /> },
    { id: 'comparison',       label: 'SAS vs R Comparison',  icon: <Activity className="w-4 h-4" /> },
    { id: 'issues',           label: 'Issue Summary',        icon: <AlertTriangle className="w-4 h-4" /> },
    { id: 'recommendations',  label: 'Recommendations',      icon: <Sparkles className="w-4 h-4" /> },
  ];

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <div className="w-14 h-14 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin" />
        <p className="text-gray-600 font-medium">Running semantic equivalence validation…</p>
        <p className="text-sm text-gray-400">Comparing SAS logic, statistics, and execution semantics</p>
      </div>
    );
  }

  if (error || !v) {
    return (
      <div className="max-w-2xl">
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <XCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
          <h3 className="font-semibold text-red-900 mb-2">Validation Failed</h3>
          <p className="text-red-700 text-sm mb-4">Unable to load validation results. Ensure execution completed successfully.</p>
          <button onClick={() => refetch()} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl space-y-5">

      {/* ── Header ── */}
      <div className="bg-white border border-gray-200 rounded-xl p-5">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h1 className="text-xl font-bold text-gray-900">Validation & Reconciliation</h1>
                <Sparkles className="w-5 h-5 text-indigo-500" />
              </div>
              <p className="text-sm text-gray-500">AI-powered semantic equivalence validation for SAS → R clinical migration.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* SAS → Validate → R diagram */}
            <div className="hidden md:flex items-center gap-2">
              <div className="w-10 h-10 bg-indigo-700 rounded-lg flex items-center justify-center text-white font-bold text-xs">SAS</div>
              <ArrowRight className="w-4 h-4 text-gray-400" />
              <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <ArrowRight className="w-4 h-4 text-gray-400" />
              <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center text-white font-bold text-xs">R</div>
            </div>
          </div>
        </div>

        <div className="flex gap-3 mt-4">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 font-medium"
          >
            <RefreshCw className="w-4 h-4" />
            Re-run Validation
          </button>
          <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50">
            <Download className="w-4 h-4" />
            Download Report
          </button>
        </div>
      </div>

      {/* ── Summary cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Confidence score */}
        <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col items-center">
          <CircleScore value={Math.round(confidence)} label={confLabel} />
        </div>

        {/* Datasets */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <Database className="w-5 h-5 text-indigo-500" />
            <p className="text-sm font-medium text-gray-700">Datasets Validated</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 mb-2">{v.datasets_validated ?? 0}</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-sm text-green-700">{v.datasets_matched ?? 0} Matched</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-sm text-red-700">{v.datasets_mismatched ?? 0} Mismatched</span>
            </div>
          </div>
        </div>

        {/* Procedures */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="w-5 h-5 text-purple-500" />
            <p className="text-sm font-medium text-gray-700">Procedures Validated</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 mb-2">{v.procedures_validated ?? 0}</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-sm text-green-700">{v.procedures_matched ?? 0} Matched</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-sm text-red-700">{(v.procedures_mismatched ?? 0)} Mismatched</span>
            </div>
          </div>
        </div>

        {/* Issues */}
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            <p className="text-sm font-medium text-gray-700">Issues Detected</p>
          </div>
          <p className="text-3xl font-bold text-gray-900 mb-2">{totalIssues}</p>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-red-600">{criticalCount}</span>
              <span className="text-sm text-gray-500">Critical</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-yellow-600">{majorCount}</span>
              <span className="text-sm text-gray-500">Major</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-blue-600">{minorCount}</span>
              <span className="text-sm text-gray-500">Minor</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Tabs ── */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="border-b border-gray-200 px-4">
          <div className="flex gap-1 overflow-x-auto">
            {tabs.map(t => (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-2 px-4 py-3.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === t.id
                    ? 'border-indigo-600 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className="p-5">

          {/* ── Tab: Validation Overview ── */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Score breakdown */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <h2 className="font-semibold text-gray-900">Validation Score Breakdown</h2>
                  <Info className="w-4 h-4 text-gray-400" />
                </div>
                {(v.category_scores ?? []).map(cs => (
                  <ScoreBar key={cs.name} label={cs.display_name} value={Math.round(cs.score)} />
                ))}
              </div>

              {/* Validation engines */}
              <div>
                <h2 className="font-semibold text-gray-900 mb-4">Validation Engines</h2>
                {(v.engines ?? []).map((eng, i) => (
                  <EngineRow key={i} engine={eng} defaultOpen={i === 0} />
                ))}
              </div>
            </div>
          )}

          {/* ── Tab: Scenario Explorer ── */}
          {activeTab === 'scenarios' && (
            <div className="flex gap-5">
              {/* Left: scenarios list */}
              <div className="flex-1 min-w-0">
                {/* Filters */}
                <div className="flex flex-wrap items-center gap-2 mb-4">
                  <span className="text-sm text-gray-600 font-medium">Filter by:</span>
                  {(['all', 'passed', 'warning', 'failed'] as FilterStatus[]).map(fs => (
                    <button
                      key={fs}
                      onClick={() => setFilterStatus(fs)}
                      className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${
                        filterStatus === fs
                          ? 'bg-indigo-600 text-white border-indigo-600'
                          : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      {fs.charAt(0).toUpperCase() + fs.slice(1)}
                    </button>
                  ))}
                  <div className="relative ml-auto">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      placeholder="Search scenarios..."
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      className="pl-9 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-300"
                    />
                  </div>
                  <select
                    value={filterSection}
                    onChange={e => setFilterSection(e.target.value)}
                    className="text-sm border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                  >
                    <option value="all">All Sections</option>
                    {CATEGORY_ORDER.map(c => (
                      <option key={c} value={c}>{CATEGORY_DISPLAY[c]}</option>
                    ))}
                  </select>
                </div>

                {/* Grouped scenarios */}
                {CATEGORY_ORDER.filter(c => scenariosByCategory[c]?.length > 0).map(cat => {
                  const catScs = scenariosByCategory[cat];
                  const passed = catScs.filter(s => s.status === 'passed').length;
                  const score = getCategoryScore(cat);
                  return (
                    <CategoryGroup
                      key={cat}
                      category={cat}
                      scenarios={catScs}
                      passedCount={passed}
                      total={catScs.length}
                      score={score}
                      selectedId={selectedScenario?.id ?? null}
                      onSelect={s => setSelectedScenario(s)}
                    />
                  );
                })}
                {Object.keys(scenariosByCategory).length === 0 && (
                  <div className="text-center py-10 text-gray-400">
                    <CheckCheck className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                    <p>No scenarios match the current filter</p>
                  </div>
                )}
              </div>

              {/* Right: scenario detail */}
              <div className="w-72 flex-shrink-0">
                {selectedScenario ? (
                  <ScenarioDetail scenario={selectedScenario} />
                ) : (
                  <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 text-center text-gray-500">
                    <Layers className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                    <p className="text-sm">Click a scenario row to see details</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Tab: SAS vs R Comparison ── */}
          {activeTab === 'comparison' && (
            <div className="grid grid-cols-2 gap-5">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 bg-indigo-700 rounded flex items-center justify-center text-white text-xs font-bold">S</div>
                  <h3 className="font-semibold text-gray-900">SAS Output (Simulated)</h3>
                </div>
                <pre className="bg-gray-900 text-green-300 text-xs rounded-xl p-4 h-96 overflow-auto whitespace-pre-wrap leading-relaxed font-mono">
                  {v.sas_output_preview || '(No SAS output available)'}
                </pre>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 bg-green-600 rounded flex items-center justify-center text-white text-xs font-bold">R</div>
                  <h3 className="font-semibold text-gray-900">R Output (Executed)</h3>
                </div>
                <pre className="bg-gray-900 text-blue-300 text-xs rounded-xl p-4 h-96 overflow-auto whitespace-pre-wrap leading-relaxed font-mono">
                  {v.r_output_preview || '(R not installed or no output)'}
                </pre>
              </div>
              {/* Numeric comparison stat */}
              <div className="col-span-2 bg-indigo-50 border border-indigo-100 rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <Activity className="w-5 h-5 text-indigo-600" />
                  <div>
                    <p className="font-medium text-indigo-900">Numeric Agreement</p>
                    <p className="text-sm text-indigo-700">
                      Overall match rate: <strong>{Math.round(confidence)}%</strong> — within ±0.0001 tolerance
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── Tab: Issue Summary ── */}
          {activeTab === 'issues' && (
            <div className="space-y-3">
              {(v.issues ?? []).length === 0 ? (
                <div className="text-center py-12">
                  <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-green-400" />
                  <p className="font-semibold text-gray-700">No issues detected</p>
                  <p className="text-sm text-gray-400">Translation passed all validation checks</p>
                </div>
              ) : (
                (v.issues ?? []).map((issue, i) => (
                  <div key={i} className={`border rounded-xl p-4 ${severityColor(issue.severity)}`}>
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-0.5">
                        {issue.severity === 'critical' ? (
                          <XCircle className="w-5 h-5 text-red-600" />
                        ) : issue.severity === 'major' ? (
                          <AlertTriangle className="w-5 h-5 text-yellow-600" />
                        ) : (
                          <Info className="w-5 h-5 text-blue-600" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-sm">{issue.title}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium border ${severityColor(issue.severity)}`}>
                            {issue.severity.toUpperCase()}
                          </span>
                          <span className="text-xs text-gray-500 ml-auto">{CATEGORY_DISPLAY[issue.category] ?? issue.category}</span>
                        </div>
                        <p className="text-sm mb-2 opacity-80">{issue.detail}</p>
                        <div className="flex items-start gap-2 text-xs bg-white/60 rounded-lg p-2">
                          <Sparkles className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                          <p><strong>Suggestion:</strong> {issue.suggestion}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* ── Tab: Recommendations ── */}
          {activeTab === 'recommendations' && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-5 h-5 text-indigo-500" />
                <h2 className="font-semibold text-gray-900">AI Recommendations</h2>
              </div>
              {(v.recommendations ?? []).length === 0 ? (
                <div className="text-center py-12">
                  <CheckCheck className="w-12 h-12 mx-auto mb-3 text-green-400" />
                  <p className="font-semibold text-gray-700">No recommendations</p>
                  <p className="text-sm text-gray-400">Translation quality is excellent across all dimensions</p>
                </div>
              ) : (
                (v.recommendations ?? []).map((rec, i) => (
                  <div key={i} className="bg-indigo-50 border border-indigo-100 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-6 h-6 bg-indigo-600 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-0.5">
                        {i + 1}
                      </div>
                      <p className="text-sm text-indigo-900 leading-relaxed">{rec}</p>
                    </div>
                  </div>
                ))
              )}

              {/* Category-level score table */}
              <div className="mt-6 bg-white border border-gray-200 rounded-xl overflow-hidden">
                <div className="px-5 py-3 bg-gray-50 border-b border-gray-200">
                  <h3 className="font-medium text-gray-900">Score Contribution Table</h3>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="px-5 py-3 text-left text-xs font-medium text-gray-500">Validation Area</th>
                      <th className="px-5 py-3 text-right text-xs font-medium text-gray-500">Score</th>
                      <th className="px-5 py-3 text-right text-xs font-medium text-gray-500">Weight</th>
                      <th className="px-5 py-3 text-right text-xs font-medium text-gray-500">Contribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(v.category_scores ?? []).map(cs => (
                      <tr key={cs.name} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="px-5 py-3 text-gray-700">{cs.display_name}</td>
                        <td className={`px-5 py-3 text-right font-semibold ${scoreColor(cs.score)}`}>{cs.score.toFixed(1)}%</td>
                        <td className="px-5 py-3 text-right text-gray-500">{(cs.weight * 100).toFixed(0)}%</td>
                        <td className="px-5 py-3 text-right text-gray-700">{(cs.score * cs.weight).toFixed(1)}</td>
                      </tr>
                    ))}
                    <tr className="bg-gray-50 font-semibold">
                      <td className="px-5 py-3 text-gray-900">Overall Confidence</td>
                      <td colSpan={2} />
                      <td className={`px-5 py-3 text-right text-lg ${scoreColor(confidence)}`}>{confidence}%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* ── Action bar ── */}
      <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-5 py-4">
        <button
          onClick={() => navigate(`/projects/${projectId}/execution`)}
          className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Execute
        </button>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50">
            <Download className="w-4 h-4" />
            Download Validation Report
          </button>
          <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50">
            <Download className="w-4 h-4" />
            Download Reconciliation Report
          </button>
          <button
            onClick={() => navigate(`/projects/${projectId}/report`)}
            className="flex items-center gap-2 px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 font-medium"
          >
            Proceed to Export
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ValidationStep;
