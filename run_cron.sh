#!/bin/bash
# Railway cron script to check stock
curl -X GET "https://zarastock-production.up.railway.app/check" || exit 1

