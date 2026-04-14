export function LoadingSkeletons({ lines = 3 }: { lines?: number }) {
  return <div className="space-y-2">{Array.from({ length: lines }).map((_, index) => <div key={index} className="relative h-4 overflow-hidden rounded bg-slate-200"><span className="absolute inset-y-0 left-0 w-1/2 -translate-x-full bg-gradient-to-r from-transparent via-white/70 to-transparent animate-shimmer" /></div>)}</div>;
}
