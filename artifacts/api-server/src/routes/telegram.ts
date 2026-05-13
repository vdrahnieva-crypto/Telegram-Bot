import { Router } from "express";
import { logger } from "../lib/logger";

const router = Router();

const BOT_PORT = process.env.BOT_PORT ?? "8090";
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET ?? "tg-crm-hook";
const BOT_URL = `http://localhost:${BOT_PORT}/${WEBHOOK_SECRET}`;

router.post(`/telegram/webhook`, async (req, res) => {
  try {
    const response = await fetch(BOT_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const data = await response.json();
    res.json(data);
  } catch (err) {
    logger.error({ err }, "Failed to forward Telegram update to bot");
    res.status(502).json({ ok: false, error: "bot unreachable" });
  }
});

export default router;
