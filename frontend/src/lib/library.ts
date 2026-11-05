import { CheckCircle2, Clock, Pause, Play, X } from "lucide-react";
import type { SearchItemType } from "@/types/search";
import type { LibraryStatus } from "@/types/library";

type IconComponent = typeof Clock;

type StatusMeta = {
  status: LibraryStatus;
  label: string;
  playableLabel?: string; // for "Граю" when media_type === "game"
  icon: IconComponent;
};

export const LIBRARY_STATUSES: readonly LibraryStatus[] = [
  "in_progress",
  "planned",
  "completed",
  "on_hold",
  "dropped",
] as const;

const META: Record<LibraryStatus, StatusMeta> = {
  in_progress: {
    status: "in_progress",
    label: "Дивлюсь",
    playableLabel: "Граю",
    icon: Play,
  },
  planned: { status: "planned", label: "У планах", icon: Clock },
  completed: { status: "completed", label: "Завершено", icon: CheckCircle2 },
  on_hold: { status: "on_hold", label: "На паузі", icon: Pause },
  dropped: { status: "dropped", label: "Закинуто", icon: X },
};

export function statusLabel(status: LibraryStatus, type?: SearchItemType): string {
  const meta = META[status];
  if (type === "game" && meta.playableLabel) return meta.playableLabel;
  return meta.label;
}

export function statusIcon(status: LibraryStatus): IconComponent {
  return META[status].icon;
}

export function tabLabel(status: LibraryStatus): string {
  const meta = META[status];
  if (!meta.playableLabel) return meta.label;
  return `${meta.label} / ${meta.playableLabel.toLowerCase()}`;
}
