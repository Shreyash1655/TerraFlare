import { useState } from 'react';

interface PipelineNode {
  id: number;
  label: string;
  name: string;
  icon: string;
  metricLabel: string;
  metricValue: string;
  desc: string;
  techDetails: {
    runtime: string;
    throughput: string;
    rejectionRate: string;
    memoryFootprint: string;
    validationStatus: string;
  };
}

const pipelineNodes: PipelineNode[] = [
  {
    id: 1,
    label: 'L-01',
    name: 'Ingestion Adapters',
    icon: 'cloud_sync',
    metricLabel: 'THROUGHPUT',
    metricValue: '32 MB/s',
    desc: 'FIRMS NRT CSVs, S3 Polling, REST API hooks with SHA-256 payload pinning.',
    techDetails: {
      runtime: 'Python 3.11 BaseAdapter Worker',
      throughput: '32 MB/s (Compressed Gzip Stream)',
      rejectionRate: '0.00% (Raw Hash Validated)',
      memoryFootprint: '64 MB Streaming Buffer',
      validationStatus: 'SHA-256 Checksum Verified',
    },
  },
  {
    id: 2,
    label: 'L-02',
    name: 'Clean & Normalize',
    icon: 'filter_alt',
    metricLabel: 'QC REJECTION',
    metricValue: '0.04% dropped',
    desc: 'Boundary clip [-180, 180], UTC epoch parsing, QA masking, flag deduplication.',
    techDetails: {
      runtime: 'Fast NumPy Vectorized Bounds Check',
      throughput: '1.2M rows/sec',
      rejectionRate: '0.04% (Out-of-range Lat/Lon)',
      memoryFootprint: '128 MB In-Memory Chunk',
      validationStatus: '100% Coordinate Compliance',
    },
  },
  {
    id: 3,
    label: 'L-03',
    name: 'Harmonization Mesh',
    icon: 'hexagon',
    metricLabel: 'APERTURE',
    metricValue: 'H3 Res 7',
    desc: 'Uber H3 Resolution 7 projection, Cell-Day spatial-temporal discretization.',
    techDetails: {
      runtime: 'H3 C-Bindings + Spatial Geometry',
      throughput: '450k cells/sec',
      rejectionRate: '0.00% (Global Coverage)',
      memoryFootprint: '94 MB Spatial Index',
      validationStatus: 'WGS84 Uniform Hex Partition',
    },
  },
  {
    id: 4,
    label: 'L-04',
    name: 'Statistical Engine',
    icon: 'tune',
    metricLabel: 'RESIDUAL R²',
    metricValue: '0.941',
    desc: 'M0-M4 regression kernels, cross-sensor FRP scaling, Holdout validation.',
    techDetails: {
      runtime: 'SciPy / Statsmodels Estimator',
      throughput: '18ms fit latency',
      rejectionRate: '0.00% (Converged)',
      memoryFootprint: '42 MB Model Weights',
      validationStatus: 'Leave-One-Year-Out Passed',
    },
  },
  {
    id: 5,
    label: 'L-05',
    name: 'Lake & In-Memory',
    icon: 'database',
    metricLabel: 'QUERY LATENCY',
    metricValue: '14.2 ms',
    desc: 'DuckDB columnar store, partitioned Z-ordered Parquet files on SSD.',
    techDetails: {
      runtime: 'DuckDB v1.1 Columnar Engine',
      throughput: '4.8M rows queried in 14.2ms',
      rejectionRate: '0.00%',
      memoryFootprint: '180 MB In-Memory Cache',
      validationStatus: 'Parquet Snappy Compressed',
    },
  },
  {
    id: 6,
    label: 'L-06',
    name: 'FastAPI v1 Engine',
    icon: 'terminal',
    metricLabel: 'OPENAPI',
    metricValue: '/v1/openapi',
    desc: 'High-throughput REST API, Pydantic type validation, GeoJSON stream serialization.',
    techDetails: {
      runtime: 'FastAPI + Uvicorn ASGI Server',
      throughput: '2,400 req/sec',
      rejectionRate: '0.00% (Strict Envelope)',
      memoryFootprint: '38 MB Service Worker',
      validationStatus: 'Swagger UI Active at /docs',
    },
  },
];

