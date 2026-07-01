import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import GrowthMap from '@/pages/GrowthMap'
import AreaAnalyzer from '@/pages/AreaAnalyzer'
import OpportunityFinder from '@/pages/OpportunityFinder'
import CompareAreas from '@/pages/CompareAreas'
import Watchlist from '@/pages/Watchlist'
import Reports from '@/pages/Reports'
import DataSources from '@/pages/DataSources'
import Admin from '@/pages/Admin'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/map" replace /> },
      { path: 'map', element: <GrowthMap /> },
      { path: 'analyzer', element: <AreaAnalyzer /> },
      { path: 'opportunities', element: <OpportunityFinder /> },
      { path: 'compare', element: <CompareAreas /> },
      { path: 'watchlist', element: <Watchlist /> },
      { path: 'reports', element: <Reports /> },
      { path: 'data-sources', element: <DataSources /> },
      { path: 'admin', element: <Admin /> },
    ],
  },
])
