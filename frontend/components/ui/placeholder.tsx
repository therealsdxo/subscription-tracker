import { PageHeader } from "@/components/ui/misc";

export function Placeholder({ title }: { title: string }) {
  return (
    <>
      <PageHeader title={title} />
      <div className="border-border-strong bg-surface text-text-muted rounded-[var(--radius)] border border-dashed px-6 py-12 text-center text-sm">
        This screen is not built yet — it follows the Customers list pattern.
      </div>
    </>
  );
}
