export interface FeatureConfig {
    id: string;
    name: string;
    enabled: boolean;
    path: string;
    group: 'core' | 'advanced';
}

export const featureRegistry: Record<string, FeatureConfig> = {
    // Core Features
    dashboard: { id: 'dashboard', name: 'Dashboard', enabled: true, path: '/', group: 'core' },
    hotspotMap: { id: 'hotspotMap', name: 'Hotspot Map', enabled: true, path: '/map', group: 'core' },
    calendar: { id: 'calendar', name: 'Activity Calendar', enabled: true, path: '/calendar', group: 'core' },
    history: { id: 'history', name: 'Historical Analysis', enabled: true, path: '/history', group: 'core' },
    currentVsMedian: { id: 'currentVsMedian', name: 'Current vs Median', enabled: true, path: '/current-vs-median', group: 'core' },
    comparison: { id: 'comparison', name: 'Sensor Comparison', enabled: true, path: '/comparison', group: 'core' },

    // Advanced Features
    quality: { id: 'quality', name: 'Data Quality & Provenance', enabled: true, path: '/advanced/quality', group: 'advanced' },
    anomaly: { id: 'anomaly', name: 'Anomaly Engine', enabled: true, path: '/advanced/anomalies', group: 'advanced' },
    seasonShift: { id: 'seasonShift', name: 'Season Shift', enabled: true, path: '/advanced/season-shift', group: 'advanced' },
    fireMemory: { id: 'fireMemory', name: 'Fire Memory Map', enabled: true, path: '/advanced/fire-memory', group: 'advanced' },
    events: { id: 'events', name: 'Event Tracking', enabled: false, path: '/advanced/events', group: 'advanced' },
    exposure: { id: 'exposure', name: 'Impact & Exposure', enabled: false, path: '/advanced/exposure', group: 'advanced' },
};

export const getNavigationLinks = () => {
    const enabledFeatures = Object.values(featureRegistry).filter(f => f.enabled);
    return {
        core: enabledFeatures.filter(f => f.group === 'core'),
        advanced: enabledFeatures.filter(f => f.group === 'advanced'),
    };
};