#!/bin/bash
docker run -it --rm -v /data/NeuroVault/compose/nginx/certs:/etc/letsencrypt       -v /data/NeuroVault/compose/nginx/certs-data:/data/letsencrypt       certbot/certbot certonly --webroot --webroot-path=/data/letsencrypt       -d neurovault.org -d www.neurovault.org --force-renewal && cd /data/NeuroVault/ && docker-compose -f production.yml restart nginx
