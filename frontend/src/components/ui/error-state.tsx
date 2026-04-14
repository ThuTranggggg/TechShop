export function ErrorState({ message }: { message: string }) {
  return <div className="rounded-2xl border border-danger/30 bg-red-50 px-4 py-3 text-sm text-red-700">{message}</div>;
}
