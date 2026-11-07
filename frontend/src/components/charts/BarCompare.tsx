import EChart from './EChart';
import type { EChartsOption } from 'echarts';

interface BarCompareProps {
  categories: string[];
  seriesData: {
    name: string;
    data: number[];
    color: string;
  }[];
  height?: string;
  className?: string;
}

export default function BarCompare({
  categories,
  seriesData,
  height = '260px',
  className = '',
}: BarCompareProps) {
  const option: EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#1c1f2a',
      borderColor: '#374151',
      textStyle: { color: '#dfe2f1', fontFamily: 'JetBrains Mono', fontSize: 11 },
    },
    legend: {
      textStyle: { color: '#a08e7a', fontSize: 11, fontFamily: 'JetBrains Mono' },
      top: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '18%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLine: { lineStyle: { color: '#262a35' } },
      axisLabel: { color: '#a08e7a', fontFamily: 'JetBrains Mono', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#262a35', type: 'dashed' } },
      axisLabel: { color: '#a08e7a', fontFamily: 'JetBrains Mono', fontSize: 10 },
    },
    series: seriesData.map((s) => ({
      name: s.name,
      type: 'bar',
      data: s.data,
      itemStyle: { color: s.color, borderRadius: [2, 2, 0, 0] },
    })),
  };

  return <EChart option={option} style={{ height, width: '100%' }} className={className} />;
}
