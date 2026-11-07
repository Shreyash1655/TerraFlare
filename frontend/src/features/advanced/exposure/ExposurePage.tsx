
import { useEffect, useState } from 'react';
import { getExposure } from '../../../api/advanced';
import type { ExposureData, ExposureLayerResult } from '../../../api/types/advanced';

type BufferOption = 1 | 5 | 10;

interface LayerDisplay {
  name: string;
  category: string;
  unit: string;
  valueType: 'count' | 'sum';
}

const layerDisplay: Record<string, LayerDisplay> = {
  settlements_osm: {
    name: 'Human Settlements & Populated Places',
    category: 'Socioeconomic Infrastructure',
    unit: 'settlements',
    valueType: 'count',
  },
  population_ghsl: {
    name: 'Modelled Residential Population',
    category: 'Demographic Exposure',
    unit: 'estimated residents',
    valueType: 'sum',
  },
  transport_corridors: {
    name: 'Primary & Secondary Road Corridors',
    category: 'Lifeline Networks',
    unit: 'km / reported sum',
    valueType: 'sum',
  },
  protected_areas_wdpa: {
    name: 'Protected Areas & Conservation Reserves',
    category: 'Ecological Assets',
    unit: 'reported value',
    valueType: 'sum',
  },
};

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return 'N/A';
  }

  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function getLayerValue(layer: ExposureLayerResult): string {
  if (!layer.available) return 'Unavailable';

  const display = layerDisplay[layer.layer_id];

  if (!display) {
    return layer.count !== null
      ? formatNumber(layer.count)
      : formatNumber(layer.sum_value);
  }

  const value =
    display.valueType === 'count'
      ? layer.count
      : layer.sum_value;

  return formatNumber(value);
}

function getLayerUnit(layer: ExposureLayerResult): string {
  const display = layerDisplay[layer.layer_id];

  if (!layer.available) return 'Not available';

  if (!display) {
    return layer.count !== null ? 'records' : 'reported value';
  }

  if (
    display.valueType === 'count' &&
    layer.count === null
  ) {
    return 'Count not supplied';
  }

  if (
    display.valueType === 'sum' &&
    layer.sum_value === null
  ) {
    return 'Sum not supplied';
  }

  return display.unit;
}

function getLayerName(layer: ExposureLayerResult): string {
  return (
    layerDisplay[layer.layer_id]?.name ??
    layer.layer_id.replaceAll('_', ' ')
  );
}

function getLayerCategory(layer: ExposureLayerResult): string {
  return (
    layerDisplay[layer.layer_id]?.category ??
    'External Geographic Dataset'
  );
}

