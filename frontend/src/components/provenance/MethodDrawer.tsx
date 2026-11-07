
import { useEffect, useState } from 'react';
import { getHarmonizationMethod } from '../../api/core';

interface MethodDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function MethodDrawer({
  isOpen,
  onClose,
}: MethodDrawerProps) {
  const [method, setMethod] = useState<
    Awaited<ReturnType<typeof getHarmonizationMethod>>['data'] | null
  >(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    if (!isOpen) return;

    let cancelled = false;

    const fetchMethodology = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await getHarmonizationMethod();

        if (!cancelled) {
          setMethod(response.data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : 'Unable to retrieve methodology information.'
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchMethodology();

    return () => {
      cancelled = true;
    };
  }, [isOpen, retryCount]);

  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);

    return () => {
      window.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <button
        type="button"
        aria-label="Close methodology drawer"
        className="fixed inset-0 bg-[#0a0e18]/80 backdrop-blur-sm z-50 cursor-default"
        onClick={onClose}
      />

      {/* Drawer */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="method-drawer-title"
        className="fixed top-0 right-0 h-full w-full max-w-xl bg-[#1c1f2a] z-50 shadow-2xl border-l border-[#262a35] flex flex-col overflow-hidden animate-in slide-in-from-right duration-300"
      >
        {/* Header */}
        <div className="p-6 bg-[#0a0e18] border-b border-[#262a35] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-[#ffc174]/10 border border-[#ffc174]/30 flex items-center justify-center">
              <span className="material-symbols-outlined text-[#ffc174] text-xl">
                biotech
              </span>
            </div>

            <div>
              <h2
                id="method-drawer-title"
                className="font-headline-sm text-lg font-bold text-[#dfe2f1]"
              >
                Methodology &amp; Scientific Protocol
              </h2>

              <span className="font-caption-mono text-xs text-[#7bd0ff]">
                TerraFlare · Harmonization Method
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            type="button"
            aria-label="Close"
            className="w-8 h-8 rounded bg-[#262a35] hover:bg-[#313540] flex items-center justify-center text-[#dfe2f1] transition-colors"
          >
            <span className="material-symbols-outlined text-base">
              close
            </span>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 font-body-sm text-xs text-[#d8c3ad]">
          {loading && (
            <div className="flex flex-col items-center justify-center min-h-[220px] gap-3">
              <span className="material-symbols-outlined text-3xl text-[#7bd0ff] animate-spin">
                progress_activity
              </span>

              <p className="text-[#a08e7a]">
                Retrieving scientific methodology...
              </p>
            </div>
          )}

          {!loading && error && (
            <div className="p-4 rounded bg-[#93000a]/10 border border-[#ffb4ab]/30 space-y-3">
              <h3 className="text-[#ffb4ab] font-bold">
                Methodology unavailable
              </h3>

              <p className="text-[#d8c3ad]">{error}</p>

              <button
                type="button"
                onClick={() => {
                  setRetryCount((count) => count + 1);
                }}
                className="text-[#7bd0ff] underline"
              >
                Retry
              </button>
            </div>
          )}

          {!loading && !error && method && (
            <>
              {/* Method identification */}
              <section className="space-y-2">
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[#7bd0ff] text-base">
                    account_tree
                  </span>
                  Harmonization Method
                </h3>

                <div className="p-3 rounded bg-[#171b26] border border-[#262a35] space-y-2">
                  <div className="flex justify-between gap-3">
                    <span className="text-[#a08e7a]">
                      METHOD IDENTIFIER
                    </span>

                    <span className="text-[#7bd0ff] font-mono">
                      {method.method_id}
                    </span>
                  </div>

                  <p className="text-[#d8c3ad] leading-relaxed">
                    {method.description}
                  </p>
                </div>
              </section>

              {/* Overlap period */}
              <section className="space-y-2">
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[#ffc174] text-base">
                    date_range
                  </span>
                  Sensor Overlap Period
                </h3>

                <div className="p-3 rounded bg-[#171b26] border border-[#262a35] flex justify-between gap-3">
                  <div>
                    <span className="block text-[#a08e7a] text-[10px]">
                      START
                    </span>

                    <span className="text-[#dfe2f1]">
                      {method.overlap_period.start}
                    </span>
                  </div>

                  <div>
                    <span className="block text-[#a08e7a] text-[10px]">
                      END
                    </span>

                    <span className="text-[#dfe2f1]">
                      {method.overlap_period.end}
                    </span>
                  </div>
                </div>
              </section>

              {/* Assumptions */}
              <section className="space-y-2">
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[#7bd0ff] text-base">
                    science
                  </span>
                  Methodological Assumptions
                </h3>

                {method.assumptions.length > 0 ? (
                  <ul className="space-y-2">
                    {method.assumptions.map((assumption, index) => (
                      <li
                        key={index}
                        className="p-3 rounded bg-[#171b26] border border-[#262a35] text-[#d8c3ad] leading-relaxed"
                      >
                        {assumption}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[#a08e7a]">
                    No assumptions have been supplied by the backend.
                  </p>
                )}
              </section>

              {/* Limitations */}
              <section className="space-y-2">
                <h3 className="font-title-sm text-sm font-bold text-[#dfe2f1] flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[#ffb4ab] text-base">
                    warning
                  </span>
                  Scientific Limitations
                </h3>

                {method.limitations.length > 0 ? (
                  <ul className="space-y-2">
                    {method.limitations.map((limitation, index) => (
                      <li
                        key={index}
                        className="p-3 rounded bg-[#171b26] border border-[#262a35] text-[#a08e7a] leading-relaxed"
                      >
                        {limitation}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[#a08e7a]">
                    No limitations have been supplied by the backend.
                  </p>
                )}
              </section>

              
{/* Validation information */}
<section className="p-3 rounded bg-[#0a0e18] border border-[#262a35] space-y-3">
  <h3 className="text-[#dfe2f1] font-semibold flex items-center gap-1.5">
    <span className="material-symbols-outlined text-[#ffc174] text-base">
      verified
    </span>
    Validation Information
  </h3>

  {method.validation.length > 0 ? (
    <ul className="space-y-3">
      {method.validation.map((item, index) => (
        <li
          key={index}
          className="p-3 rounded bg-[#171b26] border border-[#262a35] space-y-1.5"
        >
          {Object.entries(item).map(([key, value]) => (
            <div
              key={key}
              className="flex justify-between items-start gap-3"
            >
              <span className="text-[#7bd0ff] text-[10px] uppercase">
                {key.replace(/_/g, ' ')}
              </span>

              <span className="text-[#d8c3ad] text-right break-words">
                {typeof value === 'object' && value !== null
                  ? JSON.stringify(value)
                  : String(value ?? '—')}
              </span>
            </div>
          ))}
        </li>
      ))}
    </ul>
  ) : (
    <p className="text-[#a08e7a]">
      No validation information is currently available.
    </p>
  )}
</section>

            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 bg-[#0a0e18] border-t border-[#262a35]">
          <button
            onClick={onClose}
            type="button"
            className="w-full py-2 rounded bg-[#262a35] hover:bg-[#313540] text-[#dfe2f1] font-label-mono text-xs font-semibold transition-colors"
          >
            Close Scientific Protocol
          </button>
        </div>
      </aside>
    </>
  );
}
