// Saves the request (name, prompt, list of uploaded files) once all uploads have finished.
import { put } from "@vercel/blob";

const ID = /^[A-Za-z0-9]{12}$/;

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });
  const { id, name = "", prompt = "", files = [] } = req.body || {};
  if (!ID.test(id || "")) return res.status(400).json({ error: "Bad request id" });
  if (!String(prompt).trim()) return res.status(400).json({ error: "Please describe what you want done" });
  if (!Array.isArray(files) || files.length === 0 || files.length > 50) return res.status(400).json({ error: "Add 1 to 50 files" });

  const prefix = `requests/${id}/uploads/`;
  const clean = [];
  for (const f of files) {
    let u;
    try { u = new URL(f.url); } catch { return res.status(400).json({ error: "Bad file" }); }
    if (!u.hostname.endsWith(".blob.vercel-storage.com") || !String(f.pathname || "").startsWith(prefix))
      return res.status(400).json({ error: "Bad file" });
    clean.push({ url: f.url, pathname: f.pathname, name: String(f.name || "").slice(0, 160),
                 type: String(f.type || "").slice(0, 60), size: Number(f.size) || 0 });
  }
  const body = {
    id,
    name: String(name).trim().slice(0, 80),
    prompt: String(prompt).trim().slice(0, 4000),
    files: clean,
    createdAt: new Date().toISOString(),
  };
  try {
    await put(`requests/${id}/request.json`, JSON.stringify(body, null, 1), {
      access: "public", addRandomSuffix: false, allowOverwrite: false, contentType: "application/json",
    });
  } catch (e) {
    return res.status(409).json({ error: "This request was already sent" });
  }
  res.status(200).json({ ok: true, id });
}
