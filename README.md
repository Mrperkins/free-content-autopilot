# Free Content Autopilot

Zero-dollar, approval-first YouTube content-generation starter. **No paid fallbacks, no autopublishing without approval, private-only YouTube API uploads.**

## Workflow
1. GitHub Actions fetches RSS topic signals, asks a free-tier Gemini model to compare four niches, and creates review Issues.
2. The repository owner approves one niche by applying the `niche-approved` label to a bot-created proposal.
3. Scheduled runs create one short/long video script, render an MP4 locally with FFmpeg and espeak-ng, upload a review artifact and open an Issue.
4. The owner inspects the script and full MP4. Applying `publish-approved` to that Issue triggers SHA-256 validation and, only after OAuth secrets are configured, a **private** YouTube upload.

## One-time setup
- Open [Google AI Studio](https://aistudio.google.com/apikey) and make a key for a project with **billing disabled**. Confirm the selected Gemini model has free usage in your region. Add `GEMINI_API_KEY` under GitHub Settings → Secrets and variables → Actions.
- Enable Issues and Actions in this repository if needed. Actions → **Research niche for owner approval** → **Run workflow**. Apply `niche-approved` to just one suggested Issue.
- After a niche is approved, scheduled draft jobs produce videos. Review the video artifact attached to its Actions run and approve by applying `publish-approved`.
- For YouTube private uploads, create a Google Cloud OAuth desktop app with YouTube Data API v3 enabled. Run `python scripts-auth.py /path/to/client_secret.json` locally and add `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` as GitHub Action secrets. Do NOT paste secrets into Issues or commits. Public uploads can be restricted until Google audits the API project; testing OAuth refresh tokens can expire after 7 days.
- Test offline: `python -m unittest discover -s tests -v`. Sample rendering requires FFmpeg, espeak-ng and Pillow.

## Reality check and safeguards
- This starter is NOT connected to your Google accounts yet. Nothing publishes until you set permissions and explicitly approve each proposed video.
- Generated images are typographic graphics; narration is basic local text-to-speech, a functional baseline rather than premium visual production.
- RSS headlines are weak topic signals, not reliable audience size or revenue evidence. All factual claims must be checked before approval.
- No traffic, promotions, affiliate accounts, revenue, or monetization are implemented. No guaranteed income.
- Public GitHub Issues/artifacts can reveal drafts. GitHub Actions standard runners are free for public repositories subject to policy changes and limits.
- The no-billing requirement must be enforced on the Gemini/Google project itself, not just in this code.

References: [GitHub Actions billing](https://docs.github.com/en/actions/concepts/billing-and-usage), [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing), [YouTube uploads](https://developers.google.com/youtube/v3/docs/videos/insert).
