import EChart from './EChart';
import type { EChartsOption } from 'echarts';

interface CalendarHeatmapProps {
  year?: number;
  data?: [string, number][];
  height?: string;
  className?: string;
}

export default function CalendarHeatmap({
  year = 2024,
  data = [],
  height = '220px',
  className = '',
}: CalendarHeatmapProps) {
  // Generate sample points if not provided
  const chartData: [string, number][] =
    data.length > 0
      ? data
      : Array.from({ length: 180 }).map((_, i) => {
          const d = new Date(year, 4, 1 + i);
          const dateStr = d.toISOString().split('T')[0];
          const val = Math.floor(Math.sin(i / 15) * 200 + ((i * 31) % 80) + 50);
          return [dateStr, Math.max(0, val)];
        });

  const option: EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      position: 'top',
      backgroundColor: '#1c1f2a',
      borderColor: '#374151',
      textStyle: { color: '#dfe2f1', fontFamily: 'JetBrains Mono', fontSize: 11 },
      formatter: (params: unknown) => {
        const p = params as { value?: [string, number] };
        if (Array.isArray(p.value)) {
          return `${p.value[0]}: ${p.value[1]} eq/day`;
        }
        return '';
      },
    },
    visualMap: {
      min: 0,
      max: 400,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#171b26', '#313540', '#7bd0ff', '#f59e0b', '#ff938c'],
      },
      textStyle: {
        color: '#a08e7a',
        fontFamily: 'JetBrains Mono',
        fontSize: 10,
      },
    },
    calendar: {
      top: '15%',
      left: '3%',
      right: '3%',
      bottom: '22%',
      range: String(year),
      cellSize: ['auto', 13],
      splitLine: { show: true, lineStyle: { color: '#262a35' } },
      itemStyle: { color: '#0a0e18', borderColor: '#1F2937' },
      yearLabel: { show: false },
      monthLabel: { color: '#a08e7a', fontFamily: 'JetBrains Mono', fontSize: 10 },
      dayLabel: { color: '#a08e7a', fontFamily: 'JetBrains Mono', fontSize: 9 },
    },
    series: [
      {
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: chartData,
      },
    ],
  };

  return <EChart option={option} style={{ height, width: '100%' }} className={className} />;
}
