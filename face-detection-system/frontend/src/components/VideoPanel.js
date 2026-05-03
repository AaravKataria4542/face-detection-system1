import React, { useState, useEffect, useRef } from 'react';
import styles from './VideoPanel.module.css';

export default function VideoPanel({ sessionId, apiBase, status, fps, lastDetection, videoRef, canvasRef }) {
  const imgRef = useRef(null);
  const [streamReady, setStreamReady] = useState(false);

  // Poll the MJPEG stream from backend
  useEffect(() => {
    if (status !== 'streaming') { setStreamReady(false); return; }
    const mjpegUrl = `${apiBase}/api/v1/stream/${sessionId}/mjpeg`;
    // Small delay to let first frame land
    const t = setTimeout(() => {
      if (imgRef.current) {
        imgRef.current.src = mjpegUrl + '?t=' + Date.now();
        setStreamReady(true);
      }
    }, 800);
    return () => clearTimeout(t);
  }, [status, sessionId, apiBase]);

  const isActive = status === 'streaming';
  const hasDetection = lastDetection?.face_detected;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <span className={styles.title}>LIVE FEED</span>
        <div className={styles.indicators}>
          <span className={`${styles.dot} ${isActive ? styles.dotGreen : styles.dotGray}`} />
          <span className={styles.label}>{isActive ? 'ACTIVE' : status.toUpperCase()}</span>
          {isActive && <span className={styles.fps}>{fps} FPS</span>}
        </div>
      </div>

      <div className={`${styles.viewfinder} ${isActive && hasDetection ? styles.viewfinderDetected : ''}`}>
        {/* Hidden video element for webcam capture */}
        <video ref={videoRef} className={styles.hiddenVideo} muted playsInline />
        {/* Hidden canvas for frame capture */}
        <canvas ref={canvasRef} className={styles.hiddenCanvas} />

        {/* Annotated MJPEG stream from backend */}
        {isActive && (
          <img
            ref={imgRef}
            className={`${styles.stream} ${streamReady ? styles.streamVisible : ''}`}
            alt="Annotated face detection stream"
          />
        )}

        {/* Idle overlay */}
        {!isActive && (
          <div className={styles.idleOverlay}>
            <div className={styles.crosshair}>
              <div className={styles.crosshairH} />
              <div className={styles.crosshairV} />
              <div className={styles.crosshairCenter} />
            </div>
            <p className={styles.idleText}>
              {status === 'error' ? '⚠ CAMERA ERROR' : 'AWAITING INPUT'}
            </p>
          </div>
        )}

        {/* Detection badge */}
        {isActive && (
          <div className={`${styles.badge} ${hasDetection ? styles.badgeDetected : styles.badgeClear}`}>
            {hasDetection
              ? `◉ FACE · ${(lastDetection.confidence * 100).toFixed(0)}%`
              : '○ NO FACE'}
          </div>
        )}

        {/* Corner brackets */}
        <div className={`${styles.corner} ${styles.tl}`} />
        <div className={`${styles.corner} ${styles.tr}`} />
        <div className={`${styles.corner} ${styles.bl}`} />
        <div className={`${styles.corner} ${styles.br}`} />
      </div>
    </div>
  );
}
