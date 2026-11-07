
import { useEffect, useMemo, useState } from 'react';
import { getQuality, getProvenance } from '../../../api/advanced';
import type {
  QualityData,
  ProvenanceData,
} from '../../../api/types/advanced';

interface PipelineNode {
  id: number;
  label: string;
  name: string;
  icon: string;
  desc: string;
  details: string[];
}

const pipelineNodes: PipelineNode[] = [
  {
    id: 1,
    label: 'L-01',
    name: 'Data Ingestion',
    icon: 'cloud_sync',
    desc: 'Satellite observation data enters the processing workflow.',
    details: [
      'Input: MODIS and VIIRS observations',
      'Source: NASA FIRMS products',
      'Output: Raw observation records',
    ],
  },
  {
    id: 2,
    label: 'L-02',
    name: 'Cleaning & Normalization',
    icon: 'filter_alt',
    desc: 'Observation records are checked and prepared for analysis.',
    details: [
      'Coordinate and timestamp validation',
      'Quality filtering and duplicate handling',
      'Output: Cleaned observations',
    ],
  },
  {
    id: 3,
    label: 'L-03',
    name: 'Spatial Harmonization',
    icon: 'hexagon',
    desc: 'Satellite observations are represented on a common spatial grid.',
    details: [
      'H3 spatial indexing',
      'Cell and day aggregation',
      'Output: Harmonized spatial records',
    ],
  },
  {
    id: 4,
    label: 'L-04',
    name: 'Statistical Analysis',
    icon: 'tune',
    desc: 'Cross-sensor comparisons and statistical analysis are performed.',
    details: [
      'Sensor comparison',
      'Activity and uncertainty analysis',
      'Output: Analytical results',
    ],
  },
  {
    id: 5,
    label: 'L-05',
    name: 'Data Storage',
    icon: 'database',
    desc: 'Processed records are stored for analytical queries.',
    details: [
      'DuckDB analytical database',
      'Parquet-based data storage',
      'Output: Queryable datasets',
    ],
  },
  {
    id: 6,
    label: 'L-06',
    name: 'API & Analytics',
    icon: 'terminal',
    desc: 'Backend endpoints expose processed results to the frontend.',
    details: [
      'FastAPI REST endpoints',
      'Structured API responses',
      'Output: Frontend-ready information',
    ],
  },
];

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return 'N/A';
  }

  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function formatShare(value: number): string {
  if (!Number.isFinite(value)) return 'N/A';

  const percentage = value <= 1 ? value * 100 : value;

  return `${percentage.toFixed(1)}%`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) return 'N/A';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString();
}

function shortenHash(hash: string | null | undefined): string {
  if (!hash) return 'Not available';

  if (hash.length <= 20) return hash;

  return `${hash.slice(0, 10)}...${hash.slice(-8)}`;
}

