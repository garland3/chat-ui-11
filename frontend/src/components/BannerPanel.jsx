import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useWS } from '../contexts/WSContext'

function BannerPanel() {
  const [bannerMessages, setBannerMessages] = useState([])
  const [dismissedMessages, setDismissedMessages] = useState(new Set())
  const [bannerEnabled, setBannerEnabled] = useState(false)
  const { config, configLoaded } = useWS()

  useEffect(() => {
    // Fetch banner messages from the backend (config is now provided by WSContext)
    const fetchBanners = async () => {
      try {
        // Check if config is loaded and banners are enabled
        if (configLoaded && config && !config.banner_enabled) {
          setBannerEnabled(false)
          return
        }
        
        if (configLoaded && config && config.banner_enabled) {
          setBannerEnabled(true)
          
          // If banners are enabled, fetch the messages
          const bannersResponse = await fetch('/api/banners')
          const bannersData = await bannersResponse.json()
          setBannerMessages(bannersData.messages || [])
        }
      } catch (error) {
        console.error('Error fetching banner messages:', error)
        setBannerMessages([])
      }
    }

    fetchBanners()
    
    // Refresh banner messages every 5 minutes
    const interval = setInterval(fetchBanners, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [config, configLoaded])

  const handleDismiss = (index) => {
    setDismissedMessages(prev => new Set([...prev, index]))
  }

  // Don't render anything if config isn't loaded yet, banners are disabled, or no messages
  if (!configLoaded || !bannerEnabled || bannerMessages.length === 0) {
    return null
  }

  // Filter out dismissed messages
  const visibleMessages = bannerMessages.filter((_, index) => !dismissedMessages.has(index))

  if (visibleMessages.length === 0) {
    return null
  }

  return (
    <div className="w-full bg-gradient-to-r from-yellow-500 to-orange-500 text-white">
      {visibleMessages.map((message, originalIndex) => {
        // Find the original index in the full array
        const actualIndex = bannerMessages.findIndex((msg, idx) => 
          msg === message && !dismissedMessages.has(idx)
        )
        
        return (
          <div
            key={actualIndex}
            className="flex items-center justify-between px-4 py-2 border-b border-yellow-400 last:border-b-0"
          >
            <div className="flex-1 text-sm font-medium">
              {message}
            </div>
            <button
              onClick={() => handleDismiss(actualIndex)}
              className="ml-4 p-1 hover:bg-yellow-600 hover:bg-opacity-30 rounded-full transition-colors"
              aria-label="Dismiss banner"
            >
              <X size={16} />
            </button>
          </div>
        )
      })}
    </div>
  )
}

export default BannerPanel
