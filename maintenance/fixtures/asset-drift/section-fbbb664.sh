section "[INFO] Asset drift vs baseline"
# Tells you exactly which Common assets changed since the baseline was captured.
if [ -f maintenance/baseline/CommonAssetsIndex.hashes ] && [ -f "$ASSETS/CommonAssetsIndex.hashes" ]; then
  # LC_ALL=C: locale collation treats '-'/'_' as equal, making sort order
  # unstable for near-duplicate paths (e.g. Face-Scar.png vs Face_Scar.png)
  D="$(diff <(LC_ALL=C sort maintenance/baseline/CommonAssetsIndex.hashes) <(LC_ALL=C sort "$ASSETS/CommonAssetsIndex.hashes") | grep -c '^[<>]' || true)"
  if [ "$D" -eq 0 ]; then
    info "0 changed Common assets — docs verified against this build still apply"
  else
    warn "$D changed line(s) vs baseline — re-verify docs referencing those assets"
    info "see: diff <(LC_ALL=C sort maintenance/baseline/CommonAssetsIndex.hashes) <(LC_ALL=C sort \"$ASSETS/CommonAssetsIndex.hashes\")"
  fi
else
  warn "skipped (missing baseline or live index)"
fi
# Server/Cosmetics half (our own generated index — Hytale ships one for Common/ only).
if [ -f maintenance/baseline/ServerAssetsIndex.hashes ] && [ -d "$ASSETS/Server" ]; then
  D="$(maintenance/scripts/hash-server-assets.sh "$ASSETS" | diff maintenance/baseline/ServerAssetsIndex.hashes - | grep -c '^[<>]' || true)"
  if [ "$D" -eq 0 ]; then
    info "0 changed Server/Cosmetics assets — data-format docs verified against this build still apply"
  else
    warn "$D changed line(s) vs ServerAssetsIndex baseline — re-verify docs referencing those assets"
    info "see: maintenance/scripts/hash-server-assets.sh | diff maintenance/baseline/ServerAssetsIndex.hashes -"
  fi
else
  warn "Server-assets drift skipped (missing ServerAssetsIndex.hashes baseline or extracted Server/)"
fi

