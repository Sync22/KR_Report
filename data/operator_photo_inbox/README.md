# Operator Photo Inbox

Local-only inbox for screenshots or reference images the operator wants to use as implementation examples.

Rules:

- Keep this folder local to the project machine.
- Do not put secrets, access codes, cookies, `.env` screenshots, admin pages, DB paths, or Telegram/KRX credentials here.
- Use ordinary image files only: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.bmp`.
- Telegram intake is supported from the configured chat with `/사진 설명` as either the photo caption or a pending command before the next photo.
- Review with `python -m stock_monitor operator-photo-inbox-status --json`.
- This folder is an input queue only; it does not upload, publish, or expose images through `web-view`.
