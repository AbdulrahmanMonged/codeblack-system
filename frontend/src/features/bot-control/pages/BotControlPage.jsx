import { Button, Card, Chip } from "@heroui/react";
import {
  Activity,
  ListRestart,
  RefreshCw,
  Rocket,
  Save,
  ServerCog,
  ShieldAlert,
} from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { FormInput } from "../../../shared/ui/FormControls.jsx";
import { DashboardSearchField } from "../../../shared/ui/DashboardSearchField.jsx";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../../shared/ui/StateBlocks.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
import { ListPaginationBar } from "../../../shared/ui/ListPaginationBar.jsx";
import { toArray } from "../../../shared/utils/collections.js";
import { includesSearchQuery } from "../../../shared/utils/search.js";
import {
  getBotChannels,
  getBotFeatures,
  listBotDeadLetters,
  replayBotDeadLetter,
  triggerBotCopScoresRefresh,
  triggerBotForumSync,
  updateBotChannels,
  updateBotFeatures,
} from "../api/bot-control-api.js";

const CHANNEL_KEYS = [
  "live_scores_channel_id",
  "recruitment_review_channel_id",
  "orders_notification_channel_id",
  "error_report_channel_id",
];

const FEATURE_KEYS = [
  "watch_cop_live_scores",
  "irc_bridge",
  "group_chat_watcher",
  "activity_monitor",
];

