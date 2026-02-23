import { Button, Card, Chip, Separator, Spinner } from "@heroui/react";
import dayjs from "dayjs";
import { Check, ImagePlus, PencilLine, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { DashboardSearchField } from "../../../shared/ui/DashboardSearchField.jsx";
import { FormInput, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
import { ListPaginationBar } from "../../../shared/ui/ListPaginationBar.jsx";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { toast } from "../../../shared/ui/toast.jsx";
import { toArray } from "../../../shared/utils/collections.js";
import { includesSearchQuery } from "../../../shared/utils/search.js";
import {
  createPost,
  listPosts,
  publishPost,
  updatePost,
  uploadPostMedia,
} from "../api/posts-api.js";

export function PostsManagementPage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);
  const canRead = hasPermissionSet(["posts.read"], permissions, isOwner);
  const canWrite = hasPermissionSet(["posts.write"], permissions, isOwner);
  const canPublish = hasPermissionSet(["posts.publish"], permissions, isOwner);
  const canAccess = hasAnyPermissionSet(["posts.read", "posts.write", "posts.publish"], permissions, isOwner);

  const [selectedPublicId, setSelectedPublicId] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const [editingTitle, setEditingTitle] = useState("");
  const [editingContent, setEditingContent] = useState("");
  const [editingMediaUrl, setEditingMediaUrl] = useState("");
  const [editingAttachmentFile, setEditingAttachmentFile] = useState(null);

  const [createAttachmentName, setCreateAttachmentName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);

  const { data, mutate, isLoading, error } = useSWR(
    canRead ? ["dashboard-posts-list", page, pageSize] : null,
    () =>
      listPosts({
        publishedOnly: false,
        limit: pageSize + 1,
        offset: (page - 1) * pageSize,
      }),
  );

  const rows = useMemo(() => toArray(data), [data]);
  const pageRows = useMemo(() => rows.slice(0, pageSize), [rows, pageSize]);
  const hasNextPage = rows.length > pageSize;
  const filteredRows = useMemo(
    () =>
      pageRows.filter((row) =>
        includesSearchQuery(row, searchQuery, ["public_id", "title", "content", "is_published"]),
      ),
    [pageRows, searchQuery],
  );

  const selected = useMemo(
    () => pageRows.find((item) => item.public_id === selectedPublicId) || null,
    [pageRows, selectedPublicId],
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

    const title = String(form.get("title") || "").trim();
    const content = String(form.get("content") || "").trim();
    const attachment = form.get("attachment");

    if (!title || !content) {
      toast.error("Title and content are required.");
      return;
    }

    setIsCreating(true);
    try {
      let mediaUrl = null;
      if (typeof File !== "undefined" && attachment instanceof File && attachment.size > 0) {
        const uploaded = await uploadPostMedia(attachment);
        mediaUrl = uploaded.media_url;
      }

      const created = await createPost({
        title,
        content,
        media_url: mediaUrl,
      });

      toast.success(`Post created: ${created.public_id}`);
      formElement?.reset?.();
      setCreateAttachmentName("");
      await mutate();

      setSelectedPublicId(created.public_id);
      setEditingTitle(created.title || "");
      setEditingContent(created.content || "");
      setEditingMediaUrl(created.media_url || "");
      setEditingAttachmentFile(null);
    } catch (submitError) {
      toast.error(extractApiErrorMessage(submitError, "Failed to create post"));
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSaveEdits() {
    if (!selectedPublicId) {
      toast.error("Select a post first.");
      return;
    }

    setIsSaving(true);
    try {
      let nextMediaUrl = editingMediaUrl.trim() || null;
      if (typeof File !== "undefined" && editingAttachmentFile instanceof File && editingAttachmentFile.size > 0) {
        const uploaded = await uploadPostMedia(editingAttachmentFile);
        nextMediaUrl = uploaded.media_url;
      }

      const updated = await updatePost(selectedPublicId, {
        title: editingTitle.trim(),
        content: editingContent.trim(),
        media_url: nextMediaUrl,
      });

      toast.success("Post updated");
      await mutate();

      setEditingMediaUrl(updated.media_url || "");
      setEditingAttachmentFile(null);
    } catch (updateError) {
      toast.error(extractApiErrorMessage(updateError, "Failed to update post"));
    } finally {
      setIsSaving(false);
    }
  }

  async function handlePublishToggle(target) {
    if (!selectedPublicId) {
      toast.error("Select a post first.");
      return;
    }

    setIsPublishing(true);
    try {
      await publishPost(selectedPublicId, target);
      toast.success(target ? "Post published" : "Post unpublished");
      await mutate();
    } catch (publishError) {
      toast.error(extractApiErrorMessage(publishError, "Failed to change publish state"));
    } finally {
      setIsPublishing(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Chip color="warning" variant="flat">
                Landing
              </Chip>
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
                  Posts: <span className="font-semibold text-white">{filteredRows.length}</span>
                </p>
                {isLoading ? <p className="text-xs text-white/55">Loading...</p> : null}
              </div>
              <div className="mb-3">
                <DashboardSearchField
                  label="Search Posts"
                  description="Search by post ID, title, content, and status."
                  placeholder="Search posts..."
                  value={searchQuery}
                  onChange={setSearchQuery}
                  className="w-full"
                  inputClassName="w-full"
                />
              </div>
              <ListPaginationBar
                page={page}
                pageSize={pageSize}
                onPageChange={setPage}
                onPageSizeChange={(nextPageSize) => {
                  setPageSize(nextPageSize);
                  setPage(1);
                }}
                hasNextPage={hasNextPage}
                isLoading={isLoading}
                visibleCount={filteredRows.length}
              />
              <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
                {filteredRows.map((row) => (
                  <button
                    key={row.public_id}
                    type="button"
                    onClick={() => {
                      setSelectedPublicId(row.public_id);
                      setEditingTitle(row.title || "");
                      setEditingContent(row.content || "");
                      setEditingMediaUrl(row.media_url || "");
                      setEditingAttachmentFile(null);
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
                    {row.media_url ? (
                      <img
                        src={row.media_url}
                        alt={`${row.title} attachment`}
                        className="mt-2 h-24 w-full rounded-lg border border-white/10 object-cover"
                        loading="lazy"
                      />
                    ) : null}
                    <p className="mt-2 text-[11px] uppercase tracking-[0.16em] text-white/45">
                      {row.public_id} · {dayjs(row.updated_at).format("YYYY-MM-DD HH:mm")}
                    </p>
                  </button>
                ))}
              </div>
              {!isLoading && filteredRows.length === 0 ? (
                <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                  No posts matched the current search query.
                </div>
              ) : null}
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
              <FormSectionDisclosure title="Create Post">
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
                    name="attachment"
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    label="Attachment"
                    description="Upload image/gif attachment. It will be pushed to CDN via backend."
                    onChange={(event) => setCreateAttachmentName(event?.target?.files?.[0]?.name || "")}
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                  {createAttachmentName ? (
                    <p className="text-xs text-emerald-300">Selected: {createAttachmentName}</p>
                  ) : null}
                  <Button type="submit" color="warning" isDisabled={isCreating} isPending={isCreating}>
                    {({ isPending }) => (
                      <>
                        {isPending ? <Spinner color="current" size="sm" /> : <Plus size={14} />}
                        {isPending ? "Creating..." : "Create"}
                      </>
                    )}
                  </Button>
                </form>
              </FormSectionDisclosure>
            </Card>
          ) : null}

          {selected ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <FormSectionDisclosure title={`Edit ${selected.public_id}`}>
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

                    {editingMediaUrl ? (
                      <img
                        src={editingMediaUrl}
                        alt={`${selected.title} attachment`}
                        className="h-44 w-full rounded-xl border border-white/15 object-cover"
                        loading="lazy"
                      />
                    ) : null}

                    <FormInput
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/gif"
                      label="Replace Attachment"
                      description="Uploading a new file replaces current attachment."
                      onChange={(event) =>
                        setEditingAttachmentFile(event?.target?.files?.[0] || null)
                      }
                      className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                    />

                    {editingAttachmentFile ? (
                      <p className="text-xs text-emerald-300">Selected: {editingAttachmentFile.name}</p>
                    ) : null}

                    {editingMediaUrl ? (
                      <Button
                        variant="ghost"
                        color="danger"
                        startContent={<Trash2 size={14} />}
                        onPress={() => {
                          setEditingMediaUrl("");
                          setEditingAttachmentFile(null);
                        }}
                      >
                        Remove Attachment
                      </Button>
                    ) : null}

                    <Button color="warning" variant="flat" isDisabled={isSaving} isPending={isSaving} onPress={handleSaveEdits}>
                      {({ isPending }) => (
                        <>
                          {isPending ? <Spinner color="current" size="sm" /> : <PencilLine size={14} />}
                          {isPending ? "Saving..." : "Save"}
                        </>
                      )}
                    </Button>
                  </div>
                ) : null}

                {canPublish ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      color="success"
                      variant="flat"
                      startContent={<Check size={14} />}
                      isDisabled={isPublishing}
                      isPending={isPublishing}
                      onPress={() => handlePublishToggle(true)}
                    >
                      {({ isPending }) => (
                        <>
                          {isPending ? <Spinner color="current" size="sm" /> : <ImagePlus size={14} />}
                          Publish
                        </>
                      )}
                    </Button>
                    <Separator orientation="vertical" className="h-5 bg-white/20" />
                    <Button
                      variant="ghost"
                      isDisabled={isPublishing}
                      isPending={isPublishing}
                      onPress={() => handlePublishToggle(false)}
                    >
                      {({ isPending }) => (
                        <>
                          {isPending ? <Spinner color="current" size="sm" /> : null}
                          Unpublish
                        </>
                      )}
                    </Button>
                  </div>
                ) : null}
              </FormSectionDisclosure>
            </Card>
          ) : null}
        </section>
      </div>
    </div>
  );
}
