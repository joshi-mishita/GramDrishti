import { CircleCheck, CircleDashed, CircleX, PencilLine } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Status } from "../../api/types";

const ICON = {
  draft: CircleDashed,
  approved: CircleCheck,
  edited: PencilLine,
  rejected: CircleX,
} as const;

/** Review status as icon plus word; neutral colours, so it never reads as a risk level. */
export function StatusChip({ status }: { status: Status }) {
  const { t } = useTranslation();
  const Icon = ICON[status];
  return (
    <span className={`status-chip status-${status}`}>
      <Icon size={14} aria-hidden="true" />
      {t(`statuses.${status}`)}
    </span>
  );
}
