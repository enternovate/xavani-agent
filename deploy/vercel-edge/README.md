# Xavani Omera edge host

A Vercel project with one external rewrite to the Render service. It gives
Xavani a `*.vercel.app` origin without a request-scoped runtime.

## Deploy

```bash
cd deploy/vercel-edge
vercel link --yes --project xavani-omera
vercel --prod
```

## Verify

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://xavani-omera.vercel.app/v1/capabilities
```

Expected: `401`. Without the service key the proxy cannot answer.

The service key stays on Render and in the Omera Vercel environment. It is not
part of this project.
