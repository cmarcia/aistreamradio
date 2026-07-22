Yes — with a **Python backend**, the recommendation changes slightly.

## Best solution for a Python app

Use a **Python auth library/framework** to handle OAuth/OIDC sign-in yourself, instead of a hosted auth platform, if you want it free.

### Good free options
* **Authlib** — very solid for OAuth 2.0 / OpenID Connect
* **django-allauth** — if you use Django - NOT IN USE IN THIS PROJECT IGNORE THIS
* **python-social-auth** — works with multiple frameworks
* **FastAPI + Authlib** — a common modern choice

## My recommendation

If you are building a custom backend in Python:

* **FastAPI + Authlib** if you want a clean, modern, flexible implementation
* **Django + django-allauth** if you are already using Django - NOT IN USE IN THIS PROJECT IGNORE THIS

## Why this is the best free approach

* no vendor auth subscription
* supports multiple identity providers
* you control user accounts and sessions
* you can still use Google, Microsoft, Facebook, LinkedIn

## What I would do in practice

### For FastAPI
* Use **Authlib** for OAuth/OIDC
* Use **JWT or secure cookies** for your app session
* Store a local user record in your DB
* Link social identities to that user

### For Django - (NOT IN USE IN THIS PROJECT IGNORE THIS)
* Use **django-allauth**
* It gives you a lot out of the box:
    * social login
    * account linking
    * signup flows
    * provider handling

## Provider support notes

* **Google**: easiest
* **Microsoft**: straightforward
* **Facebook**: possible, but app review and policy overhead
* **LinkedIn**: possible, but can be more restricted than Google/Microsoft

## My practical recommendation

If you want **free + Python + flexible**:

* **FastAPI + Authlib** is my top pick
* **Django + django-allauth** if you want a batteries-included solution

## Suggested architecture

* Frontend sends user to provider login
* Provider returns authorisation code
* Backend exchanges code for tokens
* Backend verifies identity
* Backend creates/loads local user
* Backend issues its own session/JWT

## What I would avoid

* implementing raw OAuth flows manually for each provider
* using access tokens directly as your app’s login mechanism
* relying on social login without a local user mapping

If you want, I can give you a **complete FastAPI example with Google login** or a **provider comparison for Python frameworks**.