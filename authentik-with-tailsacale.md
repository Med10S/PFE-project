# Authentik + Tailscale OIDC Setup Guide

This document explains how to configure Authentik as the OpenID Connect (OIDC) identity provider for Tailscale.

## Prerequisites

1. A running Authentik instance with admin access.
2. A domain name you control (required for WebFinger).
3. Public HTTPS access for your WebFinger endpoint.
4. A valid TLS certificate for your domain.

## 1. Configure Authentik

1. Sign in to Authentik as an administrator.
2. Open the Admin interface.
3. Go to Applications > Applications.
4. Click Create with Provider.

Create the Application and Provider with these values:

- Provider type: OAuth2/OpenID Connect.
- Strict redirect URI: https://login.tailscale.com/a/oauth_response.
- Signing key: any valid signing key.

Then:

1. Save the configuration.
2. Copy and store the Client ID and Client Secret.

You will need these values in Tailscale.

## 2. Start Tailscale OIDC Signup

1. Open https://login.tailscale.com/start.
2. Click Sign up with OIDC.
3. Enter the administrator email you will use for your Tailnet.
4. Select Authentik as identity provider type.
5. Click Get OIDC Issuer.

Important:

- The email domain must be a domain you own.
- The same domain must serve the WebFinger endpoint.

## 3. Configure the WebFinger Endpoint

Tailscale requires:

- https://<your-domain>/.well-known/webfinger

This endpoint must return JSON in this format:

```json
{
    "links": [
        {
            "href": "https://authentik.company/application/o/<application_slug>/",
            "rel": "http://openid.net/specs/connect/1.0/issuer"
        }
    ],
    "subject": "acct:your@email.com"
}
```

Notes:

- Replace your@email.com with the exact admin email used for Tailnet creation.
- The subject domain must match the domain hosting the WebFinger endpoint.
- Replace <application_slug> with your Authentik application slug.

## 4. Ensure HTTPS/TLS Is Valid

The WebFinger endpoint must be publicly reachable over HTTPS with a trusted certificate.

You can use Nginx Proxy Manager (Docker image: jc21/nginx-proxy-manager:latest) to simplify reverse proxy and TLS management.

Reference compose file:

- https://github.com/Med10S/PFE-project/blob/main/Proxy/docker-compose.yml

## 5. Final Tailscale Fields

In Tailscale OIDC setup, set:

- Client ID: from Authentik provider.
- Client secret: from Authentik provider.
- Prompts: keep default value consent.

Finish the signup flow and follow the remaining Tailscale prompts.

## Validation Checklist

- Authentik app/provider created and saved.
- Redirect URI is exactly https://login.tailscale.com/a/oauth_response.
- Client ID and Client Secret copied correctly.
- WebFinger endpoint is reachable at /.well-known/webfinger.
- WebFinger JSON contains correct href and subject.
- TLS certificate is valid and trusted.