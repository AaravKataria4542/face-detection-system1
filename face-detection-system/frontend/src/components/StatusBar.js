import React from 'react';
import styles from './StatusBar.module.css';

export default function StatusBar({ sessionId, status, lastDetection, roiTotal }) {
  const stats = [
    { label: 'SESSION', value: sessionId ? sessionId.slice(0, 8) + '…' : '—' },
    { label: 'STATUS', value: status.toUpperCase(), accent: status === 'streaming' },
    { label: 'ROI STORED', value: roiTotal ?? 0, accent: roiTotal > 0 },
    {
      label: 'LAST CONF',
      value: lastDetection?.face_detected
        ? `${(lastDetection.confidence * 100).toFixed(1)}%`
        : '—',
      accent: lastDetection?.face_detected,
    },
  ];

  return (
    <div className={styles.bar}>
      {stats.map(s => (
        <div key={s.label} className={styles.stat}>
          <span className={styles.label}>{s.label}</span>
          <span className={`${styles.value} ${s.accent ? styles.accent : ''}`}>{s.value}</span>
        </div>
      ))}
    </div>
  );
}
