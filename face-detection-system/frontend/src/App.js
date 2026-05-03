import React, { useState, useCallback, useRef } from 'react';
import styles from './App.module.css';
import { useWebcamStream } from './hooks/useWebcamStream';
import { useROIData } from './hooks/useROIData';
import VideoPanel from './components/VideoPanel';
import ROITable from './components/ROITable';
import StatusBar from './components/StatusBar';

const API_BASE = process.env.REACT_APP_API_BASE || '';
const WS_BASE  = process.env.REACT_APP_WS_BASE
  || API_BASE.replace(/^http/, 'ws')
  || `ws://${window.location.host}`;

function generateSessionId() {
  return Date.now().toString(16) + Math.random().toString(16).slice(2, 8);
}

export default function App() {
  const [sessionId] = useState(() => generateSessionId());
  const [lastDetection, setLastDetection] = useState(null);

  const handleDetection = useCallback((data) => {
    setLastDetection(data);
  }, []);

  const { videoRef, canvasRef, status, error, fps, start, stop } =
    useWebcamStream({ sessionId, wsBaseUrl: WS_BASE, onDetection: handleDetection });

  const { records, total, loading } = useROIData({
    sessionId,
    apiBase: API_BASE,
    live: status === 'streaming',
  });

  const isStreaming = status === 'streaming';

  return (
    <div className={styles.app}>
      {/* Scanline effect */}
      <div className={styles.scanline} aria-hidden />

      {/* Header */}
      <header className={styles.header}>
        <div className={styles.logo}>
          <span className={styles.logoMark}>◈</span>
          <span className={styles.logoText}>FACETRACK</span>
          <span className={styles.logoBadge}>v1.0</span>
        </div>
        <p className={styles.tagline}>Real-Time Face Detection · ROI Streaming System</p>
      </header>

      {/* Status bar */}
      <div className={styles.statusWrapper}>
        <StatusBar
          sessionId={sessionId}
          status={status}
          lastDetection={lastDetection}
          roiTotal={total}
        />
      </div>

      {/* Main content */}
      <main className={styles.main}>
        {/* Left: video feed */}
        <section className={styles.videoSection}>
          <VideoPanel
            sessionId={sessionId}
            apiBase={API_BASE}
            status={status}
            fps={fps}
            lastDetection={lastDetection}
            videoRef={videoRef}
            canvasRef={canvasRef}
          />

          {/* Controls */}
          <div className={styles.controls}>
            {!isStreaming ? (
              <button
                className={`${styles.btn} ${styles.btnStart}`}
                onClick={start}
                disabled={status === 'connecting'}
              >
                {status === 'connecting' ? '⟳ CONNECTING…' : '▶ START STREAM'}
              </button>
            ) : (
              <button className={`${styles.btn} ${styles.btnStop}`} onClick={stop}>
                ■ STOP STREAM
              </button>
            )}
          </div>

          {error && (
            <div className={styles.errorBanner}>
              ⚠ {error}
            </div>
          )}

          {/* Live ROI bbox */}
          {lastDetection?.face_detected && (
            <div className={styles.bboxCard}>
              <p className={styles.bboxTitle}>CURRENT BOUNDING BOX</p>
              <div className={styles.bboxGrid}>
                {['x', 'y', 'w', 'h'].map(k => (
                  <div key={k} className={styles.bboxCell}>
                    <span className={styles.bboxLabel}>{k.toUpperCase()}</span>
                    <span className={styles.bboxVal}>{lastDetection.bbox?.[k] ?? '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Right: ROI data table */}
        <section className={styles.dataSection}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>ROI DATABASE</span>
            <span className={styles.sectionSub}>session · {sessionId.slice(0, 12)}</span>
          </div>
          <div className={styles.tableWrapper}>
            <ROITable records={records} total={total} loading={loading} />
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <span>MediaPipe · FastAPI · PostgreSQL · React</span>
        <span>No OpenCV used</span>
      </footer>
    </div>
  );
}
