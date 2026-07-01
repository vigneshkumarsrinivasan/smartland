import { ShieldCheck } from 'lucide-react'

export default function Admin() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-4 text-[hsl(215_20%_50%)]">
      <ShieldCheck className="w-12 h-12 opacity-30" />
      <div className="text-center">
        <p className="text-lg font-medium text-[hsl(215_20%_65%)]">Admin</p>
        <p className="text-sm mt-1">Platform configuration and user management — Phase 5</p>
      </div>
    </div>
  )
}
