import React, { useState } from 'react';
import { UploadForm } from './components/UploadForm';
import { StepsViewer } from './components/StepsViewer';
import { PdfViewer } from './components/PdfViewer';

export interface ModuleStep {
  module: string;
  detected: boolean;
  applied: boolean;
  detect_meta: any;
  process_meta: any;
  timing_ms: { detect: number; process: number; total: number };
}

export interface PageResult {
  page_index: number;
  modules: ModuleStep[];
}

export interface ProcessResponse {
  filename: string;
  page_count: number;
  steps: PageResult[];
  pdf_base64?: string;
  pages_base64_png?: string[];
}

const App: React.FC = () => {
  const [data, setData] = useState<ProcessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div>
      <UploadForm onResult={setData} onLoading={setLoading} onError={setError} />
      {loading && <p style={{ color: '#999' }}>Processing...</p>}
      {error && <p style={{ color: '#ff6b6b' }}>{error}</p>}
      {data && (
        <>
          <h2>Result: {data.filename}</h2>
          <p>Pages: {data.page_count}</p>
          <PdfViewer pdfBase64={data.pdf_base64} />
          <StepsViewer steps={data.steps} pages={data.pages_base64_png} />
        </>
      )}
    </div>
  );
};

export default App;
