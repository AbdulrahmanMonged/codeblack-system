import { Card, Chip } from "@heroui/react";
import useSWR from "swr";
import { listPublicRoster } from "../../home/api/public-api.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { toArray } from "../../../shared/utils/collections.js";

export function PublicRosterPage() {
  const { data, isLoading, error } = useSWR(["public-roster"], () =>
    listPublicRoster({ limit: 300, offset: 0 }),
  );
  const rows = toArray(data);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <Chip color="warning" variant="flat">Public</Chip>
              <Chip variant="flat">Read-only roster</Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">CodeBlack Roster</h2>
          </div>
          <Chip variant="flat">{rows.length} members</Chip>
        </div>
      </Card>

      {isLoading ? (
        <Card className="border border-white/15 bg-black/45 p-4">
          <p className="text-sm text-white/75">Loading roster...</p>
        </Card>
      ) : null}

      {error ? (
        <Card className="border border-rose-300/25 bg-rose-300/10 p-4">
          <p className="text-sm text-rose-100">
            {extractApiErrorMessage(error, "Failed to load public roster")}
          </p>
        </Card>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2">
        {rows.map((row) => (
          <Card
            key={row.membership_id}
            className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-base font-semibold text-white">{row.ingame_name}</p>
              <Chip size="sm" variant="flat">{row.status}</Chip>
            </div>
            <p className="mt-1 text-sm text-white/70">@{row.account_name}</p>
            <p className="mt-2 text-xs text-white/65">
              Rank: {row.rank_name || "Unassigned"}
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
