import { FileText } from 'lucide-react'

export default function Reports() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-[hsl(215_20%_50%)]">
      <FileText className="w-12 h-12 opacity-30" />
      <div className="text-center">
        <p className="text-lg font-medium text-[hsl(215_20%_65%)]">Reports</p>
        <p className="text-sm mt-1">Export PDF reports and share analysis — Phase 5</p>
      </div>
    </div>
  )
}
