import { Button, Chip } from "@heroui/react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { FormSelect } from "./FormControls.jsx";

const DEFAULT_PAGE_SIZE_OPTIONS = [10, 20, 30, 50];

export function ListPaginationBar({
  page,
  pageSize,
  onPageChange,
  onPageSizeChange,
  hasNextPage,
  isLoading = false,
  visibleCount = 0,
  totalCount = null,
  className = "",
  pageSizeOptions = DEFAULT_PAGE_SIZE_OPTIONS,
}) {
  const safePage = Number.isFinite(Number(page)) && Number(page) > 0 ? Number(page) : 1;
  const safePageSize =
    Number.isFinite(Number(pageSize)) && Number(pageSize) > 0 ? Number(pageSize) : 20;

  const from = visibleCount > 0 ? (safePage - 1) * safePageSize + 1 : 0;
  const to = visibleCount > 0 ? (safePage - 1) * safePageSize + visibleCount : 0;
  const hasTotal = Number.isFinite(Number(totalCount)) && Number(totalCount) >= 0;
  const rangeLabel = hasTotal ? `${from}-${to} of ${Number(totalCount)}` : `${from}-${to}`;

  const canPrevious = safePage > 1 && !isLoading;
  const canNext = Boolean(hasNextPage) && !isLoading;

  return (
    <div
      className={[
        "mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-black/30 px-3 py-2",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="flex items-center gap-2">
        <Chip size="sm" variant="flat">
          Page {safePage}
        </Chip>
        <span className="text-xs text-white/65">Showing {rangeLabel}</span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <FormSelect
          fieldClassName="min-w-[120px]"
          label="Rows"
          value={String(safePageSize)}
          onChange={(event) => {
            const nextSize = Number(event?.target?.value || safePageSize);
            if (Number.isFinite(nextSize) && nextSize > 0) {
              onPageSizeChange?.(nextSize);
            }
          }}
        >
          {pageSizeOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </FormSelect>
        <Button
          size="sm"
          variant="ghost"
          startContent={<ChevronLeft size={14} />}
          isDisabled={!canPrevious}
          onPress={() => onPageChange?.(Math.max(1, safePage - 1))}
        >
          Prev
        </Button>
        <Button
          size="sm"
          variant="ghost"
          endContent={<ChevronRight size={14} />}
          isDisabled={!canNext}
          onPress={() => onPageChange?.(safePage + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
