# Security policy

## Secrets

Never commit an Anthropic API key. Use `.streamlit/secrets.toml`, a trusted environment variable,
or the in-app password field. If a key is accidentally committed, revoke it immediately in the
Anthropic Console; deleting the line from a later commit is not enough because Git history keeps it.

## Public deployment

The built-in request cap is scoped to a Streamlit session. It is not authentication and it does
not prevent a visitor from opening a new session. Use bring-your-own-key mode for a public MVP, or
add authentication and a persistent, server-side quota before funding public requests with a
shared key.

## Uploaded content

The app validates extension and size and parses uploaded documents in memory. File extensions are
not a complete security guarantee. Keep parser dependencies current, avoid confidential notes on
untrusted deployments, and add malware scanning if this becomes a production service.

## Reporting

For a public fork, use a private GitHub security advisory rather than posting keys, private lecture
materials, or exploitable details in a public issue.
