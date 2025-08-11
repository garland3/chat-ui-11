import { useCallback, useMemo } from 'react'
import { usePersistentState } from './usePersistentState'

const toSet = arr => new Set(arr)
const toArray = set => Array.from(set)

export function useSelections() {
  // Auto-select canvas tool if empty
  const [toolsRaw, setToolsRaw] = usePersistentState('chatui-selected-tools', ['canvas_canvas'])
  const [promptsRaw, setPromptsRaw] = usePersistentState('chatui-selected-prompts', [])
  const [dataSourcesRaw, setDataSourcesRaw] = usePersistentState('chatui-selected-data-sources', [])
  const [toolChoiceRequired, setToolChoiceRequired] = usePersistentState('chatui-tool-choice-required', false)

  const selectedTools = useMemo(() => toSet(toolsRaw), [toolsRaw])
  const selectedPrompts = useMemo(() => toSet(promptsRaw), [promptsRaw])
  const selectedDataSources = useMemo(() => toSet(dataSourcesRaw), [dataSourcesRaw])

  const toggleSetItem = (currentSet, setUpdater, key) => {
    const next = new Set(currentSet)
    next.has(key) ? next.delete(key) : next.add(key)
    setUpdater(toArray(next))
  }

  const toggleTool = useCallback(k => toggleSetItem(selectedTools, setToolsRaw, k), [selectedTools, setToolsRaw])
  const togglePrompt = useCallback(k => toggleSetItem(selectedPrompts, setPromptsRaw, k), [selectedPrompts, setPromptsRaw])
  const toggleDataSource = useCallback(k => toggleSetItem(selectedDataSources, setDataSourcesRaw, k), [selectedDataSources, setDataSourcesRaw])

  const clearToolsAndPrompts = useCallback(() => {
    setToolsRaw([])
    setPromptsRaw([])
    localStorage.removeItem('chatui-selected-tools')
    localStorage.removeItem('chatui-selected-prompts')
  }, [setToolsRaw, setPromptsRaw])

  return {
    selectedTools,
    selectedPrompts,
    selectedDataSources,
    toggleTool,
    togglePrompt,
    toggleDataSource,
    toolChoiceRequired,
    setToolChoiceRequired,
    clearToolsAndPrompts
  }
}
