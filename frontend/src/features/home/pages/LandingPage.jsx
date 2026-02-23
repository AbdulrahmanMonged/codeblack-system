import { Button, Card, Chip, Separator, Spinner } from "@heroui/react";
import dayjs from "dayjs";
import { ArrowRight, CalendarDays, FileText, Link2, ScrollText, ShieldAlert } from "lucide-react";
import { Icon } from "@iconify/react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectSessionStatus } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { toArray } from "../../../shared/utils/collections.js";
import { createDiscordLogin } from "../../auth/api/auth-api.js";
import { getPublicMetrics, listPublicPosts } from "../api/public-api.js";

function MetricCard({ label, value }) {
  return (
    <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
      <p className="text-xs uppercase tracking-[0.16em] text-white/60">{label}</p>
      <p className="cb-feature-title mt-2 text-4xl">{value}</p>
    </Card>
  );
}

export function LandingPage() {
  const navigate = useNavigate();
  const sessionStatus = useAppSelector(selectSessionStatus);
  const isAuthenticated = sessionStatus === "authenticated";
  const [isSignInRedirecting, setIsSignInRedirecting] = useState(false);

  const { data: metrics, error: metricsError } = useSWR(["public-metrics"], () => getPublicMetrics());
  const { data: posts, error: postsError } = useSWR(["public-posts"], () =>
    listPublicPosts({ limit: 6, offset: 0 }),
  );

  const postRows = toArray(posts);

  async function handleSignIn() {
    setIsSignInRedirecting(true);
    try {
      const payload = await createDiscordLogin({ nextUrl: "/dashboard" });
      if (!payload?.authorize_url) {
        throw new Error("Missing Discord authorize URL");
      }
      window.location.assign(payload.authorize_url);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to start Discord sign-in"));
      setIsSignInRedirecting(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5">
      <Card className="cb-feature-card border border-white/15 bg-black/55 shadow-2xl backdrop-blur-xl">
        <Card.Header className="space-y-3 p-7">
          <div className="flex flex-wrap items-center gap-2">
            <Chip color="warning" variant="flat">
              CodeBlack Portal
            </Chip>
            <Chip variant="flat">Public modules + protected operations</Chip>
          </div>
          <Card.Title className="cb-feature-title text-4xl md:text-5xl">
            Operations And Recruitment Center
          </Card.Title>
          <Card.Description className="max-w-3xl text-sm text-white/80 md:text-base">
            Public visitors can read roster, posts, and metrics. Protected actions require Discord
            authentication and backend role permissions.
          </Card.Description>
        </Card.Header>
        <Card.Content className="space-y-4 px-7 pb-7">
          <div className="flex flex-wrap items-center gap-3">
            {isAuthenticated ? (
              <Button
                color="warning"
                endContent={<ArrowRight size={14} />}
                onPress={() => navigate("/dashboard")}
              >
                Open Dashboard
              </Button>
            ) : (
              <Button
                color="warning"
                onPress={handleSignIn}
                isPending={isSignInRedirecting}
                isDisabled={isSignInRedirecting}
              >
                {({ isPending }) => (
                  <>
                    {isPending ? (
                      <Spinner color="current" size="sm" />
                    ) : (
                      <Icon icon="ri:discord-fill" width="16" height="16" />
                    )}
                    <span>Continue With Discord</span>
                    {!isPending ? <ArrowRight size={14} /> : null}
                  </>
                )}
              </Button>
            )}
            <Button
              variant="ghost"
              startContent={<FileText size={15} />}
              onPress={() => navigate("/applications/new")}
            >
              Submit Application
            </Button>
            <Button variant="ghost" onPress={() => navigate("/roster-public")}>
              View Public Roster
            </Button>
          </div>
        </Card.Content>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Members" value={metrics?.members_count ?? "-"} />
        <MetricCard label="Current Level" value={metrics?.current_level ?? "-"} />
        <MetricCard label="Online Players" value={metrics?.online_players ?? "-"} />
      </div>

      {metricsError ? (
        <Card className="border border-rose-300/25 bg-rose-300/10 p-4">
          <p className="text-sm text-rose-100">
            {extractApiErrorMessage(metricsError, "Failed to load public metrics")}
          </p>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
          <div className="mb-2 flex items-center gap-2">
            <ScrollText size={15} className="text-amber-200" />
            <p className="cb-title text-xl">Recruitment</p>
          </div>
          <p className="text-sm text-white/75">
            Start with eligibility, then complete the guided 5-step application flow.
          </p>
          <Button
            className="mt-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-amber-300/25 data-[hovered=true]:bg-amber-300/30"
            variant="flat"
            color="warning"
            onPress={() => navigate("/applications/new")}
          >
            Open Application Wizard
          </Button>
        </Card>

        <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
          <div className="mb-2 flex items-center gap-2">
            <ShieldAlert size={15} className="text-amber-200" />
            <p className="cb-title text-xl">Blacklist Removal</p>
          </div>
          <p className="text-sm text-white/75">
            Use the two-step removal request flow: pre-check then reason submission.
          </p>
          <Button
            className="mt-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-amber-300/25 data-[hovered=true]:bg-amber-300/30"
            variant="flat"
            color="warning"
            onPress={() => navigate("/blacklist/removal-request")}
          >
            Open Removal Request
          </Button>
        </Card>
      </div>

      <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
        <p className="cb-title text-2xl">Latest Posts</p>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {postRows.map((post) => (
            <Card key={post.public_id} className="border border-white/10 bg-white/5 p-4">
              <div className="flex items-start justify-between gap-2">
                <p className="text-base font-semibold text-white">{post.title}</p>
                <Chip size="sm" variant="flat">
                  Published
                </Chip>
              </div>

              <Separator className="my-3 bg-white/15" />

              <p className="line-clamp-4 text-sm text-white/75">{post.content}</p>

              {post.media_url ? (
                <>
                  <Separator className="my-3 bg-white/15" />
                  <img
                    src={post.media_url}
                    alt={`${post.title} attachment`}
                    className="h-44 w-full rounded-xl border border-white/15 object-cover"
                    loading="lazy"
                  />
                </>
              ) : null}

              <Separator className="my-3 bg-white/15" />

              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-white/60">
                <span className="inline-flex items-center gap-1.5">
                  <CalendarDays size={12} />
                  {dayjs(post.published_at || post.updated_at).format("YYYY-MM-DD HH:mm")}
                </span>
                <Separator orientation="vertical" className="h-4 bg-white/20" />
                <span className="inline-flex items-center gap-1.5">
                  <Link2 size={12} />
                  {post.public_id}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  onPress={() => navigate(`/posts/${post.public_id}`)}
                >
                  Read Post
                </Button>
              </div>
            </Card>
          ))}
          {!postRows.length ? (
            <Card className="border border-white/10 bg-white/5 p-4 text-sm text-white/70">
              No public posts published yet.
            </Card>
          ) : null}
        </div>
      </Card>

      {postsError ? (
        <Card className="border border-rose-300/25 bg-rose-300/10 p-4">
          <p className="text-sm text-rose-100">
            {extractApiErrorMessage(postsError, "Failed to load public posts")}
          </p>
        </Card>
      ) : null}
    </div>
  );
}
