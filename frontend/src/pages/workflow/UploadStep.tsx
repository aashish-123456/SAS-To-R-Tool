import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { useMutation } from '@tanstack/react-query';
import { Upload, File, X, ArrowRight } from 'lucide-react';
import { projectsApi } from '@/services/api';

const UploadStep: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const sasSectionRef = useRef<HTMLDivElement | null>(null);
  const datasetSectionRef = useRef<HTMLDivElement | null>(null);
  const [sasFile, setSasFile] = useState<File | null>(null);
  const [sasPreview, setSasPreview] = useState<string>('');
  const [datasetFiles, setDatasetFiles] = useState<File[]>([]);
  const sasFileUrl = useMemo(() => (sasFile ? URL.createObjectURL(sasFile) : ''), [sasFile]);

  const uploadMutation = useMutation({
    mutationFn: ({ sasCode, datasets }: { sasCode: File; datasets?: File[] }) =>
      projectsApi.uploadFiles(projectId!, sasCode, datasets),
    onSuccess: () => {
      navigate(`/projects/${projectId}/translation`);
    },
  });

  const onDropSas = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const selectedFile = acceptedFiles[0];
      setSasFile(selectedFile);
      const content = await selectedFile.text();
      setSasPreview(content);
    }
  }, []);

  const onDropDatasets = useCallback((acceptedFiles: File[]) => {
    setDatasetFiles((prev) => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps: getSasRootProps, getInputProps: getSasInputProps, isDragActive: isSasDragActive } =
    useDropzone({
      onDrop: onDropSas,
      accept: { 'text/plain': ['.sas', '.txt'] },
      multiple: false,
    });

  const { getRootProps: getDatasetsRootProps, getInputProps: getDatasetsInputProps, isDragActive: isDatasetsDragActive } =
    useDropzone({
      onDrop: onDropDatasets,
      accept: { 'application/octet-stream': ['.sas7bdat', '.xpt'] },
      multiple: true,
    });

  const removeDataset = (index: number) => {
    setDatasetFiles((prev) => prev.filter((_, i) => i !== index));
  };

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const uploadType = params.get('uploadType');

    if (uploadType === 'dataset') {
      datasetSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (uploadType === 'sas') {
      sasSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [location.search]);

  const handleContinue = () => {
    if (sasFile) {
      uploadMutation.mutate({
        sasCode: sasFile,
        datasets: datasetFiles.length > 0 ? datasetFiles : undefined,
      });
    }
  };

  return (
    <div className="max-w-4xl">
      <div className="bg-white border border-gray-200 rounded-lg p-8">
        {/* SAS Code Upload */}
        <div className="mb-8" ref={sasSectionRef}>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">SAS Code</h2>
          <p className="text-sm text-gray-600 mb-4">Upload your SAS program (.sas or .txt file)</p>

          {!sasFile ? (
            <div
              {...getSasRootProps()}
              className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
                isSasDragActive
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getSasInputProps()} />
              <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-700 mb-2">
                {isSasDragActive ? 'Drop the file here' : 'Drag & drop your SAS file here'}
              </p>
              <p className="text-sm text-gray-500">or click to browse</p>
            </div>
          ) : (
            <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg">
              <File className="w-8 h-8 text-blue-600" />
              <div className="flex-1">
                <p className="font-medium text-gray-900">{sasFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(sasFile.size / 1024).toFixed(2)} KB
                </p>
                {sasFileUrl && (
                  <a
                    href={sasFileUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-blue-600 hover:text-blue-700 underline"
                  >
                    Open file in new tab
                  </a>
                )}
              </div>
              <button
                onClick={() => {
                  setSasFile(null);
                  setSasPreview('');
                }}
                className="p-2 text-gray-400 hover:text-red-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          )}
        </div>

        {/* Datasets Upload */}
        <div className="mb-8" ref={datasetSectionRef}>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            Datasets (Optional)
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Upload SAS datasets (.sas7bdat or .xpt files)
          </p>

          <div
            {...getDatasetsRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors mb-4 ${
              isDatasetsDragActive
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <input {...getDatasetsInputProps()} />
            <Upload className="w-10 h-10 mx-auto mb-3 text-gray-400" />
            <p className="text-gray-700 mb-1">
              {isDatasetsDragActive ? 'Drop the files here' : 'Drag & drop dataset files'}
            </p>
            <p className="text-sm text-gray-500">or click to browse</p>
          </div>

          {datasetFiles.length > 0 && (
            <div className="space-y-2">
              {datasetFiles.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                >
                  <File className="w-6 h-6 text-green-600" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024).toFixed(2)} KB
                    </p>
                  </div>
                  <button
                    onClick={() => removeDataset(index)}
                    className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Input Preview */}
        {sasFile && (
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Input Preview</h2>
            <p className="text-sm text-gray-600 mb-4">Preview uploaded inputs before continuing.</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-gray-200 rounded-lg p-4">
                <p className="text-sm font-medium text-gray-900 mb-2">SAS Input ({sasFile.name})</p>
                <div className="bg-gray-900 text-gray-100 rounded-lg p-3 h-56 overflow-auto">
                  <pre className="text-xs font-mono whitespace-pre-wrap">
                    <code>{sasPreview || '# Empty file'}</code>
                  </pre>
                </div>
              </div>
              <div className="border border-gray-200 rounded-lg p-4">
                <p className="text-sm font-medium text-gray-900 mb-2">Datasets Uploaded</p>
                {datasetFiles.length === 0 ? (
                  <p className="text-sm text-gray-500">No dataset files uploaded.</p>
                ) : (
                  <ul className="space-y-1 text-sm text-gray-700">
                    {datasetFiles.map((file, idx) => (
                      <li key={`${file.name}-${idx}`}>
                        <a
                          href={URL.createObjectURL(file)}
                          target="_blank"
                          rel="noreferrer"
                          className="text-blue-600 hover:text-blue-700 underline"
                        >
                          {file.name}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/projects')}
            className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleContinue}
            disabled={!sasFile || uploadMutation.isPending}
            className="flex-[2] flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {uploadMutation.isPending ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Uploading...
              </>
            ) : (
              <>
                Continue to Translation
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UploadStep;

