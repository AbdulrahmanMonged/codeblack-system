import { Button, Card, Chip } from "@heroui/react";
import { FormInput, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import dayjs from "dayjs";
import { Check, PencilLine, Plus, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { toArray } from "../../../shared/utils/collections.js";
import { createPost, listPosts, publishPost, updatePost } from "../api/posts-api.js";

export function PostsManagementPage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);
  const canRead = hasPermissionSet(["posts.read"], permissions, isOwner);
  const canWrite = hasPermissionSet(["posts.write"], permissions, isOwner);
  const canPublish = hasPermissionSet(["posts.publish"], permissions, isOwner);
  const canAccess = hasAnyPermissionSet(["posts.read", "posts.write", "posts.publish"], permissions, isOwner);

  const [selectedPublicId, setSelectedPublicId] = useState("");
  const [editingTitle, setEditingTitle] = useState("");
  const [editingContent, setEditingContent] = useState("");
  const [editingMediaUrl, setEditingMediaUrl] = useState("");

  const { data, mutate, isLoading, error } = useSWR(
    canRead ? ["dashboard-posts-list"] : null,
    () => listPosts({ publishedOnly: false, limit: 100, offset: 0 }),
  );

  const rows = useMemo(() => toArray(data), [data]);
  const selected = useMemo(
    () => rows.find((item) => item.public_id === selectedPublicId) || null,
    [rows, selectedPublicId],
  );

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Posts Access Restricted"
        description="You need posts.read/posts.write/posts.publish permissions to access this section."
      />
    );
  }

  async function handleCreate(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      title: String(form.get("title") || "").trim(),
      content: String(form.get("content") || "").trim(),
      media_url: String(form.get("mediaUrl") || "").trim() || null,
    };
    if (!payload.title || !payload.content) {
      toast.error("Title and content are required.");
      return;
    }
    try {
      const created = await createPost(payload);
      toast.success(`Post created: ${created.public_id}`);
      formElement?.reset?.();
      await mutate();
      setSelectedPublicId(created.public_id);
      setEditingTitle(created.title);
      setEditingContent(created.content);
      setEditingMediaUrl(created.media_url || "");
    } catch (submitError) {
      toast.error(extractApiErrorMessage(submitError, "Failed to create post"));
    }
  }

  async function handleSaveEdits() {
    if (!selectedPublicId) {
      toast.error("Select a post first.");
      return;
    }
    try {
      await updatePost(selectedPublicId, {
        title: editingTitle.trim(),
        content: editingContent.trim(),
        media_url: editingMediaUrl.trim() || null,
      });
      toast.success("Post updated");
      await mutate();
    } catch (updateError) {
      toast.error(extractApiErrorMessage(updateError, "Failed to update post"));
    }
  }

  async function handlePublishToggle(target) {
    if (!selectedPublicId) {
      toast.error("Select a post first.");
      return;
    }
    try {
      await publishPost(selectedPublicId, target);
      toast.success(target ? "Post published" : "Post unpublished");
      await mutate();
    } catch (publishError) {
      toast.error(extractApiErrorMessage(publishError, "Failed to change publish state"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Chip color="warning" variant="flat">Landing</Chip>
              <Chip variant="flat">Public posts management</Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Posts</h2>
          </div>
          <Button variant="ghost" startContent={<RefreshCw size={15} />} onPress={() => mutate()}>
            Refresh
          </Button>
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.1fr_1fr]">
        <section className="space-y-4">
          {canRead ? (
            <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
              <div className="mb-2 flex items-center justify-between px-2 py-1">
                <p className="text-sm text-white/70">
                  Posts: <span className="font-semibold text-white">{rows.length}</span>
                </p>
                {isLoading ? <p className="text-xs text-white/55">Loading...</p> : null}
              </div>
              <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
                {rows.map((row) => (
                  <button
                    key={row.public_id}
                    type="button"
                    onClick={() => {
                      setSelectedPublicId(row.public_id);
                      setEditingTitle(row.title || "");
                      setEditingContent(row.content || "");
                      setEditingMediaUrl(row.media_url || "");
                    }}
                    className={[
                      "w-full rounded-xl border p-3 text-left transition",
                      row.public_id === selectedPublicId
                        ? "border-amber-300/45 bg-amber-300/15"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                    ].join(" ")}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-white">{row.title}</p>
                      <Chip size="sm" variant="flat" color={row.is_published ? "success" : "warning"}>
                        {row.is_published ? "published" : "draft"}
                      </Chip>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-white/70">{row.content}</p>
                    <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
                      {row.public_id} · {dayjs(row.updated_at).format("YYYY-MM-DD HH:mm")}
                    </p>
                  </button>
                ))}
              </div>
            </Card>
          ) : null}
          {error ? (
            <Card className="border border-rose-300/25 bg-rose-300/10 p-3">
              <p className="text-sm text-rose-100">
                {extractApiErrorMessage(error, "Failed to load posts")}
              </p>
            </Card>
          ) : null}
        </section>

        <section className="space-y-4">
          {canWrite ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Create Post</p>
              <form className="space-y-3" onSubmit={handleCreate}>
                <FormInput
                  name="title"
                  placeholder="Post title"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormTextarea
                  name="content"
                  rows={4}
                  placeholder="Post content"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="mediaUrl"
                  placeholder="Media URL (optional)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button type="submit" color="warning" startContent={<Plus size={14} />}>
                  Create
                </Button>
              </form>
            </Card>
          ) : null}

          {selected ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="cb-title text-xl">Edit {selected.public_id}</p>
                <Chip variant="flat" color={selected.is_published ? "success" : "warning"}>
                  {selected.is_published ? "published" : "draft"}
                </Chip>
              </div>
              {canWrite ? (
                <div className="space-y-3">
                  <FormInput
                    value={editingTitle}
                    onChange={(event) => setEditingTitle(event.target.value)}
                    placeholder="Title"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                  <FormTextarea
                    rows={5}
                    value={editingContent}
                    onChange={(event) => setEditingContent(event.target.value)}
                    placeholder="Content"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                  <FormInput
                    value={editingMediaUrl}
                    onChange={(event) => setEditingMediaUrl(event.target.value)}
                    placeholder="Media URL"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                  <Button color="warning" variant="flat" startContent={<PencilLine size={14} />} onPress={handleSaveEdits}>
                    Save
                  </Button>
                </div>
              ) : null}

              {canPublish ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    color="success"
                    variant="flat"
                    startContent={<Check size={14} />}
                    onPress={() => handlePublishToggle(true)}
                  >
                    Publish
                  </Button>
                  <Button variant="ghost" onPress={() => handlePublishToggle(false)}>
                    Unpublish
                  </Button>
                </div>
              ) : null}
            </Card>
          ) : null}
        </section>
      </div>
    </div>
  );
}
