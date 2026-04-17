# Add cloudflare gpg key
 mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-public-v2.gpg | tee /usr/share/keyrings/cloudflare-public-v2.gpg >/dev/null

# Add this repo to your apt repositories
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-public-v2.gpg] https://pkg.cloudflare.com/cloudflared any main' |  tee /etc/apt/sources.list.d/cloudflared.list

# install cloudflared
 apt-get update &&  apt-get install cloudflared



cloudflared service install eyJhIjoiNmU4Nzg1NjRkNDg4YjQ3YjA1MDM0YzcyMTE0Zjg0ZTUiLCJ0IjoiNWI3OGU0YmEtOTFlYS00MWRkLTk0OGEtYTIwY2QzYjQ5YjY1IiwicyI6IllXVXhPR0l5TjJJdE9EazVOeTAwTUdObUxXSXpPVFF0TlRjd00yVXdaVEF6Wm1NNCJ9
cloudflared tunnel run --token eyJhIjoiNmU4Nzg1NjRkNDg4YjQ3YjA1MDM0YzcyMTE0Zjg0ZTUiLCJ0IjoiNWI3OGU0YmEtOTFlYS00MWRkLTk0OGEtYTIwY2QzYjQ5YjY1IiwicyI6IllXVXhPR0l5TjJJdE9EazVOeTAwTUdObUxXSXpPVFF0TlRjd00yVXdaVEF6Wm1NNCJ9