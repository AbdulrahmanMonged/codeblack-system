import { Button, Card, Chip, Separator, Spinner } from "@heroui/react";
import dayjs from "dayjs";
import { ArrowLeft, CalendarDays, Link2 } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import useSWR from "swr";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { getPublicPost } from "../api/public-api.js";

export function PublicPostPage() {
  const navigate = useNavigate();
  const { postId } = useParams();

  const {
    data: post,
    error,
    isLoading,
    mutate,
  } = useSWR(postId ? ["public-post", postId] : null, () => getPublicPost(postId));

  return (
    <div className="mx-auto w-full max-w-4xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Public Post
              </Chip>
              {post?.is_published ? (
                <Chip variant="flat" color="success">
                  Published
                </Chip>
              ) : null}
            </div>
            <h1 className="cb-feature-title text-4xl">{post?.title || "Post"}</h1>
          </div>
          <Button variant="ghost" startContent={<ArrowLeft size={14} />} onPress={() => navigate("/")}>
            Back Home
          </Button>
        </div>
      </Card>

      {isLoading ? (
        <Card className="border border-white/15 bg-black/45 p-6 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center gap-2 text-white/80">
            <Spinner color="warning" size="sm" />
            Loading post...
          </div>
        </Card>
      ) : null}

      {error ? (
        <Card className="border border-rose-300/25 bg-rose-300/10 p-4">
          <p className="text-sm text-rose-100">
            {extractApiErrorMessage(error, "Failed to load post")}
          </p>
          <Button className="mt-3" variant="ghost" onPress={() => mutate()}>
            Retry
          </Button>
        </Card>
      ) : null}

      {post ? (
        <Card className="border border-white/15 bg-black/45 p-5 shadow-2xl backdrop-blur-xl">
          <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.14em] text-white/60">
            <span className="inline-flex items-center gap-1.5">
              <CalendarDays size={12} />
              {dayjs(post.published_at || post.updated_at).format("YYYY-MM-DD HH:mm")}
            </span>
            <Separator orientation="vertical" className="h-4 bg-white/20" />
            <span className="inline-flex items-center gap-1.5">
              <Link2 size={12} />
              {post.public_id}
            </span>
          </div>

          <Separator className="my-4 bg-white/15" />

          <article className="whitespace-pre-line text-sm leading-7 text-white/85">{post.content}</article>

          {post.media_url ? (
            <>
              <Separator className="my-4 bg-white/15" />
              <a href={post.media_url} target="_blank" rel="noreferrer" className="block">
                <img
                  src={post.media_url}
                  alt={`${post.title} attachment`}
                  className="h-64 w-full rounded-2xl border border-white/15 object-cover"
                  loading="lazy"
                />
              </a>
            </>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}
