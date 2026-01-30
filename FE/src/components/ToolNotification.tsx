export default function ToolNotification({ status }: { status: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-1.5 text-sm text-[#06b6d4] bg-[#06b6d4]/10 border border-[#06b6d4]/30 rounded-lg animate-pulse">
      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
      </svg>
      {status}
    </div>
  );
}
