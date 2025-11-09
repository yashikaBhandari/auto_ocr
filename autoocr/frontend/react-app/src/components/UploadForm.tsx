import React, { useState } from 'react';
import { ProcessResponse } from '../App';

interface Props {
  onResult: (r: ProcessResponse) => void;
  onLoading: (b: boolean) => void;
  onError: (e: string | null) => void;
}

const API_BASE = import.meta.env.VITE_API_BASE || '';

export const UploadForm: React.FC<Props> = ({ onResult, onLoading, onError }) => {
  const [modules, setModules] = useState<string>('');
  const [includePages, setIncludePages] = useState<boolean>(false);
  const [file, setFile] = useState<File | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) { onError('Select a file'); return; }
    onError(null);
    onLoading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const query = new URLSearchParams();
      query.set('return_format', 'json');
      if (includePages) query.set('return_pages', 'true');
      if (modules.trim()) query.set('modules_enabled', modules.trim());
      const resp = await fetch(`${API_BASE}/process?${query.toString()}`, { method: 'POST', body: form });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: ProcessResponse = await resp.json();
      onResult(data);
    } catch (err: any) {
      onError(err.message);
    } finally {
      onLoading(false);
    }
  };

  return (
    <form onSubmit={submit} style={{ display:'grid', gap:'0.75rem', maxWidth:'640px', background:'#1b1f24', padding:'1rem', borderRadius:'8px', border:'1px solid #2a2f36' }}>
      <label style={{ display:'flex', flexDirection:'column', gap:'0.25rem' }}>
        <span>PDF or Image:</span>
        <input type="file" accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff" onChange={e=> setFile(e.target.files?.[0]||null)} />
      </label>
      <label style={{ display:'flex', flexDirection:'column', gap:'0.25rem' }}>
        <span>Enabled modules (comma-separated, optional):</span>
        <input value={modules} onChange={e=> setModules(e.target.value)} placeholder="edge_mask,orientation,deskew" />
      </label>
      <label style={{ display:'flex', alignItems:'center', gap:'0.5rem' }}>
        <input type="checkbox" checked={includePages} onChange={e=> setIncludePages(e.target.checked)} /> Include processed page PNGs
      </label>
      <button type="submit" style={{ background:'#3478f6', color:'#fff', padding:'0.6rem 1rem', border:'none', borderRadius:'4px', cursor:'pointer' }}>Process</button>
    </form>
  );
};
