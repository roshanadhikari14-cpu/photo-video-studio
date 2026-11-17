// Everything the reference page shows: the request, its latest status and the finished results, grouped
// into posts / stories / collages / videos / photos with titles and captions.
import { list } from "@vercel/blob";

const ID = /^[A-Za-z0-9]{12}$/;
const GROUPS = ["posts", "stories", "collages", "videos", "photos"];
const base = (p) => p.split("/").pop().replace(/-[A-Za-z0-9]{20,}(?=\.[^.]+$)/, "");

export default async function handler(req, res) {
  const id = String(req.query.id || "");
  if (!ID.test(id)) return res.status(400).json({ error: "Bad id" });
  const blobs = [];
  let cursor;
  do {
    const r = await list({ prefix: `requests/${id}/`, cursor, limit: 1000 });
    blobs.push(...r.blobs); cursor = r.hasMore ? r.cursor : undefined;
  } while (cursor);

  const reqBlob = blobs.find((b) => b.pathname === `requests/${id}/request.json`);
  if (!reqBlob) return res.status(404).json({ error: "Not found" });
  const request = await (await fetch(reqBlob.url, { cache: "no-store" })).json();

  const statuses = blobs.filter((b) => b.pathname.startsWith(`requests/${id}/status/`))
    .sort((a, b) => new Date(b.uploadedAt) - new Date(a.uploadedAt));
  let status = { status: "received", note: "" };
  if (statuses[0]) status = await (await fetch(statuses[0].url, { cache: "no-store" })).json();

  const meta = new Map((Array.isArray(status.items) ? status.items : []).map((it) => [it.group + "/" + it.name, it]));
  const results = blobs.filter((b) => b.pathname.startsWith(`requests/${id}/results/`))
    .map((b) => {
      const parts = b.pathname.split("/");                 // requests/<id>/results/[<group>/]<file>
      const name = base(b.pathname);
      let group = parts.length >= 5 ? parts[3] : (/\.(mp4|mov|webm)$/i.test(name) ? "videos" : "photos");
      if (!GROUPS.includes(group)) group = "photos";
      const m = meta.get(group + "/" + name) || {};
      return { url: b.url, downloadUrl: b.downloadUrl, name, group, size: b.size,
               title: m.title || "", caption: m.caption || "" };
    })
    .sort((a, b) => GROUPS.indexOf(a.group) - GROUPS.indexOf(b.group) || a.name.localeCompare(b.name));

  res.setHeader("Cache-Control", "s-maxage=8, stale-while-revalidate=20");
  res.status(200).json({
    id,
    name: request.name,
    prompt: request.prompt,
    createdAt: request.createdAt,
    uploads: request.files.map((f) => ({ url: f.url, name: f.name, type: f.type })),
    previews: blobs.filter((b) => b.pathname.startsWith(`requests/${id}/preview/`))
      .sort((a, b) => a.pathname.localeCompare(b.pathname)).map((b) => b.url),
    status: status.status,
    note: status.note || "",
    progress: typeof status.progress === "number" ? status.progress : null,
    title: status.title || "",
    subtitle: status.subtitle || "",
    updatedAt: status.updatedAt || request.createdAt,
    results,
  });
}
