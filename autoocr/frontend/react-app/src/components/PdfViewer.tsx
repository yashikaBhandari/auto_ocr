import React from 'react';

interface Props { pdfBase64?: string; }

export const PdfViewer: React.FC<Props> = ({ pdfBase64 }) => {
  if (!pdfBase64) return null;
  const blob = new Blob([Uint8Array.from(atob(pdfBase64), c => c.charCodeAt(0))], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  return (
    <div style={{ margin: '1rem 0' }}>
      <a href={url} download="processed.pdf" style={{ background:'#2563eb', color:'#fff', padding:'0.5rem 0.9rem', borderRadius:'4px', textDecoration:'none' }}>Download Processed PDF</a>
      <iframe src={url} style={{ width:'100%', height:'480px', marginTop:'0.75rem', border:'1px solid #2a2f36', borderRadius:'4px' }} title="Processed PDF" />
    </div>
  );
};
