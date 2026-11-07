import { createBrowserRouter, Navigate } from 'react-router-dom';
import AppLayout from './layouts/AppLayout';
import DashboardPage from '../features/core/dashboard/DashboardPage';
import HotspotMapPage from '../features/core/hotspot-map/HotspotMapPage';
import CalendarPage from '../features/core/calendar/CalendarPage';
import HistoryPage from '../features/core/history/HistoryPage';
import CurrentVsMedianPage from '../features/core/current-vs-median/CurrentVsMedianPage';
import ComparisonPage from '../features/core/sensor-comparison/ComparisonPage';
import QualityPage from '../features/advanced/quality/QualityPage';
import AnomalyPage from '../features/advanced/anomaly/AnomalyPage';
import SeasonShiftPage from '../features/advanced/season-shift/SeasonShiftPage';
import FireMemoryPage from '../features/advanced/fire-memory/FireMemoryPage';
import EventsPage from '../features/advanced/events/EventsPage';
import ExposurePage from '../features/advanced/exposure/ExposurePage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'map',
        element: <HotspotMapPage />,
      },
      {
        path: 'calendar',
        element: <CalendarPage />,
      },
      {
        path: 'history',
        element: <HistoryPage />,
      },
      {
        path: 'current-vs-median',
        element: <CurrentVsMedianPage />,
      },
      {
        path: 'comparison',
        element: <ComparisonPage />,
      },
      {
        path: 'advanced',
        element: <Navigate to="/advanced/season-shift" replace />,
      },
      {
        path: 'advanced/season-shift',
        element: <SeasonShiftPage />,
      },
      {
        path: 'advanced/anomalies',
        element: <AnomalyPage />,
      },
      {
        path: 'advanced/anomaly',
        element: <AnomalyPage />,
      },
      {
        path: 'advanced/fire-memory',
        element: <FireMemoryPage />,
      },
      {
        path: 'advanced/events',
        element: <EventsPage />,
      },
      {
        path: 'advanced/exposure',
        element: <ExposurePage />,
      },
      {
        path: 'advanced/quality',
        element: <QualityPage />,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      },
    ],
  },
]);
