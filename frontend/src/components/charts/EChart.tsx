import ReactECharts from 'echarts-for-react';
import type { EChartsOption } from 'echarts';

interface EChartProps {
  option: EChartsOption;
  style?: React.CSSProperties;
  className?: string;
  loading?: boolean;
}

export default function EChart({
  option,
  style = { height: '300px', width: '100%' },
  className = '',
  loading = false,
}: EChartProps) {
  return (
    <div className={`relative w-full ${className}`}>
      <ReactECharts
        option={option}
        style={style}
        showLoading={loading}
        loadingOption={{
          text: 'Loading telemetry...',
          color: '#f59e0b',
          textColor: '#dfe2f1',
          maskColor: 'rgba(11, 15, 25, 0.8)',
        }}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  );
}
