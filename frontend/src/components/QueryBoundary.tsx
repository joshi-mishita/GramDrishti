import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { FileQuestion } from "lucide-react";
import { useTranslation } from "react-i18next";
import { isApiError } from "../api/errors";
import { formatDate } from "../lib/format";
import { useAppStore } from "../state/store";
import { EmptyState, ErrorState, Skeleton } from "./states";

interface Props<T> {
  query: UseQueryResult<T, Error>;
  /** What is being loaded, as a noun phrase for messages: "the priority list". */
  what: string;
  /** Returns true when the data is valid but has nothing to show. */
  isEmpty?: (data: T) => boolean;
  /** Rendered when isEmpty returns true. */
  empty?: ReactNode;
  skeletonLines?: number;
  children: (data: T) => ReactNode;
}

/**
 * Renders the loading, error and empty states of one query the same way on every
 * screen (Guide 9.1). A request with no demo file is shown as an empty state that names
 * the dates that do have files, not as a failure.
 */
export function QueryBoundary<T>({
  query,
  what,
  isEmpty,
  empty,
  skeletonLines = 3,
  children,
}: Props<T>) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);

  if (query.isPending) {
    return <Skeleton lines={skeletonLines} label={t("states.loading", { what })} />;
  }

  if (query.isError) {
    const err = query.error;
    if (isApiError(err) && err.code === "not_in_mock") {
      const dates = err.mockDates.map((d) => formatDate(d, lang)).join(", ");
      return (
        <EmptyState icon={FileQuestion} title={t("states.notInMock", { what })}>
          <p>{dates ? t("states.notInMockDates", { dates }) : t("states.notInMockNoDates")}</p>
        </EmptyState>
      );
    }
    const detail = isApiError(err)
      ? err.status
        ? `${err.status} ${err.code}: ${err.message}`
        : err.message
      : err.message;
    return (
      <ErrorState
        message={t("states.error", { what })}
        detail={detail}
        onRetry={() => void query.refetch()}
        retrying={query.isFetching}
      />
    );
  }

  if (isEmpty?.(query.data)) return <>{empty}</>;
  return <>{children(query.data)}</>;
}