export default function QualityPage() {
  const [selectedNodeId, setSelectedNodeId] = useState(3);

  const [quality, setQuality] = useState<QualityData | null>(null);
  const [provenance, setProvenance] = useState<ProvenanceData | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dataMode, setDataMode] = useState<'fixture' | 'real' | null>(null);
  const [isSynthetic, setIsSynthetic] = useState<boolean | null>(null);

  const [reloadKey, setReloadKey] = useState(0);

  const selectedNode =
    pipelineNodes.find((node) => node.id === selectedNodeId) ??
    pipelineNodes[2];

  useEffect(() => {
    let cancelled = false;

    async function loadQualityData() {
      try {
        setLoading(true);
        setError(null);

        const [qualityResponse, provenanceResponse] = await Promise.all([
          getQuality(),
          getProvenance(),
        ]);

        if (cancelled) return;

        setQuality(qualityResponse.data);
        setProvenance(provenanceResponse.data);

        setDataMode(qualityResponse.meta.data_mode);
        setIsSynthetic(qualityResponse.meta.is_synthetic);
      } catch (err) {
        if (cancelled) return;

        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load quality and provenance information.',
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadQualityData();

    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const confidenceTotal = useMemo(() => {
    return (
      quality?.confidence_distribution.reduce(
        (total, item) => total + item.count,
        0,
      ) ?? 0
    );
  }, [quality]);

  const sensorNames = useMemo(() => {
    return [
      ...new Set(
        quality?.confidence_distribution.map(
          (item) => item.sensor_family,
        ) ?? [],
      ),
    ];
  }, [quality]);

  return (
    <div className="flex flex-col w-full pb-16">

      {/* Header */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#7bd0ff] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                SYSTEM ARCHITECTURE &amp; LINEAGE
              </span>

              <span className="text-[#a08e7a] font-caption-mono text-xs">
                /
              </span>

              <span className="font-caption-mono text-xs text-[#ffc174]">
                NASA MODIS &amp; VIIRS DATA INTEGRITY
              </span>
            </div>

            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Sensor Quality, Confidence &amp; Architectural Provenance
            </h1>

            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] leading-relaxed">
              Examine sensor confidence, observation availability, uncertainty
              and data lineage across the TerraFlare processing workflow.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#7bd0ff]">
              {loading
                ? 'LOADING DATA'
                : error
                  ? 'API ERROR'
                  : isSynthetic
                    ? 'SYNTHETIC FIXTURE'
                    : 'REAL DATA'}
            </span>

            {dataMode && (
              <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#ffc174]">
                {dataMode.toUpperCase()} MODE
              </span>
            )}
          </div>
        </div>
      </section>

      {/* Main Container */}
      <div className="w-full px-6 py-6 space-y-6">

        {loading && (
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-10 text-center">
            <p className="font-caption-mono text-sm text-[#7bd0ff] animate-pulse">
              LOADING QUALITY AND PROVENANCE DATA...
            </p>
          </div>
        )}

        {error && !loading && (
          <div className="bg-[#1c1f2a] border border-[#ff938c]/40 rounded-lg p-6">
            <p className="font-caption-mono text-sm font-bold text-[#ff938c]">
              QUALITY API ERROR
            </p>

            <p className="text-sm text-[#d8c3ad] mt-2">{error}</p>

            <button
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
              className="mt-4 px-4 py-2 rounded bg-[#262a35] border border-[#7bd0ff] text-[#7bd0ff] text-xs font-bold"
            >
              RETRY REQUEST
            </button>
          </div>
        )}

        {/* Architecture overview */}
        <div className="w-full bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#262a35] mb-4">
            <div>
              <h2 className="font-title-md text-base font-bold text-[#dfe2f1] flex items-center gap-2">
                <span className="material-symbols-outlined text-[#ffc174] text-lg">
                  schema
                </span>
                End-to-End Processing Pipeline
              </h2>

              <span className="font-caption-mono text-xs text-[#a08e7a]">
                Select a layer to inspect its role in the processing workflow.
              </span>
            </div>

            <span className="font-caption-mono text-xs text-[#ffc174] font-semibold bg-[#0a0e18] px-3 py-1 rounded border border-[#262a35]">
              SELECTED: {selectedNode.label}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
            {pipelineNodes.map((node) => {
              const isSelected = selectedNodeId === node.id;

              return (
                <button
                  key={node.id}
                  type="button"
                  onClick={() => setSelectedNodeId(node.id)}
                  className={`text-left p-3.5 rounded border transition-all text-xs flex flex-col justify-between ${
                    isSelected
                      ? 'bg-[#262a35] border-[#ffc174] shadow-md ring-1 ring-[#ffc174]'
                      : 'bg-[#171b26] border-[#262a35] hover:bg-[#262a35]/60'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-caption-mono text-[10px] px-1.5 py-0.5 rounded bg-[#0a0e18] text-[#7bd0ff] font-bold">
                        {node.label}
                      </span>

                      <span className="material-symbols-outlined text-[#7bd0ff] text-base">
                        {node.icon}
                      </span>
                    </div>

                    <div className="font-title-sm font-bold text-[#dfe2f1] mb-1">
                      {node.name}
                    </div>

                    <p className="font-body-sm text-[11px] text-[#a08e7a] line-clamp-3">
                      {node.desc}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Selected node details */}
          <div className="mt-4 p-4 rounded bg-[#0a0e18] border border-[#262a35]">
            <h3 className="font-caption-mono text-xs text-[#ffc174] font-bold mb-3">
              {selectedNode.label} • {selectedNode.name}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {selectedNode.details.map((detail) => (
                <div
                  key={detail}
                  className="p-3 rounded bg-[#171b26] border border-[#262a35]"
                >
                  <p className="text-xs font-caption-mono text-[#dfe2f1]">
                    {detail}
                  </p>
                </div>
              ))}
            </div>

            <p className="text-[10px] text-[#a08e7a] font-caption-mono mt-3">
              ARCHITECTURE OVERVIEW — NOT LIVE PERFORMANCE TELEMETRY
            </p>
          </div>
        </div>

        {!loading && !error && quality && (
          <>
            {/* Sensor confidence and contribution */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              {/* Confidence distribution */}
              <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
                <div className="flex items-center justify-between mb-4 gap-3">
                  <div>
                    <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                      Confidence Class Distribution
                    </h3>

                    <span className="font-caption-mono text-xs text-[#a08e7a]">
                      Native confidence classes reported by sensor family
                    </span>
                  </div>

                  <span className="px-2 py-0.5 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-xs">
                    {formatNumber(confidenceTotal)} RECORDS
                  </span>
                </div>

                {quality.confidence_distribution.length === 0 ? (
                  <p className="text-xs text-[#a08e7a] py-8 text-center">
                    No confidence distribution data available.
                  </p>
                ) : (
                  <div className="space-y-5">
                    {sensorNames.map((sensor) => {
                      const sensorItems =
                        quality.confidence_distribution.filter(
                          (item) => item.sensor_family === sensor,
                        );

                      const sensorTotal = sensorItems.reduce(
                        (sum, item) => sum + item.count,
                        0,
                      );

                      return (
                        <div key={sensor}>
                          <div className="flex justify-between items-center mb-2">
                            <span className="text-[#ffc174] font-caption-mono text-xs font-bold">
                              {sensor}
                            </span>

                            <span className="text-[#a08e7a] font-caption-mono text-xs">
                              {formatNumber(sensorTotal)} observations
                            </span>
                          </div>

                          <div className="space-y-3">
                            {sensorItems.map((item) => {
                              const percentage =
                                sensorTotal > 0
                                  ? (item.count / sensorTotal) * 100
                                  : 0;

                              return (
                                <div key={`${sensor}-${item.native_class}`}>
                                  <div className="flex justify-between text-[#dfe2f1] mb-1 text-xs">
                                    <span>
                                      Native class: {item.native_class}
                                    </span>

                                    <span className="text-[#7bd0ff] font-bold">
                                      {percentage.toFixed(1)}% (
                                      {formatNumber(item.count)})
                                    </span>
                                  </div>

                                  <div className="w-full bg-[#0a0e18] h-2.5 rounded-full overflow-hidden border border-[#262a35]">
                                    <div
                                      className="bg-[#7bd0ff] h-full rounded-full"
                                      style={{ width: `${percentage}%` }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="mt-4 pt-3 border-t border-[#262a35] font-caption-mono text-[11px] text-[#a08e7a]">
                  Counts are based on the confidence records returned by the
                  backend. Native classes are not assumed to be directly
                  equivalent across sensors.
                </div>
              </div>

              {/* Sensor contribution */}
              <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
                <div className="mb-4">
                  <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                    Sensor Contribution
                  </h3>

                  <span className="font-caption-mono text-xs text-[#a08e7a]">
                    Reported sensor-family shares across analysis periods
                  </span>
                </div>

                {quality.sensor_contribution.length === 0 ? (
                  <p className="text-xs text-[#a08e7a] py-8 text-center">
                    No sensor contribution data available.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {quality.sensor_contribution.map((item, index) => (
                      <div
                        key={`${item.period}-${item.sensor_family}-${index}`}
                        className="p-3 rounded bg-[#171b26] border border-[#262a35]"
                      >
                        <div className="flex justify-between gap-3 mb-2">
                          <span className="font-caption-mono text-xs text-[#dfe2f1] font-bold">
                            {item.sensor_family}
                          </span>

                          <span className="font-caption-mono text-xs text-[#ffc174]">
                            {formatShare(item.share)}
                          </span>
                        </div>

                        <div className="w-full bg-[#0a0e18] h-2 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#f59e0b] rounded-full"
                            style={{
                              width: `${Math.max(
                                0,
                                Math.min(
                                  100,
                                  item.share <= 1
                                    ? item.share * 100
                                    : item.share,
                                ),
                              )}%`,
                            }}
                          />
                        </div>

                        <p className="text-[10px] font-caption-mono text-[#a08e7a] mt-2">
                          Analysis period: {item.period}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                <div className="mt-4 pt-3 border-t border-[#262a35] text-[11px] text-[#a08e7a] font-caption-mono">
                  Sensor contribution describes the reported composition of
                  observations, not an independent accuracy score.
                </div>
              </div>
            </div>

            {/* Availability and uncertainty */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

              {/* Availability gaps */}
              <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
                <div className="mb-4">
                  <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                    Observation Availability
                  </h3>

                  <span className="font-caption-mono text-xs text-[#a08e7a]">
                    Reported sensor coverage gaps
                  </span>
                </div>

                {quality.availability.length === 0 ? (
                  <p className="text-xs text-[#a08e7a] py-8 text-center">
                    No availability gaps reported by the backend.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-caption-mono text-xs">
                      <thead>
                        <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                          <th className="py-2.5 px-3">Sensor</th>
                          <th className="py-2.5 px-3">Gap Start</th>
                          <th className="py-2.5 px-3">Gap End</th>
                          <th className="py-2.5 px-3">Description</th>
                        </tr>
                      </thead>

                      <tbody className="divide-y divide-[#262a35]">
                        {quality.availability.map((item, index) => (
                          <tr
                            key={`${item.sensor_family}-${item.gap_start}-${index}`}
                            className="bg-[#171b26] text-[#dfe2f1]"
                          >
                            <td className="py-3 px-3 text-[#ffc174] font-bold">
                              {item.sensor_family}
                            </td>

                            <td className="py-3 px-3">
                              {formatDate(item.gap_start)}
                            </td>

                            <td className="py-3 px-3">
                              {formatDate(item.gap_end)}
                            </td>

                            <td className="py-3 px-3">
                              {item.label || 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Uncertainty */}
              <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
                <div className="mb-4">
                  <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                    Uncertainty Summary
                  </h3>

                  <span className="font-caption-mono text-xs text-[#a08e7a]">
                    Available uncertainty metadata
                  </span>
                </div>

                <div className="bg-[#171b26] border border-[#262a35] rounded-lg p-5">
                  <p className="font-caption-mono text-xs text-[#a08e7a]">
                    INTERVAL LEVEL
                  </p>

                  <p className="text-3xl font-bold font-mono text-[#7bd0ff] mt-2">
                    {quality.uncertainty_summary.interval_level !== null
                      ? formatShare(
                          quality.uncertainty_summary.interval_level,
                        )
                      : 'N/A'}
                  </p>

                  <p className="text-xs text-[#a08e7a] mt-3 leading-relaxed">
                    This value represents the interval-level metadata supplied
                    by the backend. It should not be interpreted as an
                    individual observation's probability of being correct.
                  </p>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Provenance */}
        {!loading && !error && provenance && (
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                  Verifiable Data Lineage
                </h3>

                <span className="font-caption-mono text-xs text-[#a08e7a]">
                  Ingestion records and source metadata returned by the
                  provenance API
                </span>
              </div>

              <span className="px-2 py-1 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-xs">
                {provenance.sources.length} SOURCE RECORDS
              </span>
            </div>

            {provenance.sources.length === 0 ? (
              <p className="text-xs text-[#a08e7a] py-8 text-center">
                No provenance records are currently available.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left font-caption-mono text-[11px]">
                  <thead>
                    <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                      <th className="py-2.5 px-3">Source ID</th>
                      <th className="py-2.5 px-3">Product Version</th>
                      <th className="py-2.5 px-3">File Name</th>
                      <th className="py-2.5 px-3">Rows In</th>
                      <th className="py-2.5 px-3">Ingested At</th>
                      <th className="py-2.5 px-3 text-right">SHA-256</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-[#262a35]">
                    {provenance.sources.map((source) => (
                      <tr
                        key={source.source_id}
                        className="bg-[#171b26] text-[#dfe2f1]"
                      >
                        <td className="py-3 px-3 text-[#ffc174] font-bold">
                          {source.source_id}
                        </td>

                        <td className="py-3 px-3">
                          {source.product_version}
                        </td>

                        <td className="py-3 px-3">
                          {source.file_name}
                        </td>

                        <td className="py-3 px-3">
                          {formatNumber(source.rows_in)}
                        </td>

                        <td className="py-3 px-3">
                          {formatDate(source.ingested_at)}
                        </td>

                        <td
                          className="py-3 px-3 text-right font-mono text-[#7bd0ff]"
                          title={source.sha256}
                        >
                          {shortenHash(source.sha256)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-[#262a35] flex flex-wrap justify-between gap-2 font-caption-mono text-[11px] text-[#a08e7a]">
              <span>
                Provenance records: {provenance.sources.length}
              </span>

              <span className="text-[#7bd0ff]">
                Source metadata from backend
              </span>
            </div>
          </div>
        )}

        {/* Scientific note */}
        {!loading && !error && (
          <div className="bg-[#171b26] border border-[#262a35] rounded-lg p-4">
            <div className="flex items-start gap-3">
              <span className="material-symbols-outlined text-[#7bd0ff]">
                verified_user
              </span>

              <div>
                <h3 className="font-caption-mono text-xs font-bold text-[#dfe2f1]">
                  DATA QUALITY &amp; INTERPRETATION
                </h3>

                <p className="text-xs text-[#a08e7a] mt-2 leading-relaxed">
                  Sensor confidence, observation availability, uncertainty
                  and provenance are separate dimensions of data quality.
                  A high native confidence class does not automatically
                  establish cross-sensor equivalence. Missing coverage must
                  not be interpreted as zero fire activity. Provenance
                  records describe the source metadata available to the
                  system.
                </p>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
