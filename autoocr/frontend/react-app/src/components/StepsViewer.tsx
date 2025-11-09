import React from 'react';
import { PageResult } from '../App';

interface Props {
  steps: PageResult[];
  pages?: string[];
}

export const StepsViewer: React.FC<Props> = ({ steps, pages }) => {
  return (
    <section style={{ marginTop:'1.5rem' }}>
      <h3>Per-Page Module Decisions</h3>
      {steps.map(page => (
        <div key={page.page_index} style={{ border:'1px solid #2a2f36', borderRadius:'6px', padding:'0.75rem', marginBottom:'1rem', background:'#191d22' }}>
          <strong>Page {page.page_index + 1}</strong>
          {pages && pages[page.page_index] && (
            <div style={{ marginTop:'0.5rem' }}>
              <img src={`data:image/png;base64,${pages[page.page_index]}`} alt={`page-${page.page_index}`} style={{ maxWidth:'240px', border:'1px solid #333', borderRadius:'4px' }} />
            </div>
          )}
          <table style={{ width:'100%', marginTop:'0.5rem', borderCollapse:'collapse', fontSize:'0.85rem' }}>
            <thead>
              <tr style={{ textAlign:'left', borderBottom:'1px solid #2a2f36' }}>
                <th>Module</th>
                <th>Detected</th>
                <th>Applied</th>
                <th>Detect ms</th>
                <th>Process ms</th>
              </tr>
            </thead>
            <tbody>
              {page.modules.map(m => (
                <tr key={m.module} style={{ borderBottom:'1px solid #2a2f36' }}>
                  <td>{m.module}</td>
                  <td style={{ color: m.detected ? '#4ade80':'#999' }}>{String(m.detected)}</td>
                  <td style={{ color: m.applied ? '#4ade80':'#999' }}>{String(m.applied)}</td>
                  <td>{m.timing_ms.detect}</td>
                  <td>{m.timing_ms.process}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </section>
  );
};
