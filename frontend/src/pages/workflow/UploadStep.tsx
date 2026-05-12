import React, { useCallback, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { ArrowRight, Upload, File, X } from 'lucide-react';

const REQUIRED_SAS_HINTS = [
  /\bdata\s+\w+/i,
  /\bproc\s+\w+/i,
  /\brun\s*;/i,
  /\bset\s+\w+/i,
];

const isLikelySasCode = (text: string) => {
  const normalized = text.replace(/\r/g, '\n');
  const hitCount = REQUIRED_SAS_HINTS.filter((rx) => rx.test(normalized)).length;
  return hitCount >= 2;
};

const hasAllowedDatasetExt = (name: string) => /\.(sas7bdat|xpt)$/i.test(name);

const UploadStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const [sasFile, setSasFile] = useState<File | null>(null);
  const [datasetFiles, setDatasetFiles] = useState<File[]>([]);
  const [sasError, setSasError] = useState('');
  const [datasetError, setDatasetError] = useState('');
  const [datasetEnabled, setDatasetEnabled] = useState(false);
  const sasFileUrl = sasFile ? URL.createObjectURL(sasFile) : '';

  const onDropSas = useCallback(async (acceptedFiles: File[]) => {
    if (!acceptedFiles.length) return;
    const candidate = acceptedFiles[0];
    const isAllowedFile = /\.(sas|txt)$/i.test(candidate.name);
    if (!isAllowedFile) {
      setSasError('Upload only .sas or .txt files for SAS code.');
      setSasFile(null);
      return;
    }
    const text = await candidate.text();
    if (!isLikelySasCode(text)) {
      setSasError('The uploaded file does not look like valid SAS code. Please upload a correct SAS script.');
      setSasFile(null);
      alert('Please upload a correct SAS code file (.sas or .txt).');
      return;
    }
    setSasError('');
    setSasFile(candidate);
  }, []);

  const onDropDatasets = useCallback((acceptedFiles: File[]) => {
    const invalid = acceptedFiles.find((f) => !hasAllowedDatasetExt(f.name) || f.size === 0);
    if (invalid) {
      setDatasetError('One or more datasets are invalid/corrupted. Upload only non-empty .sas7bdat or .xpt files.');
      return;
    }
    setDatasetError('');
    setDatasetFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps: getSasRootProps, getInputProps: getSasInputProps } = useDropzone({
    onDrop: onDropSas,
    accept: { 'text/plain': ['.sas', '.txt'] },
    multiple: false,
  });

  const { getRootProps: getDatasetRootProps, getInputProps: getDatasetInputProps } = useDropzone({
    onDrop: onDropDatasets,
    accept: { 'application/octet-stream': ['.sas7bdat', '.xpt'] },
    multiple: true,
    disabled: !datasetEnabled,
  });

  const canContinue = !!sasFile && !sasError && (!datasetEnabled || !datasetError);

  return (
    <div className="max-w-4xl">
      <div className="bg-white border border-gray-200 rounded-lg p-8 space-y-8">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Upload SAS Input</h2>
          <p className="text-sm text-gray-600">Step 1 of 2: upload and validate files.</p>
        </div>

        <div>
          <p className="text-sm font-medium text-gray-900 mb-2">SAS Code File (.sas or .txt only)</p>
          {!sasFile && (
            <div {...getSasRootProps()} className="border-2 border-dashed border-gray-300 hover:border-gray-400 rounded-lg p-8 text-center cursor-pointer">
              <input {...getSasInputProps()} />
              <Upload className="w-9 h-9 mx-auto mb-2 text-gray-400" />
              <p className="text-sm text-gray-700">Click or drag SAS file</p>
            </div>
          )}
          {sasFile && (
            <div className="mt-4 p-5 bg-gray-50 rounded-lg flex items-start gap-3">
              <File className="w-9 h-9 text-blue-600 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-2xl font-semibold text-gray-900 truncate">{sasFile.name}</p>
                <p className="text-sm text-gray-500">{(sasFile.size / 1024).toFixed(2)} KB</p>
                {sasFileUrl && (
                  <a
                    href={sasFileUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-blue-600 hover:text-blue-700 underline"
                  >
                    Open file in new tab
                  </a>
                )}
                <p className="mt-2 text-sm text-green-700">Validated: {sasFile.name}</p>
              </div>
              <button
                onClick={() => {
                  setSasFile(null);
                  setSasError('');
                }}
                className="p-1 text-gray-400 hover:text-red-600 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
          )}
          {sasError && (
            <p className="mt-2 text-sm text-red-600">
              {sasError} Please upload a correct SAS code file to continue.
            </p>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-900">Optional Dataset Upload</p>
            <button
              type="button"
              onClick={() => setDatasetEnabled((prev) => !prev)}
              className={`w-12 h-7 rounded-full p-1 transition-colors ${datasetEnabled ? 'bg-blue-600' : 'bg-gray-300'}`}
            >
              <span className={`block w-5 h-5 rounded-full bg-white transition-transform ${datasetEnabled ? 'translate-x-5' : ''}`} />
            </button>
          </div>
          {datasetEnabled && (
            <>
              <div {...getDatasetRootProps()} className="border-2 border-dashed border-gray-300 hover:border-gray-400 rounded-lg p-8 text-center cursor-pointer">
                <input {...getDatasetInputProps()} />
                <Upload className="w-9 h-9 mx-auto mb-2 text-gray-400" />
                <p className="text-sm text-gray-700">Upload .sas7bdat or .xpt datasets</p>
              </div>
              <div className="mt-3 space-y-2">
                {datasetFiles.map((f, i) => (
                  <div key={`${f.name}-${i}`} className="flex items-center gap-2 bg-gray-50 rounded p-2">
                    <File className="w-4 h-4 text-green-600" />
                    <span className="text-sm flex-1">{f.name}</span>
                    <button onClick={() => setDatasetFiles((prev) => prev.filter((_, idx) => idx !== i))}>
                      <X className="w-4 h-4 text-gray-500" />
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
          {datasetError && <p className="mt-2 text-sm text-red-600">{datasetError}</p>}
        </div>

        <button
          onClick={() => navigate(`/projects/${projectId}/preview-input`, { state: { sasFile, datasetFiles, datasetEnabled } })}
          disabled={!canContinue}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg disabled:opacity-50"
        >
          Continue to Input Preview
          <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default UploadStep;
