import React from 'react';
import styles from './ROITable.module.css';

export default function ROITable({ records, total, loading }) {
  if (loading && records.length === 0) {
    return (
      <div className={styles.empty}>
        <span className={styles.shimmer}>LOADING ROI DATA…</span>
      </div>
    );
  }

  if (records.length === 0) {
    return (
      <div className={styles.empty}>
        <span>NO RECORDS YET</span>
      </div>
    );
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.tableHeader}>
        <span className={styles.count}>{total} RECORDS</span>
      </div>
      <div className={styles.tableScroll}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>#</th>
              <th>FRAME</th>
              <th>X</th>
              <th>Y</th>
              <th>W</th>
              <th>H</th>
              <th>CONF</th>
              <th>TIME</th>
            </tr>
          </thead>
          <tbody>
            {[...records].reverse().slice(0, 50).map((r, i) => (
              <tr key={r.id} className={i === 0 ? styles.rowLatest : ''}>
                <td className={styles.muted}>{r.id}</td>
                <td>{r.frame_index}</td>
                <td>{r.bbox.x_px}</td>
                <td>{r.bbox.y_px}</td>
                <td>{r.bbox.width_px}</td>
                <td>{r.bbox.height_px}</td>
                <td className={styles.conf}>{(r.confidence * 100).toFixed(0)}%</td>
                <td className={styles.muted}>
                  {new Date(r.timestamp).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
