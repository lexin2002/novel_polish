import { create } from 'zustand'
import axios from 'axios'

/** Generate a unique ID for stable dnd-kit sortable keys */
function generateId(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/** Recursively assign IDs to items that are missing them */
function ensureIds(data: RulesState): RulesState {
  return {
    main_categories: data.main_categories.map((cat) => ({
      ...cat,
      id: cat.id || generateId(),
      sub_categories: cat.sub_categories.map((sub) => ({
        ...sub,
        id: sub.id || generateId(),
        rules: sub.rules.map((rule) => ({
          ...rule,
          id: rule.id || generateId(),
        })),
      })),
    })),
  }
}

export interface Rule {
  id: string
  name: string
  is_active: boolean
  instruction: string
  direction?: string
}

export interface SubCategory {
  id: string
  name: string
  priority: string
  rules: Rule[]
}

export interface MainCategory {
  id: string
  name: string
  priority: string
  is_active: boolean
  sub_categories: SubCategory[]
}

export interface RulesState {
  main_categories: MainCategory[]
}

interface RuleStore {
  draft: RulesState | null
  original: RulesState | null
  isLoading: boolean
  isSyncing: boolean
  error: string | null
  validationErrors: string[]

  // Actions
  fetchRules: () => Promise<void>
  submitRules: () => Promise<boolean>
  revertRules: () => void

  // Node operations
  updateCategory: (index: number, updates: Partial<MainCategory>) => void
  updateSubCategory: (catIndex: number, subIndex: number, updates: Partial<SubCategory>) => void
  updateRule: (catIndex: number, subIndex: number, ruleIndex: number, updates: Partial<Rule>) => void

  // Drag and drop
  moveCategory: (fromIndex: number, toIndex: number) => void
  moveSubCategory: (catIndex: number, fromIndex: number, toIndex: number) => void
  moveRule: (catIndex: number, subIndex: number, fromIndex: number, toIndex: number) => void

  // Add/Delete operations
  addCategory: () => void
  deleteCategory: (index: number) => void
  addSubCategory: (catIndex: number) => void
  deleteSubCategory: (catIndex: number, subIndex: number) => void
  addRule: (catIndex: number, subIndex: number) => void
  deleteRule: (catIndex: number, subIndex: number, ruleIndex: number) => void

  // Validation
  validatePriority: (priority: string, validPriorities: string[]) => boolean
  validateAllPriorities: (validPriorities: string[]) => boolean
  clearValidationErrors: () => void
}

export const useRuleStore = create<RuleStore>((set, get) => ({
  draft: null,
  original: null,
  isLoading: false,
  isSyncing: false,
  error: null,
  validationErrors: [],

  fetchRules: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await axios.get<RulesState>('/api/rules')
      const data = response.data
      // Deep clone & ensure every node has a unique id for stable drag & drop keys
      // ensureIds already deep-clones via spread operators, no extra clone needed
      const withIds = ensureIds(data)
      set({
        draft: withIds,
        original: withIds,
        isLoading: false,
      })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch rules'
      set({ error: message, isLoading: false })
    }
  },

  submitRules: async () => {
    const { draft, validateAllPriorities } = get()
    if (!draft) return false

    // Get valid priorities from config
    try {
      const configResponse = await axios.get('/api/config')
      const validPriorities = configResponse.data.priority_order || ['P0', 'P1', 'P2', 'P3']

      // Validate all priorities before submitting
      if (!validateAllPriorities(validPriorities)) {
        return false
      }

      set({ isSyncing: true, error: null })
      await axios.post('/api/rules', draft)
      set((state) => ({
        original: state.draft ? structuredClone(state.draft) : null,
        isSyncing: false,
      }))
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to submit rules'
      set({ error: message, isSyncing: false })
      return false
    }
  },

  revertRules: () => {
    const { original } = get()
    if (original) {
      set({ draft: ensureIds(JSON.parse(JSON.stringify(original))), validationErrors: [] })
    }
  },

  updateCategory: (index: number, updates: Partial<MainCategory>) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      newDraft.main_categories = [...newDraft.main_categories]
      newDraft.main_categories[index] = {
        ...newDraft.main_categories[index],
        ...updates,
      }
      return { draft: newDraft }
    })
  },

  updateSubCategory: (catIndex: number, subIndex: number, updates: Partial<SubCategory>) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      newDraft.main_categories = [...newDraft.main_categories]
      const cat = { ...newDraft.main_categories[catIndex] }
      cat.sub_categories = [...cat.sub_categories]
      cat.sub_categories[subIndex] = { ...cat.sub_categories[subIndex], ...updates }
      newDraft.main_categories[catIndex] = cat
      return { draft: newDraft }
    })
  },

  updateRule: (catIndex: number, subIndex: number, ruleIndex: number, updates: Partial<Rule>) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      newDraft.main_categories = [...newDraft.main_categories]
      const cat = { ...newDraft.main_categories[catIndex] }
      cat.sub_categories = [...cat.sub_categories]
      const subCat = { ...cat.sub_categories[subIndex] }
      subCat.rules = [...subCat.rules]
      subCat.rules[ruleIndex] = { ...subCat.rules[ruleIndex], ...updates }
      cat.sub_categories[subIndex] = subCat
      newDraft.main_categories[catIndex] = cat
      return { draft: newDraft }
    })
  },

  moveCategory: (fromIndex: number, toIndex: number) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      const cats = [...newDraft.main_categories]
      const [removed] = cats.splice(fromIndex, 1)
      cats.splice(toIndex, 0, removed)
      newDraft.main_categories = cats
      return { draft: newDraft }
    })
  },

  moveSubCategory: (catIndex: number, fromIndex: number, toIndex: number) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      const cats = [...newDraft.main_categories]
      const cat = { ...cats[catIndex] }
      const subs = [...cat.sub_categories]
      const [removed] = subs.splice(fromIndex, 1)
      subs.splice(toIndex, 0, removed)
      cat.sub_categories = subs
      cats[catIndex] = cat
      newDraft.main_categories = cats
      return { draft: newDraft }
    })
  },

  moveRule: (catIndex: number, subIndex: number, fromIndex: number, toIndex: number) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      const cats = [...newDraft.main_categories]
      const cat = { ...cats[catIndex] }
      const subs = [...cat.sub_categories]
      const subCat = { ...subs[subIndex] }
      const rules = [...subCat.rules]
      const [removed] = rules.splice(fromIndex, 1)
      rules.splice(toIndex, 0, removed)
      subCat.rules = rules
      subs[subIndex] = subCat
      cat.sub_categories = subs
      cats[catIndex] = cat
      newDraft.main_categories = cats
      return { draft: newDraft }
    })
  },

  addCategory: () => {
    set((state) => {
      if (!state.draft) return state
      const newCategories = [...state.draft.main_categories]
      newCategories.push({
        id: generateId(),
        name: '新类别',
        priority: 'P2',
        is_active: true,
        sub_categories: [],
      })
      return { draft: { ...state.draft, main_categories: newCategories } }
    })
  },

  deleteCategory: (index: number) => {
    set((state) => {
      if (!state.draft) return state
      const newCategories = [...state.draft.main_categories]
      newCategories.splice(index, 1)
      return { draft: { ...state.draft, main_categories: newCategories } }
    })
  },

  addSubCategory: (catIndex: number) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      const cats = [...newDraft.main_categories]
      const cat = { ...cats[catIndex] }
      cat.sub_categories = [
        ...cat.sub_categories,
        { id: generateId(), name: '新子类别', priority: 'P2', rules: [] },
      ]
      cats[catIndex] = cat
      newDraft.main_categories = cats
      return { draft: newDraft }
    })
  },

  deleteSubCategory: (catIndex: number, subIndex: number) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      const cats = [...newDraft.main_categories]
      const cat = { ...cats[catIndex] }
      cat.sub_categories = [...cat.sub_categories]
      cat.sub_categories.splice(subIndex, 1)
      cats[catIndex] = cat
      newDraft.main_categories = cats
      return { draft: newDraft }
    })
  },

  addRule: (catIndex: number, subIndex: number) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      const cats = [...newDraft.main_categories]
      const cat = { ...cats[catIndex] }
      const subs = [...cat.sub_categories]
      const subCat = { ...subs[subIndex] }
      subCat.rules = [
        ...subCat.rules,
        { id: generateId(), name: '新规则', is_active: true, instruction: '', direction: '' },
      ]
      subs[subIndex] = subCat
      cat.sub_categories = subs
      cats[catIndex] = cat
      newDraft.main_categories = cats
      return { draft: newDraft }
    })
  },

  deleteRule: (catIndex: number, subIndex: number, ruleIndex: number) => {
    set((state) => {
      if (!state.draft) return state
      const newDraft = { ...state.draft }
      const cats = [...newDraft.main_categories]
      const cat = { ...cats[catIndex] }
      const subs = [...cat.sub_categories]
      const subCat = { ...subs[subIndex] }
      subCat.rules = [...subCat.rules]
      subCat.rules.splice(ruleIndex, 1)
      subs[subIndex] = subCat
      cat.sub_categories = subs
      cats[catIndex] = cat
      newDraft.main_categories = cats
      return { draft: newDraft }
    })
  },

  validatePriority: (priority: string, validPriorities: string[]) => {
    return validPriorities.includes(priority)
  },

  validateAllPriorities: (validPriorities: string[]) => {
    const { draft } = get()
    if (!draft) return false

    const errors: string[] = []

    const checkPriority = (priority: string, path: string) => {
      if (!validPriorities.includes(priority)) {
        errors.push(`未定义的优先级 "${priority}" (在 ${path})`)
      }
    }

    draft.main_categories.forEach((cat) => {
      checkPriority(cat.priority, `主类别 "${cat.name}"`)
      cat.sub_categories.forEach((sub) => {
        checkPriority(sub.priority, `子类别 "${sub.name}"`)
      })
    })

    set({ validationErrors: errors })
    return errors.length === 0
  },

  clearValidationErrors: () => {
    set({ validationErrors: [] })
  },
}))
