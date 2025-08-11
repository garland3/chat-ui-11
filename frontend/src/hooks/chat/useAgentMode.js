import { useEffect } from 'react'
import { usePersistentState } from './usePersistentState'

export function useAgentMode(available = true) {
  const [agentModeEnabled, setAgentModeEnabled] = usePersistentState('chatui-agent-mode-enabled', false)
  const [agentMaxSteps, setAgentMaxSteps] = usePersistentState('chatui-agent-max-steps', 5)
  const [currentAgentStep, setCurrentAgentStep] = usePersistentState('chatui-agent-current-step', 0)

  // If availability turns off, force-disable stored state
  useEffect(() => {
    if (!available && agentModeEnabled) {
      setAgentModeEnabled(false)
    }
  }, [available, agentModeEnabled, setAgentModeEnabled])

  return {
    agentModeEnabled,
    setAgentModeEnabled,
    agentMaxSteps,
    setAgentMaxSteps,
    currentAgentStep,
    setCurrentAgentStep,
    agentModeAvailable: available
  }
}