export default function QualityPage() {
  const [selectedNodeId, setSelectedNodeId] = useState<number>(3);
  const selectedNode = pipelineNodes.find((n) => n.id === selectedNodeId) || pipelineNodes[2];

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
              <span className="text-[#a08e7a] font-caption-mono text-xs">/</span>
              <span className="font-caption-mono text-xs text-[#ffc174]">NASA MODIS &amp; VIIRS DATA INTEGRITY</span>
            </div>
            <h1 className="font-headline-lg text-2xl lg:text-3xl font-bold text-[#dfe2f1] tracking-tight">
              Sensor Quality, Confidence &amp; Architectural Provenance
            </h1>
            <p className="font-body-md text-xs sm:text-sm text-[#d8c3ad] leading-relaxed">
              Trace active fire observations from raw NASA FIRMS payloads through cleaning, spatial discretization, statistical calibration, and DuckDB analytics.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-3 py-1.5 rounded bg-[#171b26] border border-[#262a35] font-caption-mono text-xs text-[#7bd0ff] flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse"></span>
              All 6 Pipeline Layers Operational
            </span>
          </div>
        </div>
      </section>

      {/* Main Container */}
      <div className="w-full px-6 py-6 space-y-6">
        {/* 6-Layer Interactive Pipeline Visualizer */}
        <div className="w-full bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md">
          <div className="flex items-center justify-between pb-3 border-b border-[#262a35] mb-4">
            <div>
              <h2 className="font-title-md text-base font-bold text-[#dfe2f1] flex items-center gap-2">
                <span className="material-symbols-outlined text-[#ffc174] text-lg">schema</span>
                End-to-End Modular Monolith Pipeline
              </h2>
              <span className="font-caption-mono text-xs text-[#a08e7a]">
                Click any layer to inspect runtime throughput, memory footprint, and quality controls
              </span>
            </div>
            <span className="font-caption-mono text-xs text-[#ffc174] font-semibold bg-[#0a0e18] px-3 py-1 rounded border border-[#262a35]">
              ACTIVE NODE: {selectedNode.label}
            </span>
          </div>

          {/* 6 Node Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
            {pipelineNodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              return (
                <button
                  key={node.id}
                  onClick={() => setSelectedNodeId(node.id)}
                  className={`text-left p-3.5 rounded border transition-all text-xs flex flex-col justify-between ${
                    isSelected
                      ? 'bg-[#262a35] border-[#ffc174] shadow-md ring-1 ring-[#ffc174]'
                      : 'bg-[#171b26] border-[#262a35] hover:bg-[#262a35]/60'
                  }`}
                  type="button"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-caption-mono text-[10px] px-1.5 py-0.5 rounded bg-[#0a0e18] text-[#7bd0ff] font-bold">
                        {node.label}
                      </span>
                      <span className="material-symbols-outlined text-[#7bd0ff] text-base">{node.icon}</span>
                    </div>
                    <div className="font-title-sm font-bold text-[#dfe2f1] mb-1">{node.name}</div>
                    <p className="font-body-sm text-[11px] text-[#a08e7a] line-clamp-2">{node.desc}</p>
                  </div>
                  <div className="mt-3 pt-2 border-t border-[#262a35] flex items-center justify-between text-[10px] font-caption-mono">
                    <span className="text-[#a08e7a]">{node.metricLabel}</span>
                    <span className="text-[#ffc174] font-bold">{node.metricValue}</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Node Detail Telemetry Panel */}
          <div className="mt-4 p-4 rounded bg-[#0a0e18] border border-[#262a35] grid grid-cols-1 md:grid-cols-5 gap-4 font-caption-mono text-xs">
            <div>
              <span className="text-[#a08e7a] block mb-0.5">RUNTIME EXECUTOR:</span>
              <span className="text-[#dfe2f1] font-bold">{selectedNode.techDetails.runtime}</span>
            </div>
            <div>
              <span className="text-[#a08e7a] block mb-0.5">PEAK THROUGHPUT:</span>
              <span className="text-[#ffc174] font-bold">{selectedNode.techDetails.throughput}</span>
            </div>
            <div>
              <span className="text-[#a08e7a] block mb-0.5">REJECTION RATE:</span>
              <span className="text-[#7bd0ff] font-bold">{selectedNode.techDetails.rejectionRate}</span>
            </div>
            <div>
              <span className="text-[#a08e7a] block mb-0.5">MEMORY BUFFER:</span>
              <span className="text-[#dfe2f1] font-bold">{selectedNode.techDetails.memoryFootprint}</span>
            </div>
            <div>
              <span className="text-[#a08e7a] block mb-0.5">VALIDATION STATE:</span>
              <span className="text-[#10B981] font-bold">{selectedNode.techDetails.validationStatus}</span>
            </div>
          </div>
        </div>

        {/* Confidence & Provenance Lineage */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sensor Confidence Distributions */}
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md flex flex-col justify-between">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">Confidence Class Distribution</h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">Native classes mapped to canonical low, nominal, high scale</span>
              </div>
              <span className="px-2 py-0.5 rounded bg-[#0a0e18] text-[#7bd0ff] font-caption-mono text-xs">FIRMS Mappings</span>
            </div>

            <div className="space-y-3 font-caption-mono text-xs">
              <div>
                <div className="flex justify-between text-[#dfe2f1] mb-1">
                  <span>VIIRS High Confidence (&gt;80%)</span>
                  <span className="text-[#ffc174] font-bold">68.4% (81,020)</span>
                </div>
                <div className="w-full bg-[#0a0e18] h-2.5 rounded-full overflow-hidden border border-[#262a35]">
                  <div className="bg-[#f59e0b] h-full rounded-full" style={{ width: '68.4%' }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-[#dfe2f1] mb-1">
                  <span>VIIRS Nominal Confidence (50–80%)</span>
                  <span className="text-[#7bd0ff] font-bold">26.8% (31,745)</span>
                </div>
                <div className="w-full bg-[#0a0e18] h-2.5 rounded-full overflow-hidden border border-[#262a35]">
                  <div className="bg-[#7bd0ff] h-full rounded-full" style={{ width: '26.8%' }}></div>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-[#dfe2f1] mb-1">
                  <span>MODIS Nominal + High Detections</span>
                  <span className="text-[#ffbcb7] font-bold">94.2% (45,517)</span>
                </div>
                <div className="w-full bg-[#0a0e18] h-2.5 rounded-full overflow-hidden border border-[#262a35]">
                  <div className="bg-[#ffbcb7] h-full rounded-full" style={{ width: '94.2%' }}></div>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-[#262a35] flex justify-between font-caption-mono text-[11px] text-[#a08e7a]">
              <span>Low-confidence dropped: 0.04%</span>
              <span className="text-[#10B981]">QC Threshold: Nominal (&gt;50%)</span>
            </div>
          </div>

          {/* SHA-256 Provenance & Lineage Table */}
          <div className="bg-[#1c1f2a] border border-[#262a35] rounded-lg p-5 shadow-md flex flex-col justify-between">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1]">Verifiable Data Lineage Table</h3>
                <span className="font-caption-mono text-xs text-[#a08e7a]">SHA-256 checksums and ingest batch records</span>
              </div>
              <span className="px-2 py-0.5 rounded bg-[#0a0e18] text-[#ffc174] font-caption-mono text-xs font-bold">
                v2026.11.13-r1
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left font-caption-mono text-[11px]">
                <thead>
                  <tr className="bg-[#0a0e18] text-[#a08e7a] uppercase border-b border-[#262a35]">
                    <th className="py-2 px-2.5">Source</th>
                    <th className="py-2 px-2.5">Batch ID</th>
                    <th className="py-2 px-2.5">Rows</th>
                    <th className="py-2 px-2.5 text-right">SHA-256 Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#262a35]">
                  <tr className="bg-[#171b26] text-[#dfe2f1]">
                    <td className="py-2 px-2.5 text-[#ffc174] font-bold">VIIRS VNP14IMG</td>
                    <td className="py-2 px-2.5">ING-202611-042</td>
                    <td className="py-2 px-2.5">118,450</td>
                    <td className="py-2 px-2.5 text-right font-mono text-[#7bd0ff]">4c8e...39f1</td>
                  </tr>
                  <tr className="bg-[#171b26] text-[#dfe2f1]">
                    <td className="py-2 px-2.5 text-[#ffbcb7] font-bold">MODIS MOD14</td>
                    <td className="py-2 px-2.5">ING-202611-041</td>
                    <td className="py-2 px-2.5">48,320</td>
                    <td className="py-2 px-2.5 text-right font-mono text-[#7bd0ff]">9a12...8e20</td>
                  </tr>
                  <tr className="bg-[#171b26] text-[#dfe2f1]">
                    <td className="py-2 px-2.5 text-[#7bd0ff] font-bold">H3 Harmonized</td>
                    <td className="py-2 px-2.5">CAL-M2-2026</td>
                    <td className="py-2 px-2.5">142,890</td>
                    <td className="py-2 px-2.5 text-right font-mono text-[#7bd0ff]">7e9a...c418</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="mt-4 pt-3 border-t border-[#262a35] flex justify-between font-caption-mono text-[11px] text-[#a08e7a]">
              <span>Git Commit: c8f32a0</span>
              <span className="text-[#7bd0ff]">In-Memory DuckDB Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
