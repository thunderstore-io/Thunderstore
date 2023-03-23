# Overwolf OAuth backend for Python Social Auth

https://overwolf.github.io/topics/integrations/login-with-overwolf

## Dependencies

```
django
pyjwt (2.0.1, see cached_jwk_client for more info)
social-auth-core (e.g. 4.1.0)
social-auth-app-django (e.g. 5.0.0)
```

## Configuration

In Django's config, add `"overwolf_auth.backends.OverwolfOAuth2"` to
`AUTHENTICATION_BACKENDS`. Also set suitable values for:

```
SOCIAL_AUTH_OVERWOLF_KEY = "id received from Overwolf"
SOCIAL_AUTH_OVERWOLF_SECRET = "secret token received from Overwolf"
SOCIAL_AUTH_OVERWOLF_SCOPE = ["openid", "profile", "email"]  # "openid" is required
SOCIAL_AUTH_OVERWOLF_GET_ALL_EXTRA_DATA = True
```
