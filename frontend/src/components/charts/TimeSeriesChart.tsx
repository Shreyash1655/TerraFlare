import EChart from './EChart';
import type { EChartsOption } from 'echarts';

interface DataPoint {
  period: string;
  harmonized: number;
  lower?: number;
  upper?: number;
  modis?: number;
  viirs?: number;
}

interface TimeSeriesChartProps {
  data: DataPoint[];
  title?: string;
  height?: string;
  className?: string;
}

export default function TimeSeriesChart({
  data,
  title,
  height = '240px',
  className = '',
}: TimeSeriesChartProps) {
  const periods = data.map((d) => d.period);
  const harmonizedValues = data.map((d) => d.harmonized);
  const modisValues = data.map((d) => d.modis ?? null);
  const viirsValues = data.map((d) => d.viirs ?? null);

  const option: EChartsOption = {
    backgroundColor: 'transparent',
    title: title
      ? {
          text: title,
          textStyle: { color: '#dfe2f1', fontSize: 13, fontFamily: 'Space Grotesk' },
        }
      : undefined,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1c1f2a',
      borderColor: '#374151',
      textStyle: { color: '#dfe2f1', fontFamily: 'JetBrains Mono', fontSize: 11 },
    },
    legend: {
      data: ['Harmonized', 'VIIRS (375m)', 'MODIS (1km)'],
      textStyle: { color: '#a08e7a', fontSize: 11, fontFamily: 'JetBrains Mono' },
      top: 0,
      right: 0,
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
      data: periods,
      axisLine: { lineStyle: { color: '#262a35' } },
      axisLabel: { color: '#a08e7a', fontFamily: 'JetBrains Mono', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#262a35', type: 'dashed' } },
      axisLabel: { color: '#a08e7a', fontFamily: 'JetBrains Mono', fontSize: 10 },
    },
    series: [
      {
        name: 'Harmonized',
        type: 'line',
        data: harmonizedValues,
        smooth: true,
        lineStyle: { color: '#ffc174', width: 2.5 },
        itemStyle: { color: '#ffc174' },
      },
      {
        name: 'VIIRS (375m)',
        type: 'line',
        data: viirsValues,
        smooth: true,
        lineStyle: { color: '#7bd0ff', width: 1.8 },
        itemStyle: { color: '#7bd0ff' },
      },
      {
        name: 'MODIS (1km)',
        type: 'line',
        data: modisValues,
        smooth: true,
        lineStyle: { color: '#ffbcb7', width: 1.8, type: 'dashed' },
        itemStyle: { color: '#ffbcb7' },
      },
    ],
  };

  return <EChart option={option} style={{ height, width: '100%' }} className={className} />;
}