export function BotControlPage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasPermissionSet(["bot.read_status"], permissions, isOwner);
  const canConfigureChannels = hasPermissionSet(
    ["bot.configure_channels"],
    permissions,
    isOwner,
  );
  const canToggleFeatures = hasPermissionSet(["bot.toggle_features"], permissions, isOwner);
  const canTriggerForumSync = hasPermissionSet(
    ["bot.trigger.forum_sync"],
    permissions,
    isOwner,
  );
  const canTriggerCopRefresh = hasPermissionSet(
    ["bot.trigger.cop_scores_refresh"],
    permissions,
    isOwner,
  );
  const canReplayDeadLetters = hasPermissionSet(
    ["bot.replay_dead_letter"],
    permissions,
    isOwner,
  );
  const canAccess = hasAnyPermissionSet(
    [
      "bot.read_status",
      "bot.configure_channels",
      "bot.toggle_features",
      "bot.trigger.forum_sync",
      "bot.trigger.cop_scores_refresh",
      "bot.replay_dead_letter",
    ],
    permissions,
    isOwner,
  );

  const [channelsDraft, setChannelsDraft] = useState({});
  const [featuresDraft, setFeaturesDraft] = useState({});
  const [dispatchLog, setDispatchLog] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [deadLetterPage, setDeadLetterPage] = useState(1);
  const [deadLetterPageSize, setDeadLetterPageSize] = useState(20);

  const {
    data: channelsData,
    error: channelsError,
    isLoading: channelsLoading,
    mutate: refreshChannels,
  } = useSWR(canRead ? ["bot-channels"] : null, () => getBotChannels());
  const {
    data: featuresData,
    error: featuresError,
    isLoading: featuresLoading,
    mutate: refreshFeatures,
  } = useSWR(canRead ? ["bot-features"] : null, () => getBotFeatures());
  const {
    data: deadLetters,
    error: deadLettersError,
    isLoading: deadLettersLoading,
    mutate: refreshDeadLetters,
  } = useSWR(
    canRead ? ["bot-dead-letters", deadLetterPage, deadLetterPageSize] : null,
    () =>
      listBotDeadLetters({
        limit: deadLetterPageSize + 1,
        offset: (deadLetterPage - 1) * deadLetterPageSize,
      }),
  );

  const deadLetterRows = useMemo(() => toArray(deadLetters), [deadLetters]);
  const pageDeadLetterRows = useMemo(
    () => deadLetterRows.slice(0, deadLetterPageSize),
    [deadLetterRows, deadLetterPageSize],
  );
  const hasDeadLetterNextPage = deadLetterRows.length > deadLetterPageSize;
  const dispatchLogRows = useMemo(() => toArray(dispatchLog), [dispatchLog]);

  const filteredDeadLetterRows = useMemo(
    () =>
      pageDeadLetterRows.filter((entry) =>
        includesSearchQuery(entry, searchQuery, [
          "stream_id",
          "command_type",
          "attempt_count",
          "error",
        ]),
      ),
    [pageDeadLetterRows, searchQuery],
  );

  const filteredDispatchLogRows = useMemo(
    () =>
      dispatchLogRows.filter((entry) =>
        includesSearchQuery(entry, searchQuery, [
          "command_id",
          "command_type",
          "status",
          "message",
          "dead_letter_id",
        ]),
      ),
    [dispatchLogRows, searchQuery],
  );

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Bot Control Access Restricted"
        description="You need bot control permissions to access this page."
      />
    );
  }

  function resolveChannelDraftValue(key) {
    if (Object.prototype.hasOwnProperty.call(channelsDraft, key)) {
      return channelsDraft[key];
    }
    const value = channelsData?.[key];
    return value === null || value === undefined ? "" : String(value);
  }

  function resolveFeatureDraftValue(key) {
    if (Object.prototype.hasOwnProperty.call(featuresDraft, key)) {
      return Boolean(featuresDraft[key]);
    }
    return Boolean(featuresData?.[key]);
  }

  async function handleSaveChannels() {
    const payload = {};
    for (const key of CHANNEL_KEYS) {
      const raw = String(resolveChannelDraftValue(key) || "").trim();
      if (!raw) {
        payload[key] = null;
        continue;
      }
      const numericValue = Number(raw);
      if (!Number.isFinite(numericValue) || numericValue < 0) {
        toast.error(`Invalid channel id for ${key}`);
        return;
      }
      payload[key] = Math.trunc(numericValue);
    }
    try {
      const response = await updateBotChannels(payload);
      setDispatchLog(response.dispatch_results || []);
      setChannelsDraft({});
      toast.success("Channel configuration updated");
      await Promise.all([refreshChannels(), refreshDeadLetters()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to update channel config"));
    }
  }

  async function handleSaveFeatures() {
    const payload = {};
    FEATURE_KEYS.forEach((key) => {
      payload[key] = resolveFeatureDraftValue(key);
    });
    try {
      const response = await updateBotFeatures(payload);
      setDispatchLog(response.dispatch_results || []);
      setFeaturesDraft({});
      toast.success("Feature toggles updated");
      await Promise.all([refreshFeatures(), refreshDeadLetters()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to update feature toggles"));
    }
  }

  async function handleTriggerForumSync() {
    try {
      const response = await triggerBotForumSync();
      setDispatchLog([response, ...dispatchLog].slice(0, 12));
      toast.success("Forum sync trigger sent");
      await refreshDeadLetters();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to trigger forum sync"));
    }
  }

  async function handleTriggerCopRefresh() {
    try {
      const response = await triggerBotCopScoresRefresh();
      setDispatchLog([response, ...dispatchLog].slice(0, 12));
      toast.success("Cop scores refresh trigger sent");
      await refreshDeadLetters();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to trigger cop score refresh"));
    }
  }

  async function handleReplayDeadLetter(deadLetterId) {
    try {
      const response = await replayBotDeadLetter(deadLetterId);
      setDispatchLog([response, ...dispatchLog].slice(0, 12));
      toast.success(`Replay sent for dead letter ${deadLetterId}`);
      await refreshDeadLetters();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to replay dead letter"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Bot Control
              </Chip>
              <Chip variant="flat" startContent={<ServerCog size={13} />}>
                Channels + features + triggers
              </Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Bot Control</h2>
          </div>
          {canRead ? (
            <Button
              variant="ghost"
              startContent={<RefreshCw size={15} />}
              onPress={() =>
                Promise.all([refreshChannels(), refreshFeatures(), refreshDeadLetters()])
              }
            >
              Refresh
            </Button>
          ) : null}
        </div>
      </Card>

      <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
        <DashboardSearchField
          label="Search Bot Control"
          description="Search by command ID, stream ID, command type, status, or error message."
          placeholder="Search dispatch logs and dead letters..."
          value={searchQuery}
          onChange={setSearchQuery}
          className="w-full"
          inputClassName="w-full"
        />
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-4">
          {canRead ? (
            <>
              <FormSectionDisclosure title="Channel Routing">
                <p className="mb-3 cb-title text-xl">Channel Routing</p>
                {channelsLoading ? <LoadingBlock label="Loading channel configuration..." /> : null}
                <div className="space-y-3">
                  {CHANNEL_KEYS.map((key) => (
                    <div key={key} className="space-y-1">
                      <label className="text-xs uppercase tracking-[0.14em] text-white/55">{key}</label>
                      <FormInput
                        value={resolveChannelDraftValue(key)}
                        onChange={(event) =>
                          setChannelsDraft((previous) => ({
                            ...previous,
                            [key]: event?.target?.value || "",
                          }))
                        }
                        isDisabled={!canConfigureChannels}
                        placeholder="Discord channel id or blank"
                        className="w-full"
                      />
                    </div>
                  ))}
                </div>
                {canConfigureChannels ? (
                  <Button
                    className="mt-4"
                    color="warning"
                    startContent={<Save size={14} />}
                    onPress={handleSaveChannels}
                  >
                    Save Channel Config
                  </Button>
                ) : null}
            </FormSectionDisclosure>

              <FormSectionDisclosure title="Feature Toggles">
                <p className="mb-3 cb-title text-xl">Feature Toggles</p>
                {featuresLoading ? <LoadingBlock label="Loading feature toggles..." /> : null}
                <div className="space-y-2">
                  {FEATURE_KEYS.map((key) => (
                    <div
                      key={key}
                      className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/85"
                    >
                      <span>{key}</span>
                      <FormInput
                        type="checkbox"
                        checked={resolveFeatureDraftValue(key)}
                        disabled={!canToggleFeatures}
                        onChange={(event) =>
                          setFeaturesDraft((previous) => ({
                            ...previous,
                            [key]: Boolean(event?.target?.checked),
                          }))
                        }
                      />
                    </div>
                  ))}
                </div>
                {canToggleFeatures ? (
                  <Button
                    className="mt-4"
                    color="warning"
                    startContent={<Save size={14} />}
                    onPress={handleSaveFeatures}
                  >
                    Save Feature Toggles
                  </Button>
                ) : null}
            </FormSectionDisclosure>
            </>
          ) : (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>Bot status read access is missing.</p>
              </div>
            </Card>
          )}

          {channelsError ? (
            <ErrorBlock
              title="Failed to load channels config"
              description={extractApiErrorMessage(channelsError)}
              onRetry={() => refreshChannels()}
            />
          ) : null}
          {featuresError ? (
            <ErrorBlock
              title="Failed to load features config"
              description={extractApiErrorMessage(featuresError)}
              onRetry={() => refreshFeatures()}
            />
          ) : null}
        </section>

        <section className="space-y-4">
          {(canTriggerForumSync || canTriggerCopRefresh) ? (
            <FormSectionDisclosure title="Manual Triggers">
              <p className="mb-3 cb-title text-xl">Manual Triggers</p>
              <div className="flex flex-wrap gap-2">
                {canTriggerForumSync ? (
                  <Button
                    color="warning"
                    variant="flat"
                    startContent={<Rocket size={14} />}
                    onPress={handleTriggerForumSync}
                  >
                    Trigger Forum Sync
                  </Button>
                ) : null}
                {canTriggerCopRefresh ? (
                  <Button
                    color="warning"
                    variant="flat"
                    startContent={<Activity size={14} />}
                    onPress={handleTriggerCopRefresh}
                  >
                    Refresh Cop Scores
                  </Button>
                ) : null}
              </div>
            </FormSectionDisclosure>
          ) : null}

          {canRead ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="cb-title text-xl">Dead Letter Queue</p>
                <Chip variant="flat">{filteredDeadLetterRows.length}</Chip>
              </div>
              <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                {deadLettersLoading ? <LoadingBlock label="Loading dead letters..." /> : null}
                {filteredDeadLetterRows.map((entry) => (
                  <div
                    key={entry.stream_id}
                    className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80"
                  >
                    <p className="font-medium text-white">{entry.command_type}</p>
                    <p className="mt-1 text-xs text-white/60">
                      {entry.stream_id} · attempts {entry.attempt_count}
                    </p>
                    {entry.error ? <p className="mt-1 text-xs text-rose-200">{entry.error}</p> : null}
                    {canReplayDeadLetters ? (
                      <Button
                        className="mt-2"
                        size="sm"
                        variant="flat"
                        startContent={<ListRestart size={13} />}
                        onPress={() => handleReplayDeadLetter(entry.stream_id)}
                      >
                        Replay
                      </Button>
                    ) : null}
                  </div>
                ))}
                {!deadLettersLoading && filteredDeadLetterRows.length === 0 ? (
                  <EmptyBlock
                    title="Dead letter queue is empty"
                    description="No failed bot commands are waiting for replay."
                  />
                ) : null}
              </div>
              <div className="mt-3">
                <ListPaginationBar
                  page={deadLetterPage}
                  pageSize={deadLetterPageSize}
                  onPageChange={setDeadLetterPage}
                  onPageSizeChange={(nextPageSize) => {
                    setDeadLetterPageSize(nextPageSize);
                    setDeadLetterPage(1);
                  }}
                  hasNextPage={hasDeadLetterNextPage}
                  isLoading={deadLettersLoading}
                  visibleCount={filteredDeadLetterRows.length}
                />
              </div>
              {deadLettersError ? (
                <ErrorBlock
                  title="Failed to load dead letters"
                  description={extractApiErrorMessage(deadLettersError)}
                  onRetry={() => refreshDeadLetters()}
                />
              ) : null}
            </Card>
          ) : null}

          <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
            <p className="mb-3 cb-title text-xl">Dispatch Log</p>
            <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
              {filteredDispatchLogRows.map((entry, index) => (
                <pre
                  key={`${entry.command_id || entry.dead_letter_id || "log"}-${index}`}
                  className="overflow-x-auto rounded-xl border border-white/10 bg-white/5 p-3 text-[11px] text-white/75"
                >
                  {JSON.stringify(entry, null, 2)}
                </pre>
              ))}
              {filteredDispatchLogRows.length === 0 ? (
                <EmptyBlock
                  title="No dispatch operations yet"
                  description="Trigger or update actions will appear here with command responses."
                />
              ) : null}
            </div>
          </Card>
        </section>
      </div>
    </div>
  );
}
