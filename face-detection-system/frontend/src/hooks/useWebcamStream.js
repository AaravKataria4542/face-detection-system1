import { useRef, useState, useCallback, useEffect } from 'react';

export function useWebcamStream({ sessionId, wsBaseUrl, onDetection }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const frameIntervalRef = useRef(null);
  const streamRef = useRef(null);

  const [status, setStatus] = useState('idle'); // idle | connecting | streaming | error | stopped
  const [error, setError] = useState(null);
  const [fps, setFps] = useState(0);
  const frameCountRef = useRef(0);
  const fpsIntervalRef = useRef(null);

  const stop = useCallback(() => {
    clearInterval(frameIntervalRef.current);
    clearInterval(fpsIntervalRef.current);
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setStatus('stopped');
    setFps(0);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    setStatus('connecting');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
      });
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      // Open WebSocket ingest connection
      const wsUrl = `${wsBaseUrl}/api/v1/ingest/${sessionId}/ws`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus('streaming');
        frameCountRef.current = 0;

        // FPS counter
        fpsIntervalRef.current = setInterval(() => {
          setFps(frameCountRef.current);
          frameCountRef.current = 0;
        }, 1000);

        // Capture & send frames at ~15fps
        frameIntervalRef.current = setInterval(() => {
          if (!canvasRef.current || !videoRef.current) return;
          const ctx = canvasRef.current.getContext('2d');
          const { videoWidth: w, videoHeight: h } = videoRef.current;
          canvasRef.current.width = w;
          canvasRef.current.height = h;
          ctx.drawImage(videoRef.current, 0, 0, w, h);
          canvasRef.current.toBlob(blob => {
            if (blob && ws.readyState === WebSocket.OPEN) {
              blob.arrayBuffer().then(buf => ws.send(buf));
              frameCountRef.current++;
            }
          }, 'image/jpeg', 0.8);
        }, 66); // ~15fps
      };

      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (onDetection) onDetection(data);
        } catch (_) {}
      };

      ws.onerror = () => {
        setError('WebSocket connection failed');
        setStatus('error');
      };

      ws.onclose = () => {
        if (status !== 'stopped') setStatus('stopped');
      };

    } catch (err) {
      setError(err.message || 'Camera access denied');
      setStatus('error');
    }
  }, [sessionId, wsBaseUrl, onDetection, status]);

  useEffect(() => () => stop(), [stop]);

  return { videoRef, canvasRef, status, error, fps, start, stop };
}
