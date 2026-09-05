# Currently reading

The homepage shows the first two distinct original-article links in your public
Histre collection's RSS order. Histre-internal links (such as the collections-page
bookmark) are skipped. The rest of the collection can remain in Histre; it is not
published as a long reading list.

## Connected feed

The live feed URL was recovered from `~/Downloads/nzpJNKqe.rss` and tested without
a login on September 5, 2026:

https://histre.com/collections/e7ilf2kt/mail4295-public-collection/rss/

The collection's HTML page displayed a trust-score warning, but this RSS endpoint
returned valid article links. No Histre password, API token, or access code is
needed. Only titles and original URLs are imported, not notes or highlights.

The URL is saved in `data/reading-feed.json`. Its optional `titles` mapping keeps
a few existing article labels concise and stable; it does not pin those articles
in the selection. New articles use their feed titles automatically.

## Normal workflow

1. Add the articles you want to share to this public Histre collection. An upvote
   alone is not the collection selection. Keep private notes out of a public
   collection: Histre may publish them even though this site does not import them.
2. Run `python main.py`. It refreshes the feed, takes the first two distinct
   non-Histre links, saves `data/currently-reading.json`, and builds `site/`.
3. Commit and push using your normal workflow. Cloudflare must run
   `python main.py` as its build command; each build then fetches the current feed.

Feed order is authoritative. In the verified feed, the publication dates did not
match that order, so the importer does not sort by `pubDate`. To check exactly
what Histre is currently returning:

```sh
python reading.py --histre-feed 'https://histre.com/collections/e7ilf2kt/mail4295-public-collection/rss/' --latest
```

A failed fetch or malformed feed prints a warning and preserves the saved
snapshot. On a fresh Cloudflare checkout, the fallback is the snapshot committed
to Git, not necessarily the last deployed reading selection. An intentionally
empty feed hides the section. Downloads are limited to 1 MiB with a 15-second
request timeout, and redirects must stay on HTTPS histre.com.

Use `python main.py --offline` to build without a network request. This preserves
the current snapshot. Removing `data/reading-feed.json` also restores manual-only
builds.

## Update without pushing

Cloudflare's Git integration rebuilds on pushes; adding something to Histre does
not itself trigger a deployment. This repository includes an optional workflow,
`.github/workflows/refresh-reading.yml`, that requests a Cloudflare rebuild every
six hours (00:17, 06:17, 12:17, and 18:17 UTC), or on manual dispatch.

One-time setup:

1. In Cloudflare, open your project under **Workers & Pages**, then
   **Settings > Builds > Add deploy hook** (or **Deploy Hooks** for Workers Builds).
   Name it `currently-reading` and choose your production branch.
2. Copy the hook URL. Treat it as a secret: anyone holding it can trigger builds.
3. In the GitHub repository, go to **Settings > Secrets and variables > Actions**,
   create a repository secret named `CLOUDFLARE_DEPLOY_HOOK`, and paste the URL.
   Do not commit the hook URL or put it in frontend code.
4. Push these files to the repository's default branch. In **Actions > Refresh
   currently reading**, choose **Run workflow** to test it. Check Cloudflare's
   resulting deployment and the homepage afterward.

Until the secret is supplied, the workflow logs that it is not connected and
does not trigger a build. No Cloudflare hook or GitHub secret was created from
this workspace, and no push or production deployment was performed.

GitHub schedules run from the default branch and may be delayed; public-repository
schedules can be disabled after 60 days without repository activity. Re-enable
the workflow in Actions if necessary. This is periodic refresh, not instant sync.
Change the cron expression if you want a different interval.

References:
- [Cloudflare Pages deploy hooks](https://developers.cloudflare.com/pages/configuration/deploy-hooks/)
- [Cloudflare Workers Builds deploy hooks](https://developers.cloudflare.com/workers/ci-cd/builds/deploy-hooks/)
- [GitHub scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [Histre public collection feeds](https://histre.com/features/publish-rss/)

## Manual imports

A saved feed can be previewed or imported:

```sh
python reading.py --feed-file /path/to/collection.rss --latest
python reading.py --feed-file /path/to/collection.rss --latest --write
python main.py --offline
```

Without `--latest`, the importer is strict: it requires at most two article links
and rejects Histre links. Both RSS 2.0 and Atom are supported.

Shared notes are also supported:

```sh
python reading.py --histre-note 'PASTE_HISTRE_NOTE_SHARE_URL_HERE' --write
python main.py --offline
```

**A manual import replaces the whole snapshot.** To retain two shared notes, pass
both using two `--histre-note` arguments in the same command. Access-code links
are fetched but never stored. A normal online build will resume the configured
collection selection; use offline builds for a temporary manual selection.

For fully manual use, remove the feed configuration and edit
`data/currently-reading.json`: a list of zero, one, or two objects containing
`title` and `url`. An empty list hides the section.

## Validation

Run `python -B -m unittest discover -s tests`. Tests cover strict and latest feed
selection, feed ordering, duplicates, Histre-link exclusion, safe HTML, shared
notes, failure retention, title overrides, offline builds, and homepage rendering.
