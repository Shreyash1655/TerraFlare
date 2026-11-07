interface MethodDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function MethodDrawer({ isOpen, onClose }: MethodDrawerProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[#0a0e18]/80 backdrop-blur-sm z-50 transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Drawer */}
      <aside className="fixed top-0 right-0 h-full w-full max-w-xl bg-[#1c1f2a] z-50 shadow-2xl border-l border-[#262a35] flex flex-col overflow-hidden animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="p-6 bg-[#0a0e18] border-b border-[#262a35] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-[#ffc174]/10 border border-[#ffc174]/30 flex items-center justify-center">
              <span className="material-symbols-outlined text-[#ffc174] text-xl">biotech</span>
            </div>
            <div>
              <h2 className="font-headline-sm text-lg font-bold text-[#dfe2f1]">Methodology &amp; Scientific Protocol</h2>
              <span className="font-caption-mono text-xs text-[#7bd0ff]">NASA Space Apps Challenge 2026 Overlap Fixture</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded bg-[#262a35] hover:bg-[#313540] flex items-center justify-center text-[#dfe2f1] transition-colors"
          >
            <span className="material-symbols-outlined text-base">close</span>
          </button>
        </div>

        {/* Content Scroll Area */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 font-body-sm text-xs text-[#d8c3ad]">
          {/* Section 1 */}
          <section className="space-y-2">
            <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#7bd0ff] text-base">lock_clock</span>
              1. Temporal Holdout Protocol (CV Strategy)
            </h3>
            <p className="leading-relaxed">
              Standard k-fold cross-validation is invalid for spatial time series due to temporal autocorrelation. TerraFlare deploys a strict <strong>Blocked Temporal Cross-Validation</strong>:
            </p>
            <ul className="list-disc list-inside space-y-1.5 bg-[#171b26] p-3 rounded border border-[#262a35] font-caption-mono text-xs text-[#dfe2f1]">
              <li><strong>Training Period:</strong> 2012–2020 (8 years continuous concurrent overlap).</li>
              <li><strong>Validation Buffer:</strong> 180-day moratorium to prevent seasonal spillover.</li>
              <li><strong>Out-of-Time Holdout:</strong> 2021–2025 evaluated with blocked Leave-One-Year-Out (LOYO).</li>
            </ul>
          </section>

          {/* Section 2 */}
          <section className="space-y-2">
            <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#ffc174] text-base">functions</span>
              2. Explicit Uncertainty Quantification Formulation
            </h3>
            <p className="leading-relaxed">
              Prediction intervals for harmonized counts (Ŷ_h) are computed using a non-parametric residual bootstrap conditioned on local cluster density:
            </p>
            <div className="p-3.5 rounded bg-[#0a0e18] border border-[#262a35] font-caption-mono text-xs space-y-2 text-[#ffc174]">
              <div className="text-[#dfe2f1] font-semibold">Bootstrap Resampling Formulation:</div>
              <div className="p-2 bg-[#1c1f2a] rounded text-xs font-mono font-bold text-[#7bd0ff]">
                Ŷ_h^(b) = f_M2(X_VIIRS, B, S) + ε_b*
              </div>
              <p className="text-[#a08e7a] text-[11px] leading-normal">
                Where B represents WWF Biome classification (1–14), S is diurnal solar zenith quartile, and ε_b* is the empirical stratified error distribution.
              </p>
              <div className="text-[#dfe2f1] text-[11px]">
                Coverage target: P(Y ∈ [Ŷ_0.025, Ŷ_0.975]) = 94.6% (Nominal 95.0%).
              </div>
            </div>
          </section>

          {/* Section 3 */}
          <section className="space-y-2">
            <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[#ffb4ab] text-base">warning</span>
              3. Assumptions &amp; Limitations Register (docs/LIMITATIONS.md)
            </h3>
            <div className="space-y-2 font-caption-mono text-xs">
              <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                <span className="text-[#ffc174] font-semibold block mb-0.5">A1. Cloud Masking Asynchrony:</span>
                <span className="text-[#a08e7a]">
                  Aqua and S-NPP orbits have a 15–35 minute phase offset. Convective cloud drift can obscure a fire from VIIRS while visible to MODIS or vice versa.
                </span>
              </div>
              <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                <span className="text-[#ffc174] font-semibold block mb-0.5">A2. Fire Front Kinetics:</span>
                <span className="text-[#a08e7a]">
                  Harmonization assumes stationary fire behavior during overpasses. Rapid crown fires with high rate of spread naturally present elevated VIIRS counts.
                </span>
              </div>
              <div className="p-3 rounded bg-[#171b26] border border-[#262a35]">
                <span className="text-[#ffc174] font-semibold block mb-0.5">A3. Scan Angle Footprint Deformation:</span>
                <span className="text-[#a08e7a]">
                  VIIRS pixel size expands to ~800m at scan edge; MODIS expands to 2x5km. Off-nadir observations carry 1.8x wider uncertainty bands.
                </span>
              </div>
            </div>
          </section>

          {/* Provenance Details */}
          <section className="p-3 rounded bg-[#0a0e18] border border-[#262a35] font-caption-mono text-xs space-y-1.5">
            <div className="flex justify-between text-[#a08e7a]">
              <span>MODEL ARTIFACT HASH:</span>
              <span className="text-[#7bd0ff] font-mono">sha256:7e9a3b...c418</span>
            </div>
            <div className="flex justify-between text-[#a08e7a]">
              <span>DUCKDB PARQUET SCHEMA:</span>
              <span className="text-[#dfe2f1]">h3_cell_day_canonical_v1.parquet</span>
            </div>
            <div className="flex justify-between text-[#a08e7a]">
              <span>FIRMS INGESTION DATE:</span>
              <span>2026-03-31T23:59:59Z</span>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="p-4 bg-[#0a0e18] border-t border-[#262a35] flex items-center justify-between gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded bg-[#262a35] hover:bg-[#313540] text-[#dfe2f1] font-label-mono text-xs font-semibold transition-colors text-center"
          >
            Close Scientific Protocol
          </button>
        </div>
      </aside>
    </>
  );
}
