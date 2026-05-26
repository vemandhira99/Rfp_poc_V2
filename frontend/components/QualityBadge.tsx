import { StatusBadge } from "./StatusBadge";

export function QualityBadge({ value }: { value: string }) {
  return <StatusBadge value={value} />;
}
