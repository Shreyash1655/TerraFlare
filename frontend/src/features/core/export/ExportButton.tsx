
import { useState } from 'react';

interface ExportButtonProps {
  dataset: 'harmonized_daily' | 'monthly' | 'hotspots' | 'comparison';
  regionId?: string;
  startDate?: string;
  endDate?: string;
  className?: string;
}

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'
).replace(/\/$/, '');

export default function ExportButton({
  dataset,
  regionId = 'pwn',
  startDate = '2020-01-01',
  endDate = '2025-12-31',
  className = '',
}: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState('');

  const handleDownload = async () => {
    if (isExporting) return;

    setIsExporting(true);
    setError('');

    try {
      const params = new URLSearchParams({
        dataset,
        region_id: regionId,
        start_date: startDate,
        end_date: endDate,
      });

      const response = await fetch(
        `${API_BASE_URL}/export/csv?${params.toString()}`,
        {
          method: 'GET',
          headers: {
            Accept: 'text/csv',
          },
        }
      );

      if (!response.ok) {
        const message = await response.text();
        throw new Error(
          message || `Export failed with status ${response.status}`
        );
      }

      const contentType = response.headers.get('content-type') || '';

      if (!contentType.includes('text/csv') &&
          !contentType.includes('application/octet-stream')) {
        throw new Error('The backend did not return a CSV file.');
      }

      const blob = await response.blob();

      if (blob.size === 0) {
        throw new Error('The backend returned an empty CSV file.');
      }

      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');

      link.href = objectUrl;
      link.download =
        `terraflare_${dataset}_${regionId}_${startDate}_${endDate}.csv`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      console.error('Failed to export CSV:', err);

      setError(
        err instanceof Error
          ? err.message
          : 'Unable to export CSV. Please try again.'
      );
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="inline-flex flex-col gap-1">
      <button
        onClick={handleDownload}
        disabled={isExporting}
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[#f59e0b] hover:bg-[#ffb95f] text-[#0B0F19] font-label-mono text-xs font-bold transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
        type="button"
      >
        <span className="material-symbols-outlined text-sm">
          {isExporting ? 'hourglass_empty' : 'cloud_download'}
        </span>

        <span>
          {isExporting ? 'Exporting CSV...' : 'Export Canonical CSV'}
        </span>
      </button>

      {error && (
        <p className="text-xs text-red-400 max-w-xs" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
