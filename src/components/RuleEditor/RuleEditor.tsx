import * as React from 'react'
import * as Switch from '@radix-ui/react-switch'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  ChevronDown,
  ChevronRight,
  GripVertical,
  Save,
  RotateCcw,
  AlertCircle,
  Trash2,
  Plus,
} from 'lucide-react'
import { useRuleStore, MainCategory, SubCategory, Rule } from '../../store/ruleStore'

const TreeNode: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <div className="pl-4 border-l border-border ml-2">{children}</div>
)

interface SortableItemProps {
  id: string
  children: React.ReactElement
  className?: string
}

const SortableItem: React.FC<SortableItemProps> = ({ id, children, className }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={style} className={className}>
      {React.cloneElement(children, { dragHandleProps: { ...attributes, ...listeners } })}
    </div>
  )
}

interface RuleItemProps {
  catIndex: number
  subIndex: number
  ruleIndex: number
  rule: Rule
  dragHandleProps?: Record<string, unknown>
}

const RuleItem: React.FC<RuleItemProps> = ({ catIndex, subIndex, ruleIndex, rule, dragHandleProps }) => {
  const { updateRule, deleteRule } = useRuleStore()

  return (
    <div className="bg-white border border-border rounded p-3 mb-2">
      <div className="flex items-center gap-2 mb-2">
        <div {...dragHandleProps} className="cursor-grab">
          <GripVertical className="w-4 h-4 text-muted-foreground" />
        </div>
        <input
          type="text"
          value={rule.name}
          onChange={(e) => updateRule(catIndex, subIndex, ruleIndex, { name: e.target.value })}
          className="flex-1 px-2 py-1 text-sm border border-border rounded hover:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder="规则名称"
        />
        <Switch.Root
          className="w-9 h-5 bg-border rounded-full relative data-[state=checked]:bg-primary cursor-pointer"
          checked={rule.is_active}
          onCheckedChange={(checked) => updateRule(catIndex, subIndex, ruleIndex, { is_active: checked })}
        >
          <Switch.Thumb className="block w-4 h-4 bg-white rounded-full transition-transform translate-x-0.5 data-[state=checked]:translate-x-4" />
        </Switch.Root>
        <button
          onClick={() => deleteRule(catIndex, subIndex, ruleIndex)}
          className="p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded"
          title="删除规则"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      <div className="mb-2">
        <label className="text-xs text-muted-foreground mb-1 block">审查方向</label>
        <input
          type="text"
          value={rule.direction || ''}
          onChange={(e) => updateRule(catIndex, subIndex, ruleIndex, { direction: e.target.value })}
          className="w-full px-2 py-1 text-sm border border-border rounded hover:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder="如：诊断并修改"
        />
      </div>
      <div>
        <label className="text-xs text-muted-foreground mb-1 block">精准修改指令</label>
        <textarea
          value={rule.instruction}
          onChange={(e) => updateRule(catIndex, subIndex, ruleIndex, { instruction: e.target.value })}
          className="w-full px-2 py-1 text-sm border border-border rounded hover:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary resize-y min-h-[60px]"
          placeholder="详细的修改指令..."
        />
      </div>
    </div>
  )
}

interface SubCategoryItemProps {
  catIndex: number
  subIndex: number
  subCategory: SubCategory
}

