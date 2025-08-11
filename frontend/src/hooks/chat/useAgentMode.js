import { usePersistentState } from './usePersistentState'

export function useAgentMode(available = true) {
  const [agentModeEnabled, setAgentModeEnabled] = usePersistentState('chatui-agent-mode-enabled', false)
  const [agentMaxSteps, setAgentMaxSteps] = usePersistentState('chatui-agent-max-steps', 5)
  const [currentAgentStep, setCurrentAgentStep] = usePersistentState('chatui-agent-current-step', 0)

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
