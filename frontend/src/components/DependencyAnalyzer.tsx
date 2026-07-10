import React, { useState } from 'react';
import {
  ChevronDown, ChevronRight, AlertCircle,
  TrendingUp, Database, FileSearch, Shield, Zap,
} from 'lucide-react';

interface DependencyAnalyzerProps {
  v2Data: any;
  enhancedData: any;
  qualifications: Record<string, any>;
}

export const DependencyAnalyzer: React.FC<DependencyAnalyzerProps> = ({
  v2Data,
  qualifications,
}) => {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    overview: true,
    datasets: true,
    upload_required: true,
    missing_data: true,
    lineage: false,
    qualifications: false,
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Helper to check if a dataset is uploaded
  const isDatasetUploaded = (dsName: string) => {
    // Strip library prefix and extension from dsName (e.g., "raw.demographics" -> "demographics")
    const cleanName = dsName.toLowerCase()
      .replace(/^(raw|sdtm|adam|work)\./, '')
      .replace(/\.(csv|sas7bdat|xpt)$/, '');

    return Object.keys(qualifications || {}).some(key => {
      // Strip library prefix and extension from the uploaded key (e.g., "raw.demographics.csv" -> "demographics")
      const cleanKey = key.toLowerCase()
        .replace(/^(raw|sdtm|adam|work)\./, '')
        .replace(/\.(csv|sas7bdat|xpt)$/, '');
      
      // Also match base names directly without extension (e.g., "age_summary" === "age_summary")
      const baseKeyWithoutExt = key.toLowerCase().replace(/\.(csv|sas7bdat|xpt)$/, '');
      
      return cleanKey === cleanName || baseKeyWithoutExt === dsName.toLowerCase();
    });
  };

  // Extract v2 data
  const readiness = v2Data?.readiness || {};
  const classifications = v2Data?.classifications || {};
  const allDatasets = v2Data?.all_datasets || [];
  const requiredDatasetsRaw = v2Data?.required_datasets || [];
  const missingData = v2Data?.missing_data || {};
  
  // Filter out datasets that are already uploaded from the required list
  const requiredDatasets = requiredDatasetsRaw.filter((ds: string) => !isDatasetUploaded(ds));
  const lineage = v2Data?.lineage || {};

  // A dataset is satisfied if it's generated, not required to upload, or has been uploaded
  const satisfiedCount = allDatasets.filter((ds: string) => {
    const c = classifications[ds];
    return c?.state === 'generated' || c?.upload_required === false || isDatasetUploaded(ds);
  }).length;

  const getDatasetStatus = (name: string) => {
    const c = classifications[name];
    if (isDatasetUploaded(name)) {
      return { label: 'Satisfied', color: 'emerald', icon: '✓' };
    }
    if (!c) return { label: 'Unknown', color: 'slate', icon: '?' };

    if (c.upload_required === true) {
      return { label: 'Upload Required', color: 'red', icon: '⬇' };
    } else if (c.upload_required === 'conditional') {
      return { label: 'Conditional', color: 'amber', icon: '⚠' };
    } else {
      return { label: 'Satisfied', color: 'emerald', icon: '✓' };
    }
  };

  return (
    <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl border border-indigo-200 shadow-sm overflow-hidden mt-6">
      {/* HEADER */}
      <div className="px-6 py-4 border-b border-indigo-100 flex items-center gap-3 bg-indigo-100/50">
        <Database className="w-5 h-5 text-indigo-600" />
        <div className="flex-1">
          <p className="text-sm font-bold text-slate-900">Dependency Analyzer</p>
          <p className="text-xs text-slate-600">Semantic analysis: dataset lineage, upload requirements, translation readiness</p>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* ══════════════════════════════════════════════════════════════ */
        /* SECTION 1: OVERVIEW (Semantic Dependency Statistics)           */
        /* ══════════════════════════════════════════════════════════════ */}
        <div className="border border-indigo-200 rounded-lg overflow-hidden bg-white">
          <button
            onClick={() => toggleSection('overview')}
            className="w-full p-4 flex items-center justify-between hover:bg-indigo-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              {expandedSections.overview ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <TrendingUp className="w-4 h-4 text-indigo-600" />
              <span className="font-bold text-slate-800">Semantic Dependency Statistics</span>
            </div>
            <div className="text-lg font-bold text-indigo-600">{Math.round(readiness.overall || 0)}%</div>
          </button>

          {expandedSections.overview && (
            <div className="p-4 border-t border-indigo-100 space-y-4 bg-slate-50">
              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-blue-100 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-blue-700">{allDatasets.length}</p>
                  <p className="text-xs text-blue-600 font-semibold">Total Analyzed</p>
                </div>
                <div className="bg-red-100 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-red-700">{requiredDatasets.length}</p>
                  <p className="text-xs text-red-600 font-semibold">Upload Required</p>
                </div>
                <div className="bg-emerald-100 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-emerald-700">{satisfiedCount}</p>
                  <p className="text-xs text-emerald-600 font-semibold">Satisfied</p>
                </div>
                <div className="bg-purple-100 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-purple-700">{Math.round(readiness.overall || 0)}%</p>
                  <p className="text-xs text-purple-600 font-semibold">Readiness</p>
                </div>
              </div>

              {/* Readiness Progress */}
              <div>
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-semibold text-slate-700">Translation Readiness</span>
                  <span className="text-sm font-bold text-slate-600">
                    {readiness.ready_for_translation ? '✓ Ready' : '⚠ Not Ready'}
                  </span>
                </div>
                <div className="w-full bg-slate-300 rounded-full h-3">
                  <div
                    className="bg-indigo-600 h-3 rounded-full transition-all"
                    style={{ width: `${readiness.overall || 0}%` }}
                  />
                </div>
              </div>

              {/* Component Scores */}
              {readiness.components && (
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-blue-50 border border-blue-200 rounded p-2 text-center">
                    <p className="text-sm font-bold text-blue-700">{Math.round(readiness.components.data || 0)}%</p>
                    <p className="text-xs text-blue-600">Data</p>
                  </div>
                  <div className="bg-indigo-50 border border-indigo-200 rounded p-2 text-center">
                    <p className="text-sm font-bold text-indigo-700">{Math.round(readiness.components.intent || 0)}%</p>
                    <p className="text-xs text-indigo-600">Intent</p>
                  </div>
                  <div className="bg-purple-50 border border-purple-200 rounded p-2 text-center">
                    <p className="text-sm font-bold text-purple-700">{Math.round(readiness.components.execution || 0)}%</p>
                    <p className="text-xs text-purple-600">Execution</p>
                  </div>
                </div>
              )}

              {/* Blockers */}
              {readiness.blockers && readiness.blockers.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-xs font-bold text-red-600 mb-2">⚠ Translation Blockers:</p>
                  <ul className="text-xs text-red-700 space-y-1">
                    {readiness.blockers.map((blocker: string, i: number) => (
                      <li key={i}>• {blocker}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ══════════════════════════════════════════════════════════════ */
        /* SECTION 2: DATASET REQUIREMENTS (INPUT vs OUTPUT)              */
        /* ══════════════════════════════════════════════════════════════ */}
        <div className="border border-indigo-200 rounded-lg overflow-hidden bg-white">
          <button
            onClick={() => toggleSection('upload_required')}
            className="w-full p-4 flex items-center justify-between hover:bg-indigo-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              {expandedSections.upload_required ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <AlertCircle className="w-4 h-4 text-indigo-600" />
              <span className="font-bold text-slate-800">Dataset Requirements (Input/Output)</span>
            </div>
            <span className="text-sm font-bold text-indigo-600">{requiredDatasets.length} input(s) needed</span>
          </button>

          {expandedSections.upload_required && (
            <div className="p-4 border-t border-indigo-100 bg-slate-50 space-y-4">
              {/* INPUT DATASETS */}
              <div>
                <p className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                  <span className="text-lg">📥</span> INPUT Datasets (Need to be uploaded)
                </p>
                <div className="space-y-2">
                  {requiredDatasets.length === 0 ? (
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center">
                      <p className="text-sm font-semibold text-emerald-700">All inputs satisfied!</p>
                    </div>
                  ) : (
                    requiredDatasets.map((dsName: string) => {
                      const qual = qualifications[dsName];
                      return (
                        <div key={dsName} className="bg-white border-l-4 border-blue-500 rounded-lg p-3">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <p className="font-mono text-sm font-bold text-slate-800">{dsName}</p>
                              <p className="text-xs text-slate-600 mt-1">
                                {classifications[dsName]?.reason || 'Required for processing'}
                              </p>
                              {qual && (
                                <p className="text-xs text-slate-500 mt-2">
                                  <strong>Rows:</strong> {qual.metadata?.row_count || '?'} | <strong>Cols:</strong> {qual.metadata?.column_count || '?'}
                                </p>
                              )}
                            </div>
                            <span className="text-xs font-bold px-3 py-1 rounded bg-blue-100 text-blue-700 whitespace-nowrap ml-2">
                              INPUT
                            </span>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* GENERATED/OUTPUT DATASETS */}
              {lineage && Object.keys(lineage).length > 0 && (
                <div>
                  <p className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
                    <span className="text-lg">📤</span> OUTPUT Datasets (Generated by the tool)
                  </p>
                  <div className="space-y-2">
                    {lineage.generated_outputs && lineage.generated_outputs.length > 0 ? (
                      lineage.generated_outputs.map((dsName: string) => {
                        const c = classifications[dsName];
                        return (
                          <div key={dsName} className="bg-white border-l-4 border-emerald-500 rounded-lg p-3">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <p className="font-mono text-sm font-bold text-slate-800">{dsName}</p>
                                <p className="text-xs text-slate-600 mt-1">
                                  Generated by {c?.reason ? c.reason.split(' ')[0] : 'process'}
                                </p>
                              </div>
                              <span className="text-xs font-bold px-3 py-1 rounded bg-emerald-100 text-emerald-700 whitespace-nowrap ml-2">
                                OUTPUT
                              </span>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <p className="text-xs text-slate-500 italic">No output datasets generated</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ══════════════════════════════════════════════════════════════ */
        /* SECTION 3: ALL DATASETS                                        */
        /* ══════════════════════════════════════════════════════════════ */}
        <div className="border border-indigo-200 rounded-lg overflow-hidden bg-white">
          <button
            onClick={() => toggleSection('datasets')}
            className="w-full p-4 flex items-center justify-between hover:bg-indigo-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              {expandedSections.datasets ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <FileSearch className="w-4 h-4 text-indigo-600" />
              <span className="font-bold text-slate-800">Dataset Classification</span>
            </div>
            <span className="text-xs font-mono text-slate-600">{allDatasets.length} total</span>
          </button>

          {expandedSections.datasets && (
            <div className="p-4 border-t border-indigo-100 bg-slate-50 space-y-2">
              {allDatasets.map((dsName: string) => {
                const status = getDatasetStatus(dsName);
                const c = classifications[dsName];
                
                // Determine role based on classifications state or name prefix
                const isInput = c?.state === 'external_input' || dsName.toLowerCase().startsWith('raw');
                const isOutput = c?.state === 'generated' || dsName.toLowerCase().startsWith('sdtm') || dsName.toLowerCase().startsWith('adam');
                
                let roleText = c?.role || 'unknown';
                let labelText = status.label;
                let boxColorClass = "border-slate-200 bg-slate-50 text-slate-700";
                let badgeColorClass = "bg-slate-100 text-slate-600";
                
                if (isInput) {
                  const uploaded = isDatasetUploaded(dsName);
                  roleText = uploaded ? "dataset uploaded as input" : "dataset to be uploaded as input";
                  labelText = uploaded ? "Satisfied (Input)" : "Input Dataset";
                  boxColorClass = uploaded 
                    ? "border-emerald-200 bg-emerald-50 text-emerald-700" 
                    : "border-blue-200 bg-blue-50 text-blue-700";
                  badgeColorClass = uploaded
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-blue-100 text-blue-800";
                } else if (isOutput) {
                  roleText = "dataset to be generated by the tool as output";
                  labelText = "Output Dataset";
                  boxColorClass = "border-indigo-200 bg-indigo-50 text-indigo-700";
                  badgeColorClass = "bg-indigo-100 text-indigo-800";
                }

                return (
                  <div key={dsName} className={`border rounded-lg p-3 transition-all ${boxColorClass}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <p className="font-mono text-xs font-bold">{dsName}</p>
                        <p className="text-xs mt-1 opacity-80 capitalize">{roleText}</p>
                      </div>
                      <div className="flex items-center gap-2 ml-2">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${badgeColorClass}`}>{labelText}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
        
        {/* ══════════════════════════════════════════════════════════════ */}
        {/* SECTION 3.5: MISSING DATA & INTEGRITY                          */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {missingData && Object.keys(missingData).length > 0 && (
          <div className="border border-indigo-200 rounded-lg overflow-hidden bg-white">
            <button
              onClick={() => toggleSection('missing_data')}
              className="w-full p-4 flex items-center justify-between hover:bg-indigo-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                {expandedSections.missing_data ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <AlertCircle className="w-4 h-4 text-rose-500" />
                <span className="font-bold text-slate-800">Missing Data & Integrity Alerts</span>
              </div>
              <span className="text-xs font-mono text-slate-600">{Object.keys(missingData).length} audited</span>
            </button>

            {expandedSections.missing_data && (
              <div className="p-4 border-t border-indigo-100 bg-slate-50 space-y-4">
                {Object.entries(missingData).map(([dsName, data]: [string, any]) => {
                  const completeness = data.completeness_score ?? 100;
                  const missingVars = data.missing_variables || [];
                  const alerts = data.alerts || [];
                  
                  // Score color
                  const scoreColor = completeness >= 95 
                    ? "text-emerald-600 bg-emerald-50 border-emerald-200" 
                    : completeness >= 80 
                    ? "text-amber-600 bg-amber-50 border-amber-200" 
                    : "text-rose-600 bg-rose-50 border-rose-200";

                  return (
                    <div key={dsName} className="bg-white rounded-lg border border-slate-200 p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-bold text-slate-800 font-mono">{dsName}</p>
                        <div className={`text-xs font-bold border px-2.5 py-1 rounded-full ${scoreColor}`}>
                          Completeness: {completeness}%
                        </div>
                      </div>

                      {missingVars.length > 0 ? (
                        <div className="space-y-1">
                          <p className="text-xs font-bold text-rose-700">⚠️ Missing Variables Identified:</p>
                          <div className="flex flex-wrap gap-1">
                            {missingVars.map((v: string) => (
                              <span key={v} className="font-mono text-[10px] bg-rose-100 text-rose-800 px-2 py-0.5 rounded">
                                {v}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs text-emerald-700 flex items-center gap-1">
                          ✅ No missing variables detected
                        </p>
                      )}

                      {alerts.length > 0 && (
                        <div className="space-y-1 mt-2">
                          <p className="text-xs font-bold text-amber-700">Integrity Alerts:</p>
                          <ul className="list-disc list-inside text-xs text-slate-600 space-y-1 pl-1">
                            {alerts.map((alert: any, idx: number) => (
                              <li key={idx}>
                                {typeof alert === 'string' ? alert : (alert.detail || alert.message || 'Anomaly detected')}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */
        /* SECTION 4: LINEAGE & EXECUTION ORDER                           */
        /* ══════════════════════════════════════════════════════════════ */}
        {lineage && Object.keys(lineage).length > 0 && (
          <div className="border border-indigo-200 rounded-lg overflow-hidden bg-white">
            <button
              onClick={() => toggleSection('lineage')}
              className="w-full p-4 flex items-center justify-between hover:bg-indigo-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                {expandedSections.lineage ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <Zap className="w-4 h-4 text-yellow-600" />
                <span className="font-bold text-slate-800">Execution Order & Lineage</span>
              </div>
            </button>

            {expandedSections.lineage && (
              <div className="p-4 border-t border-indigo-100 bg-slate-50 space-y-2">
                {lineage.execution_order && (
                  <div>
                    <p className="text-xs font-bold text-slate-700 mb-2">Execution Sequence:</p>
                    <div className="space-y-1">
                      {lineage.execution_order.map((ds: string, i: number) => (
                        <div key={ds} className="flex items-center gap-2 text-xs">
                          <span className="font-mono bg-indigo-200 px-2 py-1 rounded text-indigo-700 font-bold">{i + 1}</span>
                          <span className="font-mono text-slate-600">{ds}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */
        /* SECTION 5: DATASET QUALIFICATIONS                              */
        /* ══════════════════════════════════════════════════════════════ */}
        {Object.keys(qualifications).length > 0 && (
          <div className="border border-indigo-200 rounded-lg overflow-hidden bg-white">
            <button
              onClick={() => toggleSection('qualifications')}
              className="w-full p-4 flex items-center justify-between hover:bg-indigo-50 transition-colors"
            >
              <div className="flex items-center gap-2">
                {expandedSections.qualifications ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                <Shield className="w-4 h-4 text-blue-600" />
                <span className="font-bold text-slate-800">Dataset Qualification Details</span>
              </div>
              <span className="text-xs font-mono text-slate-600">{Object.keys(qualifications).length} qualified</span>
            </button>

            {expandedSections.qualifications && (
              <div className="p-4 border-t border-indigo-100 bg-slate-50 space-y-3">
                {Object.entries(qualifications).map(([name, qual]: [string, any]) => (
                  <div key={name} className="bg-white rounded-lg border border-slate-200 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-bold text-slate-800">{name}</p>
                      <p className="text-lg font-bold text-indigo-600">{qual.compatibility_score?.overall || 0}%</p>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <span className="text-slate-600">Rows:</span> <span className="font-bold">{qual.metadata?.row_count || '?'}</span>
                      </div>
                      <div>
                        <span className="text-slate-600">Columns:</span> <span className="font-bold">{qual.metadata?.column_count || '?'}</span>
                      </div>
                      <div>
                        <span className="text-slate-600">Status:</span> <span className="font-bold">{qual.acceptance_status?.replace(/_/g, ' ')}</span>
                      </div>
                      <div>
                        <span className="text-slate-600">Type:</span> <span className="font-bold">{qual.dataset_type}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
