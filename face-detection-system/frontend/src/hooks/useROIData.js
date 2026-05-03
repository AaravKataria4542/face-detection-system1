import { useState, useEffect, useCallback } from 'react';

export function useROIData({ sessionId, apiBase, live = false }) {
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch_ = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/v1/roi/${sessionId}?limit=100`);
      if (res.status === 404) { setRecords([]); setTotal(0); return; }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRecords(data.records);
      setTotal(data.total);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [sessionId, apiBase]);

  useEffect(() => {
    fetch_();
    if (!live) return;
    const interval = setInterval(fetch_, 2000);
    return () => clearInterval(interval);
  }, [fetch_, live]);

  return { records, total, loading, error, refresh: fetch_ };
}
