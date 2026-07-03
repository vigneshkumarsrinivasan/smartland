import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import { WatchlistProvider } from './context/WatchlistContext'
import { SubscriptionProvider } from './context/SubscriptionContext'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SubscriptionProvider>
      <WatchlistProvider>
        <RouterProvider router={router} />
      </WatchlistProvider>
    </SubscriptionProvider>
  </StrictMode>
)
