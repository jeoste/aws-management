import { useState, useImperativeHandle, forwardRef, useEffect } from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

export interface DiagramCheckboxListProps {
  items: Array<{ arn: string; name: string }>
  type: 'topics' | 'queues'
  onSelectionChange: () => void
}

export interface DiagramCheckboxListRef {
  selectAll: () => void
  deselectAll: () => void
  getSelectedArns: () => string[]
}

const DiagramCheckboxList = forwardRef<DiagramCheckboxListRef, DiagramCheckboxListProps>(
  ({ items, type, onSelectionChange }, ref) => {
    const [selectedArns, setSelectedArns] = useState<Set<string>>(new Set())

    // Clear selection when items become empty (e.g., after clearing scan)
    useEffect(() => {
      if (items.length === 0) {
        setSelectedArns(new Set())
      }
    }, [items.length])

    useImperativeHandle(ref, () => ({
      selectAll: () => {
        setSelectedArns(new Set(items.map(item => item.arn)))
        // Trigger update after state change
        setTimeout(() => onSelectionChange(), 0)
      },
      deselectAll: () => {
        setSelectedArns(new Set())
        // Trigger update after state change
        setTimeout(() => onSelectionChange(), 0)
      },
      getSelectedArns: () => Array.from(selectedArns)
    }))

    const handleCheckboxChange = (arn: string, checked: boolean) => {
      const newSelected = new Set(selectedArns)
      if (checked) {
        newSelected.add(arn)
      } else {
        newSelected.delete(arn)
      }
      setSelectedArns(newSelected)
      // Trigger update after state change
      setTimeout(() => onSelectionChange(), 0)
    }

    if (items.length === 0) {
      return (
        <div className="text-xs text-muted-foreground">Scan resources first</div>
      )
    }

    return (
      <div className="space-y-1">
        {items.map((item) => (
          <label
            key={item.arn}
            htmlFor={`checkbox-${type}-${item.arn}`}
            className="flex items-center gap-2 px-2 py-1 rounded hover:bg-muted cursor-pointer transition-colors"
          >
            <Checkbox
              id={`checkbox-${type}-${item.arn}`}
              checked={selectedArns.has(item.arn)}
              onCheckedChange={(checked) => handleCheckboxChange(item.arn, checked as boolean)}
            />
            <Label
              htmlFor={`checkbox-${type}-${item.arn}`}
              className="text-sm cursor-pointer"
            >
              {item.name}
            </Label>
          </label>
        ))}
      </div>
    )
  }
)

DiagramCheckboxList.displayName = 'DiagramCheckboxList'

export default DiagramCheckboxList

