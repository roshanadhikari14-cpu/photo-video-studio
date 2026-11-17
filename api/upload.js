// Issues short-lived upload tokens so the browser can send photos/videos straight to Vercel Blob
// (no size limit from the serverless function; big videos go up in parallel parts).
import { handleUpload } from "@vercel/blob/client";

const PATH = /^requests\/[A-Za-z0-9]{12}\/uploads\/[A-Za-z0-9._-]{1,120}$/;

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });
  try {
    const result = await handleUpload({
      request: req,
      body: req.body,
      onBeforeGenerateToken: async (pathname) => {
        if (!PATH.test(pathname)) throw new Error("Bad file path");
        return {
          allowedContentTypes: ["image/*", "video/*"],
          maximumSizeInBytes: 4 * 1024 * 1024 * 1024, // 4 GB per file
          addRandomSuffix: true,
        };
      },
    });
    res.status(200).json(result);
  } catch (e) {
    res.status(400).json({ error: e.message || "Upload refused" });
  }
}
