import { Clapperboard } from "lucide-react";

type Props = {
  size?: number;
  tone?: "dark" | "light";
};

export function Logo({ size = 20, tone = "dark" }: Props) {
  const colorClass = tone === "light" ? "text-accent-soft" : "text-accent";
  return (
    <span className={`inline-flex items-center justify-center ${colorClass}`}>
      <Clapperboard size={size} strokeWidth={1.8} />
    </span>
  );
}