export default function ExposurePage() {
  const [selectedBuffer, setSelectedBuffer] =
    useState<BufferOption>(5);

  const [exposure, setExposure] = useState<ExposureData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dataMode, setDataMode] =
    useState<'fixture' | 'real' | null>(null);

  const [isSynthetic, setIsSynthetic] =
    useState<boolean | null>(null);

  const [reloadKey, setReloadKey] = useState(0);

  // Fetch exposure data whenever the selected buffer changes.
  useEffect(() => {
    let cancelled = false;

    async function loadExposure() {
      try {
        setLoading(true);
        setError(null);

        const response = await getExposure({
          buffer_km: selectedBuffer,
        });

        if (cancelled) return;

        setExposure(response.data);
        setDataMode(response.meta.data_mode);
        setIsSynthetic(response.meta.is_synthetic);
      } catch (err) {
        if (cancelled) return;

        setError(
          err instanceof Error
            ? err.message
            : 'Unable to load geographic exposure data.',
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadExposure();

    return () => {
      cancelled = true;
    };
  }, [selectedBuffer, reloadKey]);

  const layers = exposure?.layers ?? [];

  return (
    <div className="flex flex-col w-full pb-16">

      {/* Top Banner */}
      <section className="w-full px-6 py-6 bg-[#0a0e18] border-b border-[#1F2937]">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div className="space-y-1.5 max-w-4xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 rounded bg-[#1c1f2a] text-[#ffc174] font-caption-mono text-[10px] uppercase tracking-wider font-semibold">
                TIER C INTEL • SUBSYSTEM 08
              </span>

              <span className="text-[#a08e7a] font-caption-mono text-xs">
                /
              </span>

              <span className="font-caption-mono text-xs text-[#7bd0ff]">
                MULTI-CRITERIA BUFFER GEOPROCESSING
              </span>
            </div>

            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Fire Impact &amp; Geographic Exposure Intelligence
            </h1>

            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] max-w-3xl leading-relaxed">
              Summarizes mapped infrastructure, population datasets and
              conservation areas located within configurable proximity
              buffers of observed satellite hotspot activity.
            </p>
          </div>

          {/* Buffer Control */}
          <div className="flex flex-wrap items-center bg-[#171b26] p-1 rounded-lg border border-[#262a35]">
            <span className="font-caption-mono text-[10px] text-[#a08e7a] px-2 uppercase">
              Buffer Radius:
            </span>

            {([1, 5, 10] as const).map((buffer) => (
              <button
                key={buffer}
                type="button"
                onClick={() => setSelectedBuffer(buffer)}
                disabled={loading}
                className={`px-3 py-1.5 rounded font-label-mono text-xs font-semibold transition-all disabled:opacity-50 ${
                  selectedBuffer === buffer
                    ? 'bg-[#f59e0b] text-[#0B0F19]'
                    : 'text-[#d8c3ad] hover:text-[#dfe2f1]'
                }`}
              >
                {buffer} km
              </button>
            ))}
          </div>
        </div>

        {/* Data Mode */}
        <div className="mt-4 flex flex-wrap gap-2">
          {dataMode && (
            <span className="px-2.5 py-1 rounded bg-[#171b26] border border-[#262a35] text-[#7bd0ff] font-caption-mono text-[10px]">
              {isSynthetic ? 'SYNTHETIC FIXTURE' : 'REAL DATA'}
            </span>
          )}

          {dataMode && (
            <span className="px-2.5 py-1 rounded bg-[#171b26] border border-[#262a35] text-[#ffc174] font-caption-mono text-[10px]">
              {dataMode.toUpperCase()} MODE
            </span>
          )}
        </div>

        {/* Scientific Limitation */}
        <div className="mt-4 p-2.5 rounded bg-[#171b26] border border-[#262a35] text-xs font-caption-mono text-[#a08e7a] flex items-start gap-2">
          <span className="material-symbols-outlined text-[#ffc174] text-base">
            warning
          </span>

          <span>
            <strong className="text-[#dfe2f1]">
              SCIENTIFIC CONSTRAINTS:
            </strong>{' '}
            Proximity is not confirmed damage, loss or forecast casualty
            risk. It indicates that a mapped asset lies within a geographic
            buffer around observed satellite activity. Missing layers must
            not be interpreted as zero exposure.
          </span>
        </div>
      </section>

      {/* Main Container */}
      <div className="w-full px-6 py-6 space-y-6">

        {/* Loading */}
        {loading && (
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-10 text-center">
            <p className="font-caption-mono text-sm text-[#7bd0ff] animate-pulse">
              CALCULATING GEOGRAPHIC EXPOSURE...
            </p>

            <p className="font-caption-mono text-xs text-[#a08e7a] mt-2">
              Requested buffer: {selectedBuffer} km
            </p>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="bg-[#1c1f2a] border border-[#ff938c]/40 rounded-lg p-6">
            <p className="font-caption-mono text-sm font-bold text-[#ff938c]">
              EXPOSURE API ERROR
            </p>

            <p className="text-sm text-[#d8c3ad] mt-2">
              {error}
            </p>

            <button
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
              className="mt-4 px-4 py-2 rounded bg-[#262a35] border border-[#7bd0ff] text-[#7bd0ff] text-xs font-bold"
            >
              RETRY REQUEST
            </button>
          </div>
        )}

        {/* Results */}
        {!loading && !error && exposure && (
          <>
            {/* Exposure Summary Cards */}
            <div>
              <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
                <h2 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                  Geographic Exposure Summary
                </h2>

                <span className="font-caption-mono text-xs text-[#7bd0ff]">
                  {exposure.buffer_km} KM BUFFER
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {layers.map((layer) => (
                  <div
                    key={layer.layer_id}
                    className="p-4 rounded bg-[#1c1f2a] border border-[#262a35] shadow-md flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-caption-mono text-[9px] text-[#a08e7a] uppercase truncate">
                          {getLayerCategory(layer)}
                        </span>

                        <span
                          className={`w-2 h-2 rounded-full ${
                            layer.available
                              ? 'bg-[#10B981]'
                              : 'bg-[#ff938c]'
                          }`}
                        />
                      </div>

                      <h4 className="font-title-sm text-sm font-bold text-[#dfe2f1] mb-2">
                        {getLayerName(layer)}
                      </h4>

                      <div className="my-2">
                        <span className="font-mono text-2xl font-bold text-[#ffc174]">
                          {getLayerValue(layer)}
                        </span>

                        <span className="font-caption-mono text-xs text-[#a08e7a] ml-1.5">
                          {getLayerUnit(layer)}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-[#262a35] flex flex-wrap justify-between gap-2 font-caption-mono text-[10px] text-[#a08e7a]">
                      <span>
                        {layer.available ? 'AVAILABLE' : 'UNAVAILABLE'}
                      </span>

                      <span className="text-[#7bd0ff]">
                        {layer.version || 'Version N/A'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {layers.length === 0 && (
                <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-8 text-center text-[#a08e7a] font-caption-mono text-xs">
                  No exposure layers were returned for this buffer.
                </div>
              )}
            </div>

            {/* Provenance Table */}
            <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
              <div className="flex flex-wrap justify-between items-center gap-2 mb-3">
                <div>
                  <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">
                    Asset Layers &amp; Provenance Specifications
                  </h3>

                  <span className="font-caption-mono text-xs text-[#a08e7a]">
                    Dataset sources and values returned by the backend
                  </span>
                </div>

                <span className="px-2 py-1 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-xs">
                  {layers.length} LAYERS
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left font-caption-mono text-xs">
                  <thead>
                    <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                      <th className="py-2.5 px-3">Asset Layer</th>
                      <th className="py-2.5 px-3">Data Provider</th>
                      <th className="py-2.5 px-3">Version</th>
                      <th className="py-2.5 px-3 text-right">Count</th>
                      <th className="py-2.5 px-3 text-right">Sum Value</th>
                      <th className="py-2.5 px-3 text-center">Status</th>
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-[#262a35]">
                    {layers.map((layer) => (
                      <tr
                        key={layer.layer_id}
                        className="bg-[#171b26] hover:bg-[#262a35]/60 transition-colors"
                      >
                        <td className="py-3 px-3 font-bold text-[#dfe2f1]">
                          {getLayerName(layer)}
                        </td>

                        <td className="py-3 px-3 text-[#d8c3ad]">
                          {layer.source || 'N/A'}
                        </td>

                        <td className="py-3 px-3 font-mono text-[#7bd0ff]">
                          {layer.version || 'N/A'}
                        </td>

                        <td className="py-3 px-3 text-right font-mono">
                          {formatNumber(layer.count)}
                        </td>

                        <td className="py-3 px-3 text-right font-mono text-[#ffc174]">
                          {formatNumber(layer.sum_value)}
                        </td>

                        <td className="py-3 px-3 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              layer.available
                                ? 'bg-[#10B981]/20 text-[#10B981]'
                                : 'bg-[#ff938c]/20 text-[#ff938c]'
                            }`}
                          >
                            {layer.available ? 'AVAILABLE' : 'UNAVAILABLE'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-4 pt-3 border-t border-[#262a35] font-caption-mono text-[11px] text-[#a08e7a]">
                Selected buffer: {exposure.buffer_km} km
              </div>
            </div>

            {/* Backend Note */}
            {exposure.note && (
              <div className="bg-[#171b26] border border-[#262a35] rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-[#7bd0ff]">
                    info
                  </span>

                  <div>
                    <h3 className="font-caption-mono text-xs font-bold text-[#dfe2f1]">
                      EXPOSURE INTERPRETATION
                    </h3>

                    <p className="text-xs text-[#a08e7a] mt-2 leading-relaxed">
                      {exposure.note}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