const SubCategoryItem: React.FC<SubCategoryItemProps> = ({ catIndex, subIndex, subCategory }) => {
  const [isExpanded, setIsExpanded] = React.useState(true)
  const { updateSubCategory, addRule, deleteSubCategory } = useRuleStore()
  const priorities = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5']

  const ruleIds = subCategory.rules.map((rule) => `rule-${catIndex}-${subIndex}-${rule.id}`)

  return (
    <div className="mb-2">
      <div
        className="flex items-center gap-2 p-2 bg-secondary/50 rounded cursor-pointer hover:bg-secondary"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        <GripVertical className="w-4 h-4 text-muted-foreground cursor-grab" />
        <input
          type="text"
          value={subCategory.name}
          onChange={(e) => {
            e.stopPropagation()
            updateSubCategory(catIndex, subIndex, { name: e.target.value })
          }}
          onClick={(e) => e.stopPropagation()}
          className="flex-1 px-2 py-1 text-sm bg-transparent border border-transparent rounded hover:border-border focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder="子类别名称"
        />
        <select
          value={subCategory.priority}
          onChange={(e) => {
            e.stopPropagation()
            updateSubCategory(catIndex, subIndex, { priority: e.target.value })
          }}
          onClick={(e) => e.stopPropagation()}
          className="px-2 py-1 text-sm border border-border rounded bg-white hover:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {priorities.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <button
          onClick={(e) => {
            e.stopPropagation()
            addRule(catIndex, subIndex)
          }}
          className="p-1 text-primary hover:bg-primary/10 rounded"
          title="添加规则"
        >
          <Plus className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            deleteSubCategory(catIndex, subIndex)
          }}
          className="p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded"
          title="删除子类别"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      {isExpanded && (
        <TreeNode>
          <SortableContext items={ruleIds} strategy={verticalListSortingStrategy}>
            {subCategory.rules.map((rule, ruleIdx) => (
              <SortableItem key={rule.id} id={`rule-${catIndex}-${subIndex}-${rule.id}`}>
                <RuleItem
                  catIndex={catIndex}
                  subIndex={subIndex}
                  ruleIndex={ruleIdx}
                  rule={rule}
                />
              </SortableItem>
            ))}
          </SortableContext>
        </TreeNode>
      )}
    </div>
  )
}

interface CategoryItemProps {
  index: number
  category: MainCategory
}

const CategoryItem: React.FC<CategoryItemProps> = ({ index, category }) => {
  const [isExpanded, setIsExpanded] = React.useState(true)
  const { updateCategory, addSubCategory, deleteCategory } = useRuleStore()
  const priorities = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5']

  const subIds = category.sub_categories.map((sub) => `sub-${index}-${sub.id}`)

  return (
    <div className="mb-4">
      <div
        className="flex items-center gap-2 p-3 bg-primary/10 rounded cursor-pointer hover:bg-primary/20 border border-primary/20"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? <ChevronDown className="w-5 h-5 text-primary" /> : <ChevronRight className="w-5 h-5 text-primary" />}
        <GripVertical className="w-5 h-5 text-primary cursor-grab" />
        <input
          type="text"
          value={category.name}
          onChange={(e) => {
            e.stopPropagation()
            updateCategory(index, { name: e.target.value })
          }}
          onClick={(e) => e.stopPropagation()}
          className="flex-1 px-3 py-1 text-sm font-medium bg-transparent border border-transparent rounded hover:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder="主类别名称"
        />
        <select
          value={category.priority}
          onChange={(e) => {
            e.stopPropagation()
            updateCategory(index, { priority: e.target.value })
          }}
          onClick={(e) => e.stopPropagation()}
          className="px-2 py-1 text-sm border border-border rounded bg-white hover:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary"
        >
          {priorities.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <Switch.Root
          className="w-9 h-5 bg-border rounded-full relative data-[state=checked]:bg-primary cursor-pointer"
          checked={category.is_active}
          onCheckedChange={(checked) => {
            updateCategory(index, { is_active: checked })
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <Switch.Thumb className="block w-4 h-4 bg-white rounded-full transition-transform translate-x-0.5 data-[state=checked]:translate-x-4" />
        </Switch.Root>
        <button
          onClick={(e) => {
            e.stopPropagation()
            addSubCategory(index)
          }}
          className="p-1 text-primary hover:bg-primary/10 rounded"
          title="添加子类别"
        >
          <Plus className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            deleteCategory(index)
          }}
          className="p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded"
          title="删除类别"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      {isExpanded && (
        <TreeNode>
          <SortableContext items={subIds} strategy={verticalListSortingStrategy}>
            {category.sub_categories.map((sub, subIdx) => (
              <SortableItem key={sub.id} id={`sub-${index}-${sub.id}`}>
                <SubCategoryItem
                  catIndex={index}
                  subIndex={subIdx}
                  subCategory={sub}
                />
              </SortableItem>
            ))}
          </SortableContext>
        </TreeNode>
      )}
    </div>
  )
}

export const RuleEditor: React.FC = () => {
  const {
    draft,
    isLoading,
    isSyncing,
    error,
    validationErrors,
    fetchRules,
    submitRules,
    revertRules,
    clearValidationErrors,
    moveCategory,
    moveSubCategory,
    moveRule,
  } = useRuleStore()

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const catIds = draft?.main_categories.map((cat) => `cat-${cat.id}`) || []

  React.useEffect(() => {
    fetchRules()
  }, [fetchRules])

  const handleSubmit = async () => {
    const success = await submitRules()
    if (success) {
      clearValidationErrors()
    }
  }

  /** Unified drag handler routing by ID prefix */
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id || !draft) return

    const activeId = active.id as string

    if (activeId.startsWith('cat-')) {
      const oldIndex = catIds.indexOf(activeId)
      const newIndex = catIds.indexOf(over.id as string)
      if (oldIndex >= 0 && newIndex >= 0) moveCategory(oldIndex, newIndex)
    } else if (activeId.startsWith('sub-')) {
      const parts = activeId.split('-')
      const catIndex = parseInt(parts[1], 10)
      const subIds = draft.main_categories[catIndex]?.sub_categories.map((s) => `sub-${catIndex}-${s.id}`) || []
      const oldIndex = subIds.indexOf(activeId)
      const newIndex = subIds.indexOf(over.id as string)
      if (oldIndex >= 0 && newIndex >= 0) moveSubCategory(catIndex, oldIndex, newIndex)
    } else if (activeId.startsWith('rule-')) {
      const parts = activeId.split('-')
      const catIndex = parseInt(parts[1], 10)
      const subIndex = parseInt(parts[2], 10)
      const ruleIds = draft.main_categories[catIndex]?.sub_categories[subIndex]?.rules.map((r) => `rule-${catIndex}-${subIndex}-${r.id}`) || []
      const oldIndex = ruleIds.indexOf(activeId)
      const newIndex = ruleIds.indexOf(over.id as string)
      if (oldIndex >= 0 && newIndex >= 0) moveRule(catIndex, subIndex, oldIndex, newIndex)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <span>加载规则配置中...</span>
      </div>
    )
  }

  if (error && !draft) {
    return (
      <div className="flex items-center justify-center h-full text-destructive">
        <span>加载失败: {error}</span>
      </div>
    )
  }

  if (!draft) {
    return null
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border bg-white">
        <h2 className="text-lg font-semibold">规则配置中心</h2>
        <div className="flex items-center gap-2">
          {isSyncing && <span className="text-sm text-primary">保存中...</span>}
          {validationErrors.length > 0 && (
            <span className="text-sm text-destructive flex items-center gap-1">
              <AlertCircle className="w-4 h-4" />
              {validationErrors.length} 个错误
            </span>
          )}
          <button
            onClick={() => useRuleStore.getState().addCategory()}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-primary hover:bg-primary/10 rounded transition-colors"
          >
            <Plus className="w-4 h-4" />
            添加类别
          </button>
          <button
            onClick={revertRules}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground hover:bg-secondary rounded transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            放弃更改
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSyncing || validationErrors.length > 0}
            className="flex items-center gap-1 px-4 py-1.5 text-sm text-white bg-primary hover:bg-primary/90 rounded transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            保存规则
          </button>
        </div>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <div className="mx-4 mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded">
          <div className="flex items-center gap-2 text-destructive font-medium mb-2">
            <AlertCircle className="w-4 h-4" />
            以下优先级未定义
          </div>
          <ul className="text-sm text-destructive/80 space-y-1">
            {validationErrors.map((err, idx) => (
              <li key={idx}>• {err}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Tree Editor — single DndContext for all three levels */}
      <div className="flex-1 overflow-y-auto p-4">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={catIds} strategy={verticalListSortingStrategy}>
            {draft.main_categories.map((category, idx) => (
              <SortableItem key={category.id} id={`cat-${category.id}`}>
                <CategoryItem index={idx} category={category} />
              </SortableItem>
            ))}
          </SortableContext>
        </DndContext>

        {draft.main_categories.length === 0 && (
          <div className="text-center text-muted-foreground py-8">
            <p>暂无规则配置</p>
            <p className="text-sm">点击上方按钮添加新类别</p>
          </div>
        )}
      </div>
    </div>
  )
}